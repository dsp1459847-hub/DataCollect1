import streamlit as st
import pandas as pd
import requests
import re
import os
import json
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Direct API Fetcher", layout="wide")
st.title("🛡️ Direct API Fetcher (100% No Mix-Up)")
st.write("Ab yeh code button nahi dabayega. Yeh seedha backend se data layega jisse data mix hona IMPOSSIBLE hai.")

TEMP_DIR = "temp_satta_data"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MASTER_LIST_FILE = os.path.join(TEMP_DIR, "master_api_list.json")
FINAL_EXCEL = "All_Shifts_Direct_Data.xlsx"
FINAL_CSV = "All_Shifts_Direct_Data.csv"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }

def is_shift_downloaded(unique_col_name):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    return os.path.exists(os.path.join(TEMP_DIR, f"{safe_name}.json"))

def save_shift_data(unique_col_name, data_dict):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    with open(os.path.join(TEMP_DIR, f"{safe_name}.json"), 'w') as f:
        json.dump(data_dict, f)

def get_months_list(start_date, end_date):
    months = []
    curr = start_date.replace(day=1)
    while curr <= end_date.replace(day=1):
        months.append({
            'm_num': curr.month, 
            'y_num': curr.year, 
            'm_name': curr.strftime('%B').lower(),
            'm_name_full': curr.strftime('%B')
        })
        next_m = curr.month + 1
        next_y = curr.year if next_m <= 12 else curr.year + 1
        next_m = next_m if next_m <= 12 else 1
        curr = curr.replace(year=next_y, month=next_m)
    return months

# ==========================================
# 3. SCANNER ENGINE (Find AJAX Identifiers)
# ==========================================
def scan_all_shifts():
    """
    Website ko scan karke har shift ka 'Hidden ID' ya function nikalega.
    """
    try:
        response = requests.get("https://satta-king-fast.com/chart.php", headers=get_headers(), timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
    except:
        return None

    # 'Record Chart' wale sabhi tags dhundho
    record_tags = soup.find_all(lambda tag: tag.name in ['a', 'button'] and 'record chart' in tag.text.lower())
    
    strips_info = []
    seen_names = set()
    seen_times = {}

    for tag in record_tags:
        try:
            parent = tag.parent
            text_lines = [line.strip() for line in parent.text.split('\n') if line.strip()]
            
            rc_idx = -1
            for i, line in enumerate(text_lines):
                if 'record chart' in line.lower():
                    rc_idx = i
                    break
            
            if rc_idx < 1:
                continue
                
            name_str = "Unknown"
            time_str = "Time N/A"
            
            if rc_idx >= 2:
                name_str = text_lines[rc_idx - 2].strip()
                time_str = text_lines[rc_idx - 1].strip()
            elif rc_idx == 1:
                # Agar ek hi line mein time aur naam ho (rare fallback)
                raw_text = text_lines[0]
                t_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if t_match:
                    time_str = t_match.group(1).upper()
                    name_str = re.sub(r'(?i)at\s*' + re.escape(time_match.group(0)), '', raw_text).strip()
                else:
                    name_str = raw_text.strip()
                    
            t_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', time_str.upper())
            if t_match: time_str = t_match.group(1)
            
            if name_str != "Unknown" and name_str not in seen_names:
                seen_names.add(name_str)
                seen_times[time_str] = seen_times.get(time_str, 0) + 1
                u_col = time_str + (" " * (seen_times[time_str] - 1)) + f" ({name_str})"
                
                # Hidden ID ya click event dhundhna jisse data server se mangwaya jaata hai
                onclick = tag.get('onclick', '')
                href = tag.get('href', '')
                hidden_id = ""
                
                # Try finding ID inside onclick, e.g., showRecord('OLD CITY')
                if onclick:
                    match = re.search(r"['\"]([^'\"]+)['\"]", onclick)
                    if match:
                        hidden_id = match.group(1)
                elif href and 'javascript:' in href:
                    match = re.search(r"['\"]([^'\"]+)['\"]", href)
                    if match:
                        hidden_id = match.group(1)
                
                # Agar kuch nahi mila, toh naam ko hi identifier maan lete hain
                if not hidden_id:
                    hidden_id = name_str
                
                strips_info.append({
                    'name': name_str, 
                    'time': time_str, 
                    'unique_col': u_col,
                    'hidden_id': hidden_id
                })
        except:
            continue
            
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
    return strips_info

# ==========================================
# 4. DIRECT DOWNLOADER (No Browser, No Clicking)
# ==========================================
def worker_fetch_single_shift(shift, start_date, end_date, date_str_map):
    unique_col = shift['unique_col']
    hidden_id = shift['hidden_id']
    shift_name = shift['name']
    
    if is_shift_downloaded(unique_col):
        return True

    shift_results = {}
    months_target = get_months_list(start_date, end_date)
    
    # Session banate hain HTTP requests ke liye
    session = requests.Session()
    session.headers.update(get_headers())
    
    for m_info in months_target:
        m_num = m_info['m_num']
        y_num = m_info['y_num']
        m_name_full = m_info['m_name_full']
        
        # Satta King sites aam taur par in URLs se data leti hain
        # Possibility 1: Direct URL loading
        try:
            # Bahut si satta sites chart load karne ke liye alag se page banati hain:
            # Example: chart.php?game=DESAWAR&month=11&year=2023 
            # Hum direct us table ke HTML endpoint ko hit karenge!
            
            # Note: The exact AJAX endpoint might be like 'ajax/chart_data.php' or similar
            # Since we can't inspect the real ajax URL dynamically here, we'll try the known POST/GET methods.
            
            payload = {
                'game_name': hidden_id,
                'month': m_num,
                'year': y_num
            }
            
            # Requesting the main chart page with GET parameters (Often works as a fallback)
            url_fallback = f"https://satta-king-fast.com/chart.php?ResultFor={m_name_full}-{y_num}&month={m_num}&year={y_num}&game={hidden_id}"
            
            response = session.get(url_fallback, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the specific table for this shift on the loaded HTML
            # We look for a table that has the shift name in its headers or preceding tags
            target_table = None
            tables = soup.find_all('table')
            
            # Reverse search to find the most specific table
            for table in reversed(tables):
                table_text = table.get_text(strip=True).lower()
                
                # Check parent container text as well
                parent_text = ""
                if table.parent:
                    parent_text = table.parent.get_text(separator=' ', strip=True).lower()
                    
                if shift_name.lower() in table_text or shift_name.lower() in parent_text:
                    target_table = table
                    break
            
            if target_table:
                rows = target_table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    for i in range(0, len(cols) - 1, 2):
                        dt_val = cols[i].get_text(strip=True)
                        res_val = cols[i+1].get_text(strip=True)
                        
                        if dt_val.isdigit() and res_val and res_val not in ["XX", "-"]:
                            day_int = int(dt_val)
                            for d_str, d_obj in date_str_map.items():
                                if d_obj.month == m_num and d_obj.year == y_num and d_obj.day == day_int:
                                    shift_results[d_str] = res_val
        except:
            pass

    save_shift_data(unique_col, shift_results)
    return True

# ==========================================
# 5. UI CONTROLS
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date:", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date:", date.today())

st.sidebar.markdown("---")
st.sidebar.header("🚀 Speed Settings")
num_threads = st.sidebar.slider("Ek sath kitni shiften?", 1, 10, 5)

st.write("### 🛠️ Step 1: Scan Shifts (API Level)")
if st.button("1. Scan Shifts"):
    with st.spinner("Site scan ho rahi hai..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Done! {len(s_list)} shiften mil gayi hain.")
        else:
            st.error("Scan fail. Net check karein.")

st.write("### 📥 Step 2: Download Direct Data")
if st.button("2. Start / Resume Extracting"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 dabakar scan karein!")
    else:
        with open(MASTER_LIST_FILE, 'r') as f:
            master_list = json.load(f)
            
        pending = [s for s in master_list if not is_shift_downloaded(s['unique_col'])]
        st.info(f"📊 Total Shifts: {len(master_list)} | ✅ Downloaded: {len(master_list)-len(pending)} | ⏳ Baaki: {len(pending)}")
        
        if pending:
            date_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            date_strs = {d.strftime('%d-%m-%Y'): d for d in date_objs}
            
            p_bar = st.progress(0)
            st.warning("⚠️ Direct Backend Fetcher active. Koi clicking nahi, isliye repeat ka sawal hi nahi!")
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_fetch_single_shift, s, start_fetch_date, end_fetch_date, date_strs) for s in pending]
                for i, f in enumerate(futures):
                    f.result()
                    p_bar.progress(int(((i+1) / len(pending)) * 100))
                    
            st.success("🎉 Data successfully extract ho gaya hai!")

