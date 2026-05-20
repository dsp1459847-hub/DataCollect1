import streamlit as st
import pandas as pd
import os
import time
import json
import re
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. SETUP & SYSTEM DIRECTORIES
# ==========================================
st.set_page_config(page_title="Pro Satta Fetcher - Parallel Engine", layout="wide")
st.title("🛡️ Pro Multi-Browser Fetcher (Data Isolated)")
st.write("Har Mahine ka alag browser khulega. Kisi shift ka data aapas mein mix nahi hoga!")

TEMP_DIR = "temp_satta_data"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MASTER_LIST_FILE = os.path.join(TEMP_DIR, "master_shifts_list.json")
FINAL_EXCEL = "All_Shifts_Master_Data.xlsx"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_browser_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    return options

def is_shift_downloaded(unique_col_name):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    return os.path.exists(os.path.join(TEMP_DIR, f"{safe_name}.json"))

def save_shift_data(unique_col_name, data_dict):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    with open(os.path.join(TEMP_DIR, f"{safe_name}.json"), 'w') as f:
        json.dump(data_dict, f)

def get_months_to_fetch(start_date, end_date):
    months = []
    curr = start_date.replace(day=1)
    while curr <= end_date.replace(day=1):
        months.append({'month': curr.month, 'year': curr.year, 'month_name': curr.strftime('%B').lower()})
        next_m = curr.month + 1
        next_y = curr.year
        if next_m > 12:
            next_m = 1
            next_y += 1
        curr = curr.replace(year=next_y, month=next_m)
    return months

# ==========================================
# 3. STEP 1: DEEP SCAN & EXACT TARGETING
# ==========================================
def scan_all_shifts():
    """Sabse pehle saari shifton ki pakki list banata hai, taki mix-up na ho"""
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    time.sleep(2)
    
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
                        rc_idx = i
                        break
                if rc_idx >= 1: break
            
            if rc_idx == -1: continue
            
            name_str, time_str = "Unknown", "Time N/A"
            if rc_idx >= 2:
                name_str = lines[rc_idx - 2].strip()
                time_str = lines[rc_idx - 1].strip()
            
            if name_str != "Unknown" and name_str not in seen_names:
                seen_names.add(name_str)
                seen_times[time_str] = seen_times.get(time_str, 0) + 1
                u_col = time_str + (" " * (seen_times[time_str] - 1)) + f" ({name_str})"
                
                # JavaScript ke function parameter se hidden ID nikalna (Agar available ho)
                onclick_val = btn.get_attribute("onclick")
                hidden_id = ""
                if onclick_val:
                    match = re.search(r"show_record\('([^']+)'\)", onclick_val)
                    if match:
                        hidden_id = match.group(1)
                
                strips_info.append({
                    'idx': idx,
                    'name': name_str, 
                    'time': time_str, 
                    'unique_col': u_col,
                    'hidden_id': hidden_id
                })
        except:
            continue
            
    driver.quit()
    
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
            
    return strips_info

# ==========================================
# 4. STEP 2: PARALLEL MONTHLY WORKER ENGINE
# ==========================================
def worker_fetch_month_data(shift_data, target_month_info, date_list_strs):
    """
    Yeh ek independent browser hai jo sirf 1 mahine ka data layega.
    Isse data aapas mein mix hone ka sawal hi paida nahi hota.
    """
    m_num = target_month_info['month']
    y_num = target_month_info['year']
    m_name = target_month_info['month_name']
    shift_name = shift_data['name']
    idx = shift_data['idx']
    
    monthly_results = {}
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return monthly_results
        
    try:
        # Direct us mahine ka URL hit karna
        url = f"https://satta-king-fast.com/chart.php?ResultFor={m_name}-{y_num}&month={m_num}&year={y_num}"
        driver.get(url)
        time.sleep(3)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
        
        target_btn = None
        for btn in buttons:
            try:
                parent_text = btn.find_element(By.XPATH, "..").text.lower()
                if shift_name.lower() in parent_text:
                    target_btn = btn
                    break
            except:
                pass
                
        if target_btn:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
            time.sleep(1)
            # Click karte hi naya data specific ID ya div me khulta hai
            driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(3) # AJAX wait
            
            # STRICT VERIFICATION: Naye table ko isolate karke padhna
            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in reversed(tables):
                if table.is_displayed():
                    try:
                        t_text = table.text.lower()
                        p_text = table.find_element(By.XPATH, "..").text.lower()
                        # Sirf wohi table jisme humari shift ka naam ho!
                        if shift_name.lower() in t_text or shift_name.lower() in p_text:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for row in rows:
                                cols = row.find_elements(By.TAG_NAME, "td")
                                for i in range(0, len(cols) - 1, 2):
                                    dt_val = cols[i].text.strip()
                                    res_val = cols[i+1].text.strip()
                                    
                                    if dt_val.isdigit() and res_val and res_val not in ["XX", "-"]:
                                        day_int = int(dt_val)
                                        # Data ko correct date mein daalna
                                        for d_str, d_obj in date_list_strs.items():
                                            if d_obj.month == m_num and d_obj.year == y_num and d_obj.day == day_int:
                                                monthly_results[d_str] = res_val
                            # Data milne ke baad loop break kar do taaki koi aur table na padh le
                            break 
                    except:
                        pass
    except Exception as e:
        pass
    finally:
        driver.quit()
        
    return monthly_results

