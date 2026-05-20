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
st.set_page_config(page_title="Verified Shift Fetcher", layout="wide")
st.title("🛡️ 100+ Shifts Verified Data Fetcher")
st.write("Ab code table ka naam verify karega tabhi data uthayega. Koi data mix nahi hoga!")

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

def get_months_to_fetch(start_date, end_date):
    """Start aur End date ke beech ke URL months banata hai"""
    months = []
    curr = start_date.replace(day=1)
    while curr <= end_date.replace(day=1):
        months.append({'month': curr.month, 'year': curr.year, 'month_name': curr.strftime('%B')})
        next_m = curr.month + 1
        next_y = curr.year
        if next_m > 12:
            next_m = 1
            next_y += 1
        curr = curr.replace(year=next_y, month=next_m)
    return months

# ==========================================
# 3. STEP 1: SCAN 100+ SHIFTS (Slow Scroll Fix)
# ==========================================
def scan_all_shifts():
    """Dheere dheere niche jayega taki poori 100+ shiften load ho jayein"""
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    # SLOW SCROLL FIX: Poora page dhyaan se scroll karega taaki 50 ki jagah 100+ load hon
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
# 4. STEP 2: VERIFIED WORKER ENGINE
# ==========================================
def parse_verified_table(driver, shift_name, target_dates, results_dict, col_key, m_num, y_num):
    """
    YAHAN HAI AAPKA LOGIC: 
    Sabse niche wale table par jayega, uska naam padhega, match hua toh hi data lega.
    """
    tables = driver.find_elements(By.TAG_NAME, "table")
    
    # Naya khula table hamesha page ke aakhir mein hota hai, isliye list ko ulta (reversed) padhenge
    for table in reversed(tables):
        if table.is_displayed():
            header_text = table.text.lower()
            
            # VERIFICATION: Kya is table ke andar humari shift ka naam likha hai?
            if shift_name.lower() in header_text:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    # Date aur Result ko padhna
                    for i in range(0, len(cols) - 1, 2):
                        dt_text = cols[i].text.strip().lower()
                        val = cols[i+1].text.strip()
                        
                        if val and val != "XX" and val != "-":
                            for d_str, d_obj in target_dates.items():
                                if d_obj.month == m_num and d_obj.year == y_num:
                                    # Match exact date
                                    if dt_text == str(d_obj.day) or dt_text == d_obj.strftime('%d') or d_obj.strftime('%d-%b-%Y').lower() in dt_text:
                                        results_dict[d_str] = val
                # Sahi table mil gaya aur padh liya, ab baaki tables ignore karo
                return True 
    return False

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
    months_list = get_months_to_fetch(start_date, end_date)
    
    try:
        for m_info in months_list:
            m_num = m_info['month']
            y_num = m_info['year']
            m_name = m_info['month_name']
            
            # Mahine ke URL par direct jana
            url = f"https://satta-king-fast.com/chart.php?ResultFor={m_name}-{y_num}&month={m_num}&year={y_num}"
            driver.get(url)
            time.sleep(4)
            
            # Dheere dheere scroll karna
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Button dhundhna
            buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
            
            # Wahi same shift dhundhna jiska naam target mein hai
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
                # Button click karna
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target_btn)
                time.sleep(3) # Naya table niche khulne ka wait
                
                # Verified data nikalna
                parse_verified_table(driver, shift_name, date_list_strs, shift_results, unique_col, m_num, y_num)
            
        # Jab saare mahine pure ho jayein tab data save karein
        save_shift_data(unique_col, shift_results)
        
    except:
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

# --- BUTTON 1: SCAN ---
st.write("### 🛠️ Step 1: Saari Shifton Ki Pakki List Banayein")
if st.button("1. Scan All Shifts"):
    with st.spinner("Site ko dheere-dheere scroll karke poori 100+ shiften nikali ja rahi hain..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Poori! Site par exactly **{len(s_list)}** shiften mili hain.")
        else:
            st.error("Scan fail ho gaya.")

# --- BUTTON 2: DOWNLOAD ---
st.write("### 📥 Step 2: Data Download Karein (Batch Mode)")
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
                    
            st.success("🎉 Saari bachi hui shifton ka data successfully download ho gaya hai!")
        else:
            st.success("✅ Saari shiften pehle se hi download ho chuki hain. Sidha Step 3 dabayein!")

# --- BUTTON 3: EXCEL BANAO ---
st.write("### 📊 Step 3: Excel File Taiyar Karein")
if st.button("3. Create Final Excel"):
    if not os.path.exists(MASTER_LIST_FILE):
        st.error("Pehle Step 1 karein.")
    else:
        with open(MASTER_LIST_FILE, 'r') as f:
            master_list = json.load(f)
            
        date_list_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
        
        final_rows = []
        # Header Row (Naam)
        row_names = {"Date": "Date"}
        for s in master_list:
            row_names[s['unique_col']] = s['name']
        final_rows.append(row_names)
        
        # Asli Data
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
                
