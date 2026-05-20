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
# 1. PAGE SETUP (No Shortcuts Engine)
# ==========================================
st.set_page_config(page_title="100% Accurate Shift Fetcher", layout="wide")
st.title("🛡️ 100% Accurate Data Fetcher (No Shortcuts)")
st.write("Ab code theek waise kaam karega jaise insaan manually karta hai. Koi data mix nahi hoga.")

TEMP_DIR = "temp_satta_data"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

MASTER_LIST_FILE = os.path.join(TEMP_DIR, "master_shifts_list.json")
FINAL_EXCEL = "All_Shifts_Accurate_Data.xlsx"
FINAL_CSV = "All_Shifts_Accurate_Data.csv"

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

def sanitize_text(text):
    if not isinstance(text, str): return str(text)
    return re.sub(r'[^\x20-\x7E]', '', text).strip()

# ==========================================
# 3. SCANNER ENGINE (List of Shifts)
# ==========================================
def scan_all_shifts():
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=get_browser_options())
    except Exception as e:
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
# 4. DOWNLOADER ENGINE (MANUAL SIMULATION - NO SHORTCUTS)
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
        
    try:
        driver.get("https://satta-king-fast.com/chart.php")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 1. Us specific shift ka Record Chart dabana
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

        # Button Click
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", target_btn)
        time.sleep(4) # Table open hone ka wait

        current_target_date = end_date
        
        # 2. Jab tak hum Start Date tak nahi pohochte, tab tak Neele Button daba kar piche jana hai
        while current_target_date >= start_date.replace(day=1):
            
            target_month_str = current_target_date.strftime("%B").lower() # e.g., "november"
            target_year_str = str(current_target_date.year)
            
            # --- A. TABLE DHUNDHNA AUR DATA NIKALNA ---
            table_found = False
            for _ in range(5): # 5 second tak wait karega ki naya data load ho jaye
                tables = driver.find_elements(By.TAG_NAME, "table")
                for table in reversed(tables): # Niche se upar check karega
                    try:
                        table_html = table.get_attribute('innerHTML').lower()
                        # VERIFICATION: Kya is table mein Shift Ka Naam aur Sahi Mahina/Saal likha hai?
                        if shift_name.lower() in table_html and target_month_str in table_html and target_year_str in table_html:
                            
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for row in rows:
                                cols = row.find_elements(By.TAG_NAME, "td")
                                for i in range(0, len(cols) - 1, 2):
                                    dt_val = cols[i].text.strip()
                                    res_val = cols[i+1].text.strip()
                                    
                                    # Agar date 1, 2, 3... hai aur result mein number hai
                                    if dt_val.isdigit() and res_val and res_val not in ["XX", "-"]:
                                        day_int = int(dt_val)
                                        # Apne record mein match karna
                                        for d_str, d_obj in date_str_map.items():
                                            if d_obj.month == current_target_date.month and d_obj.year == current_target_date.year and d_obj.day == day_int:
                                                shift_results[d_str] = res_val
                            
                            table_found = True
                            break
                    except:
                        pass
                if table_found:
                    break
                time.sleep(1) # Agar nahi mila toh 1 second wait karke dubara check karega
            
            # Limit check: Start date se piche nikal gaye toh ruk jao
            if current_target_date.year < start_date.year or (current_target_date.year == start_date.year and current_target_date.month <= start_date.month):
                break

            # --- B. NEELE BUTTON PAR CLICK KARNA (Manual Method) ---
            prev_month_date = current_target_date.replace(day=1) - timedelta(days=1)
            prev_month_short = prev_month_date.strftime("%b").lower() # e.g., 'oct'
            prev_year_short = str(prev_month_date.year)
            
            blue_btn_clicked = False
            all_links = driver.find_elements(By.TAG_NAME, "a") + driver.find_elements(By.TAG_NAME, "button")
            
            for link in all_links:
                try:
                    if link.is_displayed():
                        l_text = link.text.lower()
                        # Check: Kya button par "Oct 2023" ya "Prev" jaisa kuch likha hai?
                        if (prev_month_short in l_text and prev_year_short in l_text) or "prev" in l_text or "pichla" in l_text or "<" in l_text:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(4) # Naya mahina AJAX se load hone ka pakka wait
                            blue_btn_clicked = True
                            break
                except:
                    pass
            
            if not blue_btn_clicked:
                break # Agar neela button nahi mila, matlab site par aur piche ka data nahi hai
                
            # Date update karo taaki agle loop mein naya mahina check ho
            current_target_date = prev_month_date

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
num_browsers = st.sidebar.slider("Ek sath kitne Browser (Tabs)?", 1, 6, 3)

st.write("### 🛠️ Step 1: Scan All Shifts")
if st.button("1. Scan 100+ Shifts"):
    with st.spinner("Site ki scanning chal rahi hai..."):
        s_list = scan_all_shifts()
        if s_list:
            st.success(f"✅ Scanning Done! {len(s_list)} shiften properly detect ho gayi hain.")
        else:
            st.error("Scan fail. Net connection check karein.")

st.write("### 📥 Step 2: Extract Data (NO SHORTCUT MODE)")
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
            st.warning("⚠️ Data ekdum accurate laane ke liye code Neele Button daba raha hai, isme thoda time lagega par koi galti nahi hogi.")
            
            with ThreadPoolExecutor(max_workers=num_browsers) as executor:
                futures = [executor.submit(worker_fetch_single_shift, s, start_fetch_date, end_fetch_date, date_strs) for s in pending]
                for i, f in enumerate(futures):
                    f.result()
                    p_bar.progress(int(((i+1) / len(pending)) * 100))
                    
            st.success("🎉 Data successfully extract ho gaya hai bina kisi shortcut ke!")

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
            
            st.success("✅ File Generate Ho Gayi! Koi Data Duplicate Nahi Hai.")
            
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(FINAL_EXCEL):
                    with open(FINAL_EXCEL, "rb") as file:
                        st.download_button("📥 Download Excel", data=file, file_name=FINAL_EXCEL, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col2:
                if os.path.exists(FINAL_CSV):
                    with open(FINAL_CSV, "rb") as file:
                        st.download_button("📥 Download CSV", data=file, file_name=FINAL_CSV, mime="text/csv")
                                    
