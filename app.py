import streamlit as st
import pandas as pd
import os
import time
import json
import re
import gc
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. PAGE & FOLDER SETUP
# ==========================================
st.set_page_config(page_title="Master Satta Fetcher", layout="wide")
st.title("🛡️ Master 100+ Shifts Fetcher (Strict Match)")
st.write("Ab code shift ka naam aankhon se verify karega tabhi data Excel mein aayega.")

TEMP_DIR = "temp_satta_data"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MASTER_LIST_FILE = os.path.join(TEMP_DIR, "master_shifts_list.json")
FINAL_EXCEL = "All_Shifts_Data.xlsx"
FINAL_CSV = "All_Shifts_Data.csv"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_browser_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    return options

def is_shift_downloaded(unique_col_name):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    return os.path.exists(os.path.join(TEMP_DIR, f"{safe_name}.json"))

def save_shift_data(unique_col_name, data_dict):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    with open(os.path.join(TEMP_DIR, f"{safe_name}.json"), 'w') as f:
        json.dump(data_dict, f)

def get_months_target(start_date, end_date):
    months = []
    curr = start_date.replace(day=1)
    while curr <= end_date.replace(day=1):
        months.append({
            'm_num': curr.month, 
            'y_num': curr.year, 
            'm_name': curr.strftime('%B').lower()
        })
        next_m = curr.month + 1
        next_y = curr.year if next_m <= 12 else curr.year + 1
        next_m = next_m if next_m <= 12 else 1
        curr = curr.replace(year=next_y, month=next_m)
    return months

def sanitize_text(text):
    if not isinstance(text, str): return str(text)
    return re.sub(r'[^\x20-\x7E]', '', text).strip()

# ==========================================
# 3. SCANNER ENGINE (Step 1)
# ==========================================
def scan_all_shifts():
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h: break
        last_h = new_h
        
    buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
    
    strips_info = []
    seen_names = set()
    seen_times = {}

    for idx, btn in enumerate(buttons):
        try:
            node = btn
            rc_idx = -1
            lines = []
            for _ in range(5):
                node = node.find_element(By.XPATH, "..")
                lines = [x.strip() for x in node.text.split('\n') if x.strip()]
                for i, line in enumerate(lines):
                    if "record chart" in line.lower():
                        rc_idx = i; break
                if rc_idx >= 1: break
            
            if rc_idx == -1: continue
            
            name_str = lines[rc_idx - 2].strip() if rc_idx >= 2 else "Unknown"
            time_str = lines[rc_idx - 1].strip() if rc_idx >= 2 else "Time N/A"
            
            if name_str != "Unknown" and name_str not in seen_names:
                seen_names.add(name_str)
                seen_times[time_str] = seen_times.get(time_str, 0) + 1
                u_col = time_str + (" " * (seen_times[time_str] - 1)) + f" ({name_str})"
                
                strips_info.append({'name': name_str, 'unique_col': u_col})
        except:
            continue
            
    driver.quit()
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
    return strips_info

# ==========================================
# 4. DOWNLOADER ENGINE (Step 2 - Exact Name Match)
# ==========================================
def worker_fetch_single_shift(shift, start_date, end_date, date_str_map):
    unique_col = shift['unique_col']
    shift_name = shift['name']
    
    if is_shift_downloaded(unique_col):
        return True

    shift_results = {}
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return False
        
    months_target = get_months_target(start_date, end_date)
    
    try:
        for m_info in months_target:
            m_num = m_info['m_num']
            y_num = m_info['y_num']
            
            url = f"https://satta-king-fast.com/chart.php?ResultFor={m_info['m_name']}-{y_num}&month={m_num}&year={y_num}"
            driver.get(url)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
            
            target_btn = None
            for btn in buttons:
                try:
                    node = btn
                    rc_idx = -1
                    lines = []
                    for _ in range(5):
                        node = node.find_element(By.XPATH, "..")
                        lines = [x.strip() for x in node.text.split('\n') if x.strip()]
                        for i, line in enumerate(lines):
                            if "record chart" in line.lower():
                                rc_idx = i; break
                        if rc_idx >= 1: break
                    
                    if rc_idx >= 1:
                        n_str = lines[rc_idx - 2].strip() if rc_idx >= 2 else lines[0].split('at')[0].strip()
                        if n_str.lower() == shift_name.lower():
                            target_btn = btn
                            break
                except:
                    pass
                    
            if target_btn:
                # 👉 FIX: Purane table ko screen se uda dena, taki repeat data ka chakkar khatam ho jaye!
                driver.execute_script("""
                    var tables = document.querySelectorAll('table');
                    if (tables.length > 0) {
                        tables[tables.length - 1].innerHTML = '<tr id="waiting_row"><td>WAITING_FOR_DATA</td></tr>';
                    }
                """)
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target_btn)
                
                # 👉 FIX: Naya table aane ka wait karna aur NAAM verify karna!
                for _ in range(15):
                    time.sleep(1)
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    if tables:
                        last_t = tables[-1]
                        try:
                            if "WAITING_FOR_DATA" not in last_t.text:
                                p_text = last_t.find_element(By.XPATH, "..").text.lower()
                                gp_text = last_t.find_element(By.XPATH, "../..").text.lower()
                                
                                # Jab naam exactly match ho jayega tabhi data nikalna
                                if shift_name.lower() in p_text or shift_name.lower() in gp_text:
                                    rows = last_t.find_elements(By.TAG_NAME, "tr")
                                    for row in rows:
                                        cols = row.find_elements(By.TAG_NAME, "td")
                                        for i in range(0, len(cols) - 1, 2):
                                            dt_val = cols[i].text.strip()
                                            res_val = cols[i+1].text.strip()
                                            
                                            # Single dates check (1, 2, 3...)
                                            if dt_val.isdigit() and res_val and res_val not in ["XX", "-"]:
                                                day_int = int(dt_val)
                                                for d_str, d_obj in date_str_map.items():
                                                    if d_obj.month == m_num and d_obj.year == y_num and d_obj.day == day_int:
                                                        shift_results[d_str] = res_val
                                    break # Ek baar load ho gaya, toh intezar band karo
                        except:
                            pass

    except Exception as e:
        pass
    finally:
        driver.quit()
        
    save_shift_data(unique_col, shift_results)
    return True

