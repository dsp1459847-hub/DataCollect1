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
# 1. PAGE & FOLDER SETUP (For Saving Progress)
# ==========================================
st.set_page_config(page_title="Anti-Crash Shift Fetcher", layout="wide")
st.title("🛡️ Anti-Crash 100+ Shifts Fetcher")
st.write("Call aaye ya screen lock ho, data kabhi delete nahi hoga. Jahan rukega, wahi se aage shuru hoga!")

# Temporary folder jahan har shift ka data alag se save hoga (Taki crash hone par bacha rahe)
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
    """Check karta hai ki kya is shift ka data pehle se save ho chuka hai?"""
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    file_path = os.path.join(TEMP_DIR, f"{safe_name}.json")
    return os.path.exists(file_path)

def save_shift_data(unique_col_name, data_dict):
    """Ek shift ka data nikalte hi use turant hard drive me lock (save) kar deta hai"""
    safe_name = unique_col_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    file_path = os.path.join(TEMP_DIR, f"{safe_name}.json")
    with open(file_path, 'w') as f:
        json.dump(data_dict, f)

# ==========================================
# 3. STEP 1: SCAN ALL 100+ SHIFTS (Pakki List)
# ==========================================
def scan_all_shifts():
    """Poora page deeply scroll karke saari 100+ shifton ki ginti aur list banata hai"""
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except:
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    # Page ko deeply scroll karna taki koi shift chhupi na rahe
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    
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
    
    # Pakki list ko save kar lo taki dobara scan na karna pade
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
            
    return strips_info

# ==========================================
# 4. STEP 2: WORKER ENGINE (Neele Button Wala)
# ==========================================
def worker_fetch_single_shift(shift, start_date, end_date, date_list_strs):
    """Ek alag browser khulega, is shift pe jayega aur neele button dabayega"""
    unique_col = shift['unique_col']
    
    # Agar pehle hi download ho chuka hai (Crash hone se pehle), toh skip karo!
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
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Sahi button dhundhna
        buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
        if shift['idx'] >= len(buttons):
            return False
            
        target_btn = buttons[shift['idx']]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", target_btn)
        time.sleep(3)
        
        # Mahino me piche jana (Neele button dabana)
        curr_chk = end_date
        months_names_short = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        
        while curr_chk >= start_date.replace(day=1):
            # Table Padhna
            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                if table.is_displayed():
                    for row in table.find_elements(By.TAG_NAME, "tr"):
                        cols = row.find_elements(By.TAG_NAME, "td")
                        for i in range(0, len(cols) - 1, 2):
                            dt_text = cols[i].text.strip().lower()
                            val = cols[i+1].text.strip()
                            if val and val != "XX" and val != "-":
                                # Date match logic
                                for d_str, d_obj in date_list_strs.items():
                                    if d_obj.month == curr_chk.month and d_obj.year == curr_chk.year:
                                        if dt_text == str(d_obj.day) or dt_text == d_obj.strftime('%d') or d_obj.strftime('%d-%b-%Y').lower() in dt_text:
                                            shift_results[d_str] = val
            
            # Agar limit tak pahunch gaye toh break
            if curr_chk.year < start_date.year or (curr_chk.year == start_date.year and curr_chk.month <= start_date.month):
                break
                
            # NEELA BUTTON DHUNDH KAR DABANA (Pichle Mahine ke liye)
            clicked = False
            all_links = driver.find_elements(By.TAG_NAME, "a") + driver.find_elements(By.TAG_NAME, "button")
            for link in all_links:
                if link.is_displayed():
                    lt = link.text.lower()
                    if any(m in lt for m in months_names_short) and curr_chk.strftime('%Y') in lt or str(curr_chk.year - 1) in lt:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", link)
                        time.sleep(3) # Naya mahina load hone ka wait
                        clicked = True
                        break
            
            if not clicked:
                break
                
            # Date piche karna
            m = curr_chk.month - 1
            y = curr_chk.year
            if m == 0:
                m = 12
                y -= 1
            curr_chk = curr_chk.replace(year=y, month=m)
            
        # Data Save Karna (Crash-Proof)
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
# Aapne 10 bola tha, par mobile ki RAM ke hisab se 5-6 safe rehta hai. Aap isko slider se 10 tak kar sakte hain.
num_browsers = st.sidebar.slider("Ek sath kitne Browser kholne hain?", 1, 10, 5)

# --- BUTTON 1: SCAN ---
st.write("### 🛠️ Step 1: Saari Shifton Ki Pakki List Banayein")
if st.button("1. Scan All Shifts"):
    with st.spinner("Site ko scroll karke saari shiften dhundhi ja rahi hain..."):
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
            
        # Check karna ki kitni download ho chuki hain aur kitni baaki hain
        pending_shifts = [s for s in master_list if not is_shift_downloaded(s['unique_col'])]
        done_count = len(master_list) - len(pending_shifts)
        
        st.info(f"📊 Total Shifts: {len(master_list)} | ✅ Pehle se Downloaded: {done_count} | ⏳ Baaki: {len(pending_shifts)}")
        
        if pending_shifts:
            date_list_objs = [start_fetch_date + timedelta(days=x) for x in range((end_fetch_date - start_fetch_date).days + 1)]
            date_strs = {d.strftime('%d-%m-%Y'): d for d in date_list_objs}
            
            progress_bar = st.progress(0)
            st.warning(f"🚀 {num_browsers} browsers ek sath chal rahe hain. Agar phone lock ho jaye toh dobara yahi button dabana, data wahi se shuru hoga!")
            
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
        # Header Row
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
        