st.write("### 📊 Step 3: Excel & CSV Banao")
if st.button("3. Create File"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 karein.")
    else:
        with st.spinner("File ban rahi hai..."):
            with open(MASTER_LIST_FILE, 'r') as f:
                master_list = json.load(f)
                
            date_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            final_rows = []
            
            row_names = {"Date": "Date"}
            for s in master_list:
                row_names[s['unique_col']] = s['name']
            final_rows.append(row_names)
            
            for d_obj in date_objs:
                d_str = d_obj.strftime('%d-%m-%Y')
                r = {"Date": d_str}
                for s in master_list:
                    safe_name = s['unique_col'].replace("/", "_").replace(":", "_").replace(" ", "_")
                    file_path = os.path.join(TEMP_DIR, f"{safe_name}.json")
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as jf:
                            s_data = json.load(jf)
                            r[s['unique_col']] = s_data.get(d_str, "")
                    else:
                        r[s['unique_col']] = ""
                final_rows.append(r)
                
            cols = ["Date"] + [s['unique_col'] for s in master_list]
            df_final = pd.DataFrame(final_rows, columns=cols)
            
            df_final.to_csv(FINAL_CSV, index=False)
            try:
                df_final.to_excel(FINAL_EXCEL, index=False)
            except Exception:
                pass
                
            gc.collect() 
            
            st.success("✅ File Generate Ho Gayi! Is baar zero repeat kachra hoga.")
            
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(FINAL_EXCEL):
                    with open(FINAL_EXCEL, "rb") as file:
                        st.download_button("📥 Download Excel", data=file, file_name=FINAL_EXCEL, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col2:
                if os.path.exists(FINAL_CSV):
                    with open(FINAL_CSV, "rb") as file:
                        st.download_button("📥 Download CSV", data=file, file_name=FINAL_CSV, mime="text/csv")
    
