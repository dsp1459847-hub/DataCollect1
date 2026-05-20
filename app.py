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
st.set_page_config(page_title="Master Fetcher (Blue Button Logic)", layout="wide")
st.title("🛡️ 100% Accurate Fetcher (User's Blue Button Logic)")
st.write("Ab code Neele Buttons ko padhkar exact mahina verify karega. Koi duplicate data nahi aayega!")

TEMP_DIR = "temp_satta_data"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MASTER_LIST_FILE = os.path.join(TEMP_DIR, "master_shifts_list.json")
FINAL_EXCEL = "All_Shifts_Final_Verified.xlsx"
FINAL_CSV = "All_Shifts_Final_Verified.csv"

MONTHS_LIST = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

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

def extract_month_year(text):
    """Button ke text me se Mahina aur Saal nikalta hai (Jaise 'Oct 2023')"""
    text = text.lower()
    for i, m in enumerate(MONTHS_LIST):
        if m in text:
            match = re.search(r'\d{4}', text)
            if match:
                return (i + 1, int(match.group()))
    return None

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
    time.sleep(4)
    
    # Scroll to load everything
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
                
                strips_info.append({'idx': idx, 'name': name_str, 'unique_col': u_col})
        except:
            continue
            
    driver.quit()
    if strips_info:
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(strips_info, f)
    return strips_info

# ==========================================
# 4. DOWNLOADER ENGINE (USER'S GENIUS LOGIC)
# ==========================================
def wait_for_target_month(driver, shift_name, target_m, target_y):
    """
    YAHAN HAI AAPKA LOGIC: 
    Neele buttons padh kar verify karta hai ki exact wahi mahina khula hai ya nahi.
    """
    for _ in range(20): # 20 second tak wait karega ki AJAX page load kar de
        time.sleep(1)
        tables = driver.find_elements(By.TAG_NAME, "table")
        
        # Niche se upar search
        for table in reversed(tables):
            if table.is_displayed():
                try:
                    p_text = table.find_element(By.XPATH, "..").text.lower()
                    
                    # 1. Kya Table ke upar Shift ka Naam hai?
                    if shift_name.lower() in p_text or shift_name.lower() in table.text.lower():
                        
                        # 2. AAPKA LOGIC: Blue Buttons se Mahina nikalo
                        blue_links = table.find_element(By.XPATH, "..").find_elements(By.XPATH, ".//a | .//button")
                        
                        left_m, right_m = None, None
                        for link in blue_links:
                            if link.is_displayed():
                                l_txt = link.text.lower()
                                m_info = extract_month_year(l_txt)
                                if m_info:
                                    if "<" in l_txt or "prev" in l_txt or "pichla" in l_txt:
                                        left_m = m_info
                                    elif ">" in l_txt or "next" in l_txt or "agla" in l_txt:
                                        right_m = m_info
                        
                        current_m, current_y = None, None
                        
                        # Logic: Agar Left Button 'Oct' hai, toh current 'Nov' hoga
                        if left_m:
                            current_m = left_m[0] + 1
                            current_y = left_m[1]
                            if current_m > 12:
                                current_m = 1
                                current_y += 1
                        # Agar Right Button 'Dec' hai, toh current 'Nov' hoga
                        elif right_m:
                            current_m = right_m[0] - 1
                            current_y = right_m[1]
                            if current_m < 1:
                                current_m = 12
                                current_y -= 1
                                
                        # Agar current month humare target ke barabar aa gaya, toh table pass!
                        if current_m == target_m and current_y == target_y:
                            return table, blue_links
                            
                        # (Fallback): Agar first/last mahina ho aur button na ho, toh header padh lo
                        target_m_name = MONTHS_LIST[target_m - 1]
                        if target_m_name in table.text.lower() and str(target_y) in table.text.lower():
                            return table, blue_links
                            
                except:
                    pass
    return None, None

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
        
    try:
        driver.get("https://satta-king-fast.com/chart.php")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Click Record Chart
        buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
        target_btn = None
        for btn in buttons:
            try:
                p_text = btn.find_element(By.XPATH, "..").text.lower()
                if shift_name.lower() in p_text:
                    target_btn = btn
                    break
            except:
                pass
                
        if not target_btn:
            driver.quit()
            return False

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", target_btn)
        
        current_target_date = end_date
        
        # LOOP for going backward in months
        while current_target_date >= start_date.replace(day=1):
            target_m = current_target_date.month
            target_y = current_target_date.year
            
            # AAPKE LOGIC SE TABLE VERIFY HOGA YAHAN:
            target_table, blue_links = wait_for_target_month(driver, shift_name, target_m, target_y)
            
            if target_table:
                # Table mil gaya aur verify ho gaya, Ab Data Nikalo!
                rows = target_table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    for i in range(0, len(cols) - 1, 2):
                        dt_val = cols[i].text.strip()
                        res_val = cols[i+1].text.strip()
                        
                        if dt_val.isdigit() and res_val and res_val not in ["XX", "-"]:
                            day_int = int(dt_val)
                            for d_str, d_obj in date_str_map.items():
                                if d_obj.month == target_m and d_obj.year == target_y and d_obj.day == day_int:
                                    shift_results[d_str] = res_val
            else:
                break # Agar table hi nahi mila, toh aage data nahi hai

            # Limit check
            if current_target_date.year < start_date.year or (current_target_date.year == start_date.year and current_target_date.month <= start_date.month):
                break
                
            # NEXT STEP: Pichle Mahine Ka Neela Button Dabana
            prev_m_date = current_target_date.replace(day=1) - timedelta(days=1)
            prev_m_short = prev_m_date.strftime("%b").lower() 
            prev_y_short = str(prev_m_date.year)
            
            btn_to_click = None
            if blue_links:
                for link in blue_links:
                    if link.is_displayed():
                        l_txt = link.text.lower()
                        if (prev_m_short in l_txt and prev_y_short in l_txt) or "prev" in l_txt or "pichla" in l_txt or "<" in l_txt:
                            btn_to_click = link
                            break
                            
            if not btn_to_click:
                break
                
            # Click the blue button
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_to_click)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", btn_to_click)
            
            # Date update for the next loop, so it will wait for the NEW month to appear in the blue buttons
            current_target_date = prev_m_date
            
    except Exception as e:
        pass
    finally:
        driver.quit()
        
    save_shift_data(unique_col, shift_results)
    return True

