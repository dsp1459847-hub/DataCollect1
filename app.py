import streamlit as st
import pandas as pd
import os
import time
import json
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. PAGE & SYSTEM SETUP
# ==========================================
st.set_page_config(page_title="100% Verified Shift Fetcher", layout="wide")
st.title("🛡️ Verified 100+ Shifts AJAX Fetcher")
st.write("Ab code shift ka naam verify karega aur Neele Button daba kar data nikalega!")

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
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    return options

def is_shift_downloaded(unique_col_name):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    return os.path.exists(os.path.join(TEMP_DIR, f"{safe_name}.json"))

def save_shift_data(unique_col_name, data_dict):
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    with open(os.path.join(TEMP_DIR, f"{safe_name}.json"), 'w') as f:
        json.dump(data_dict, f)

# ==========================================
# 3. STEP 1: SCAN 100+ SHIFTS
# ==========================================
def scan_all_shifts():
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    # Slow Scroll taki sab load ho
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
                
                strips_info.append({
                    'idx': idx,
                    'name': name_str, 
                    'time': time_str, 
                    'unique_col': u_col
                })
        except:
            continue
            
    driver.quit()
    
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
            
    return strips_info

# ==========================================
# 4. STEP 2: VERIFIED WORKER ENGINE (Neele Button & Single Dates)
# ==========================================
def worker_fetch_single_shift(shift, start_date, end_date, date_list_strs):
    unique_col = shift['unique_col']
    shift_name = shift['name']
    
    if is_shift_downloaded(unique_col):
        return True

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return False
        
    shift_results = {}
    
    try:
        driver.get("https://satta-king-fast.com/chart.php")
        time.sleep(3)
        
        # 1. Scroll aur target button dhundhna
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
        
        if shift['idx'] >= len(buttons):
            return False
            
        target_btn = buttons[shift['idx']]
        
        # 2. Record chart par click (Naya table niche khulega)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", target_btn)
        time.sleep(3) # AJAX table load hone ka wait
        
        current_check_date = end_date
        
        # LOOP: Jab tak Start Date tak na pahunch jayein
        while current_check_date >= start_date.replace(day=1):
            
            # 3. YAHAN HAI NAAM VERIFICATION
            tables = driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            # Hamesha dusra ya aakhri table check karna (Permanent top 4 ko chhodkar)
            for table in reversed(tables):
                if table.is_displayed():
                    try:
                        parent_text = table.find_element(By.XPATH, "..").text.lower()
                        # Agar Naam match hua, toh yahi sahi table hai!
                        if shift_name.lower() in parent_text or shift_name.lower() in table.text.lower():
                            target_table = table
                            break
                    except:
                        pass
            
            # 4. Single Dates (1, 2, 3... 31) aur Result padhna
            if target_table:
                rows = target_table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    for i in range(0, len(cols) - 1, 2):
                        dt_text = cols[i].text.strip()
                        val = cols[i+1].text.strip()
                        
                        if dt_text.isdigit() and val and val not in ["XX", "-"]:
                            day_int = int(dt_text)
                            
                            # Exact us mahine ki tareekh ke samne data dalna
                            for d_str, d_obj in date_list_strs.items():
                                if d_obj.month == current_check_date.month and d_obj.year == current_check_date.year and d_obj.day == day_int:
                                    shift_results[d_str] = val
            
            # Check limit
            if current_check_date.year < start_date.year or (current_check_date.year == start_date.year and current_check_date.month <= start_date.month):
                break
                
            # 5. NEELE BUTTON PAR CLICK KARNA (Pichla Mahina)
            prev_m_date = current_check_date.replace(day=1) - timedelta(days=1)
            prev_m_name = prev_m_date.strftime("%b").lower() # jaise 'oct'
            prev_y_str = prev_m_date.strftime("%Y") # jaise '2023'
            
            clicked = False
            blue_btns = driver.find_elements(By.XPATH, "//a | //button")
            for btn in blue_btns:
                if btn.is_displayed():
                    btn_txt = btn.text.lower()
                    # Button par pichle mahine ka naam aur saal likha hona chahiye
                    if prev_m_name in btn_txt and prev_y_str in btn_txt:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3) # Naya mahina update hone ka wait
                        clicked = True
                        break
            
            if not clicked:
                break # Agar pichla button na mile, toh loop tod do
                
            current_check_date = prev_m_date
            
        # Jab saare mahine pure ho jayein tabhi data save karna
        save_shift_data(unique_col, shift_results)
        
    except Exception as e:
        pass
    finally:
        driver.quit()
        
    return True

# ==========================================
# 5. UI CONTROLS
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana?):", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

st.sidebar.markdown("---")
st.sidebar.header("🚀 Browser Settings")
num_browsers = st.sidebar.slider("Ek sath kitne Browser kholne hain?", 1, 10, 5)

st.write("### 🛠️ Step 1: Saari Shifton Ki Pakki List Banayein")
if st.button("1. Scan All Shifts"):
    with st.spinner("Site scroll karke poori 100+ shiften verify ki ja rahi hain..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Poori! Site par exactly **{len(s_list)}** shiften mili hain.")
        else:
            st.error("Scan fail ho gaya.")

st.write("### 📥 Step 2: Verified Data Download Karein")
if st.button("2. Start / Resume Download"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 dabakar scan poora karein!")
    else:
        with open(MASTER_LIST_FILE, 'r') as f:
            master_list = json.load(f)
            
        pending_shifts = [s for s in master_list if not is_shift_downloaded(s['unique_col'])]
        done_count = len(master_list) - len(pending_shifts)
        
        st.info(f"📊 Total Shifts: {len(master_list)} | ✅ Pehle se Downloaded: {done_count} | ⏳ Baaki: {len(pending_shifts)}")
        
        if pending_shifts:
            date_list_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            date_strs = {d.strftime('%d-%m-%Y'): d for d in date_list_objs}
            
            progress_bar = st.progress(0)
            
            with ThreadPoolExecutor(max_workers=num_browsers) as executor:
                futures = []
                for s in pending_shifts:
                    futures.append(executor.submit(worker_fetch_single_shift, s, start_fetch_date, end_fetch_date, date_strs))
                
                completed = 0
                for f in futures:
                    f.result()
                    completed += 1
                    progress_bar.progress(int((completed / len(pending_shifts)) * 100))
                    
            st.success("🎉 Saari bachi hui shifton ka Verified Data successfully download ho gaya hai!")
        else:
            st.success("✅ Saari shiften pehle se hi download ho chuki hain. Sidha Step 3 dabayein!")

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
        