def manager_fetch_single_shift(shift, start_date, end_date, date_list_strs):
    """Ek shift ke andar alag-alag mahino ke browsers (Threads) chalata hai"""
    unique_col = shift['unique_col']
    
    if is_shift_downloaded(unique_col):
        return True
        
    shift_all_data = {}
    months_list = get_months_to_fetch(start_date, end_date)
    
    # Aapka logic: Har mahine ke liye alag browser chalega ek sath (Fast speed & No mixup)
    max_month_browsers = min(12, len(months_list)) # Maximum 12 browsers ek sath
    
    with ThreadPoolExecutor(max_workers=max_month_browsers) as executor:
        futures = []
        for m_info in months_list:
            futures.append(executor.submit(worker_fetch_month_data, shift, m_info, date_list_strs))
            
        for f in futures:
            m_res = f.result()
            shift_all_data.update(m_res)
            
    # Mahine ke sabhi data merge karke Save karna
    save_shift_data(unique_col, shift_all_data)
    return True

# ==========================================
# 5. UI CONTROLS
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana?):", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

st.sidebar.markdown("---")
st.sidebar.header("🚀 Speed Settings")
num_shifts_parallel = st.sidebar.slider("Ek sath kitni shifts chalani hain?", 1, 5, 2)

st.write("### 🛠️ Step 1: Shifton Ki Pakki List")
if st.button("1. Scan All Shifts"):
    with st.spinner("Site scroll karke poori shiften verify ki ja rahi hain..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Poori! Site par exactly **{len(s_list)}** shiften mili hain.")
        else:
            st.error("Scan fail ho gaya.")

st.write("### 📥 Step 2: Download (Month-Wise Parallel Browsers)")
if st.button("2. Start Download"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 dabakar scan poora karein!")
    else:
        with open(MASTER_LIST_FILE, 'r') as f:
            master_list = json.load(f)
            
        pending_shifts = [s for s in master_list if not is_shift_downloaded(s['unique_col'])]
        done_count = len(master_list) - len(pending_shifts)
        
        st.info(f"📊 Total Shifts: {len(master_list)} | ✅ Downloaded: {done_count} | ⏳ Baaki: {len(pending_shifts)}")
        
        if pending_shifts:
            date_list_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            date_strs = {d.strftime('%d-%m-%Y'): d for d in date_list_objs}
            
            progress_bar = st.progress(0)
            st.warning("⚡ Engine Started! Har mahine ka alag data extract ho raha hai taaki data mix na ho.")
            
            with ThreadPoolExecutor(max_workers=num_shifts_parallel) as executor:
                futures = []
                for s in pending_shifts:
                    futures.append(executor.submit(manager_fetch_single_shift, s, start_fetch_date, end_fetch_date, date_strs))
                
                completed = 0
                for f in futures:
                    f.result()
                    completed += 1
                    progress_bar.progress(int((completed / len(pending_shifts)) * 100))
                    
            st.success("🎉 Saari bachi hui shifton ka Verified Data successfully download ho gaya hai!")

st.write("### 📊 Step 3: Excel File Taiyar Karein")
if st.button("3. Create Final Excel"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 karein.")
    else:
        with open(MASTER_LIST_FILE, 'r') as f:
            master_list = json.load(f)
            
        date_list_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
        
        final_rows = []
        row_names = {"Date": "Date"}
        for s in master_list:
            row_names[s['unique_col']] = s['name']
        final_rows.append(row_names)
        
        for d_obj in date_list_objs:
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
        df_final.to_excel(FINAL_EXCEL, index=False)
        
        st.success("✅ Excel File Taiyar Hai!")
        with open(FINAL_EXCEL, "rb") as file:
            st.download_button("📥 Download Final Excel", data=file, file_name=FINAL_EXCEL, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