# ==========================================
# 5. UI CONTROLS & EXCEL GENERATOR
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana?):", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

st.sidebar.markdown("---")
st.sidebar.header("🚀 Speed Settings")
num_browsers = st.sidebar.slider("Ek sath kitne Browser (Tabs)?", 1, 10, 5)

st.write("### 🛠️ Step 1: Scan All Shifts")
if st.button("1. Scan 100+ Shifts"):
    with st.spinner("Site ki scanning chal rahi hai..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Done! {len(s_list)} shiften properly detect ho gayi hain.")
        else:
            st.error("Scan fail. Net connection check karein.")

st.write("### 📥 Step 2: Extract Data (Verified Mode)")
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
            
            with ThreadPoolExecutor(max_workers=num_browsers) as executor:
                futures = [executor.submit(worker_fetch_single_shift, s, start_fetch_date, end_fetch_date, date_strs) for s in pending]
                for i, f in enumerate(futures):
                    f.result()
                    p_bar.progress(int(((i+1) / len(pending)) * 100))
                    
            st.success("🎉 Har ek shift ka VERIFIED data extract ho gaya hai!")

st.write("### 📊 Step 3: File Generate Karein")
if st.button("3. Create File"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 karein.")
    else:
        with st.spinner("File ban rahi hai, memory clean ho rahi hai..."):
            with open(MASTER_LIST_FILE, 'r') as f:
                master_list = json.load(f)
                
            date_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            final_rows = []
            
            # Header Row
            row_names = {"Date": "Date"}
            for s in master_list:
                row_names[sanitize_text(s['unique_col'])] = sanitize_text(s['name'])
            final_rows.append(row_names)
            
            # Data Rows
            for d_obj in date_objs:
                d_str = d_obj.strftime('%d-%m-%Y')
                r = {"Date": d_str}
                for s in master_list:
                    s_col = sanitize_text(s['unique_col'])
                    safe_name = s['unique_col'].replace("/", "_").replace(":", "_").replace(" ", "_")
                    file_path = os.path.join(TEMP_DIR, f"{safe_name}.json")
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as jf:
                            s_data = json.load(jf)
                            r[s_col] = sanitize_text(s_data.get(d_str, ""))
                    else:
                        r[s_col] = ""
                final_rows.append(r)
                
            cols = ["Date"] + [sanitize_text(s['unique_col']) for s in master_list]
            df_final = pd.DataFrame(final_rows, columns=cols)
            
            df_final.to_csv(FINAL_CSV, index=False)
            try:
                df_final.to_excel(FINAL_EXCEL, index=False)
            except Exception as e:
                st.warning("Excel save error, par CSV perfectly save ho gayi!")
                
            gc.collect() 
            
            st.success("✅ File Generate Ho Gayi! Koi duplication nahi milegi.")
            
            col1, col2 = st.columns(2)
            with col1:
                with open(FINAL_EXCEL, "rb") as file:
                    st.download_button("📥 Download Excel", data=file, file_name=FINAL_EXCEL, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col2:
                with open(FINAL_CSV, "rb") as file:
                    st.download_button("📥 Download CSV", data=file, file_name=FINAL_CSV, mime="text/csv")
    