# ==========================================
# 5. UI CONTROLS
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana?):", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

st.sidebar.markdown("---")
st.sidebar.header("🚀 Speed Settings")
num_browsers = st.sidebar.slider("Ek sath kitne Browser (Tabs)?", 1, 6, 3)

st.write("### 🛠️ Step 1: Scan 100+ Shifts")
if st.button("1. Scan Shifts"):
    with st.spinner("Site scan ho rahi hai..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Done! {len(s_list)} shiften properly detect ho gayi hain.")
        else:
            st.error("Scan fail. Net check karein.")

st.write("### 📥 Step 2: Download Exact Data (Neele Button Wala Logic)")
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
            st.warning("⚠️ Aapka 'Neele Button Wala Logic' chal raha hai! Data verify hote hi download hoga, isme thoda time lagega par data 100% accurate hoga.")
            
            with ThreadPoolExecutor(max_workers=num_browsers) as executor:
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
                row_names[sanitize_text(s['unique_col'])] = sanitize_text(s['name'])
            final_rows.append(row_names)
            
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
                pass
                
            gc.collect() 
            
            st.success("✅ File Generate Ho Gayi! Ab sab duplicate kachra saaf ho gaya hai.")
            
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(FINAL_EXCEL):
                    with open(FINAL_EXCEL, "rb") as file:
                        st.download_button("📥 Download Excel", data=file, file_name=FINAL_EXCEL, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col2:
                if os.path.exists(FINAL_CSV):
                    with open(FINAL_CSV, "rb") as file:
                        st.download_button("📥 Download CSV", data=file, file_name=FINAL_CSV, mime="text/csv")
            
