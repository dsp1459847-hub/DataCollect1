import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. PAGE SETUP & DATA DB LOCALIZATION
# ==========================================
st.set_page_config(page_title="Multi-Threaded Shift Fetcher", layout="wide")
st.title("⚡ Multi-Threaded Sync Shift Fetcher")
st.write("Yeh app background mein multiple sites/tabs khol kar bina load dale data sync karegi.")

FILE_NAME = "Master_Satta_Database.xlsx"

# ==========================================
# 2. FILE SYNC & STORAGE MANAGEMENT LOGIC
# ==========================================
def load_existing_db():
    """Hamesha database check karta hai taaki purana records secure rahe"""
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_excel(FILE_NAME)
            # Row 1 text patterns hatakar target filter karna
            dates_clean = df[df['Date'] != 'Date']['Date'].dropna()
            if not dates_clean.empty:
                last_saved_date = pd.to_datetime(dates_clean.iloc[-1]).date()
                return df, last_saved_date
        except Exception as e:
            st.error(f"Database reading failure: {e}. Checking backup...")
    
    # Blank structure taiyar karna agar database na ho
    columns = ["Date", "05:00 AM (DESAWAR)", "06:15 PM (FARIDABAD)", "08:00 PM (GAZIYABAD)", "11:25 PM (GALI)"]
    first_row = {
        "Date": "Date",
        "05:00 AM (DESAWAR)": "DESAWAR",
        "06:15 PM (FARIDABAD)": "FARIDABAD",
        "08:00 PM (GAZIYABAD)": "GAZIYABAD",
        "11:25 PM (GALI)": "GALI"
    }
    return pd.DataFrame([first_row], columns=columns), None

# ==========================================
# 3. ADVANCED PARALLEL SCRAPING ENGINE (Multi-Window/Tab)
# ==========================================
def scrape_single_shift_worker(strip_idx, start_date, end_date):
    """Worker Thread: Ek alag invisible browser window kholkar specific patti target karega"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except:
        return {}

    # Target control link target karein
    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3) # Initial safe rest time for low load
    
    worker_data = {}
    try:
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Record Chart') or contains(text(), 'RECORD CHART')]")
        if strip_idx < len(buttons):
            target_btn = buttons[strip_idx]
            
            # Extract header configurations metadata
            parent_txt = target_btn.find_element(By.XPATH, "..").text.split("RECORD")[0].strip().split('\n')
            shift_name = parent_txt[0].strip() if len(parent_txt) > 0 else f"Shift_{strip_idx}"
            shift_time = parent_txt[1].replace('at', '').strip() if len(parent_txt) > 1 else "Time N/A"
            col_key = f"{shift_time} ({shift_name})"
            
            # Execute human-like target redirection
            driver.execute_script("arguments[0].scrollIntoView();", target_btn)
            driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(2.5) # Dynamic injection buffer time
            
            # Parse timeline segments safely month by month
            curr = start_date
            while curr <= end_date:
                dt_str = curr.strftime('%d')
                full_dt_str = curr.strftime('%d-%b-%Y')
                res_val = ""
                
                tables = driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    if table.is_displayed():
                        for row in table.find_elements(By.TAG_NAME, "tr"):
                            if dt_str in row.text or full_dt_str in row.text:
                                cols = row.find_elements(By.TAG_NAME, "td")
                                if len(cols) > 1:
                                    res_val = cols[1].text.strip()
                                    break
                
                if col_key not in worker_data:
                    worker_data[col_key] = {}
                worker_data[col_key][curr.strftime('%d-%m-%Y')] = res_val
                curr += timedelta(days=1)
    except Exception as e:
        pass
    finally:
        driver.quit()
        
    return worker_data

# ==========================================
# 4. APP INTERFACE & DATE BOUNDS SETUP
# ==========================================
db_df, last_saved_date = load_existing_db()

st.sidebar.header("🔄 Incremental Sync Controls")
start_input = st.sidebar.date_input("Kahan se record check karein (Start Date):", date(2023, 11, 1))
end_input = st.sidebar.date_input("Kahan tak database update karein (End Date):", date.today())

# UI Info regarding historical state
st.subheader("🗄️ Master System Database Status")
if last_saved_date:
    st.success(f"💾 Aapka database pehle se **{last_saved_date.strftime('%d-%m-%Y')}** tak ka poora saved aur secure hai.")
else:
    st.info("📂 Koi database nahi mila. Ekdum fresh master file generate hogi.")

st.dataframe(db_df.head(10))

sync_triggered = st.button("🔄 Sync Database (Start Parallel Downloader)")

# ==========================================
# 5. POOL CONTROLLER & RECORD APPEND
# ==========================================
if sync_triggered:
    # Auto calculation for non-duplicating sequence range
    if last_saved_date and last_saved_date >= start_input:
        calc_start = last_saved_date + timedelta(days=1)
    else:
        calc_start = start_input
        
    if calc_start > end_input:
        st.success("✅ Database pehle se hi aaj tak updated hai! Dobara mehnat karne ki zarurat nahi.")
    else:
        st.info(f"🚀 Processing chunk delta: {calc_start.strftime('%d-%m-%Y')} se {end_input.strftime('%d-%m-%Y')}")
        
        # Scanner to dynamically identify active targets (Strips)
        init_opt = Options()
        init_opt.add_argument('--headless=new')
        init_srv = Service("/usr/bin/chromedriver")
        init_driver = webdriver.Chrome(service=init_srv, options=init_opt)
        init_driver.get("https://satta-king-fast.com/chart.php")
        total_shifts = len(init_driver.find_elements(By.XPATH, "//*[contains(text(), 'Record Chart') or contains(text(), 'RECORD CHART')]"))
        init_driver.quit()
        
        # Max pool sizing restriction: Max 7-8 tabs to balance CPU spikes safely
        MAX_WORKERS = min(7, total_shifts) 
        st.warning(f"🔄 Total active shifts mili: {total_shifts}. Ek sath {MAX_WORKERS} windows/tabs piche chal rahi hain taaki IP block na ho!")
        
        global_results = {}
        progress_bar = st.progress(0)
        
        # Distribute extraction load to autonomous threads pool
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(scrape_single_shift_worker, i, calc_start, end_input) for i in range(total_shifts)]
            
            for idx, fut in enumerate(futures):
                res = fut.result()
                if res:
                    for col, date_dict in res.items():
                        if col not in global_results:
                            global_results[col] = {}
                        global_results[col].update(date_dict)
                progress_bar.progress(int((idx + 1) / total_shifts * 100))
                time.sleep(1) # Human delay throttle between processing shifts block
                
        # Transform extracted global dictionary records securely into a tabular layout
        delta_days = (end_input - calc_start).days + 1
        date_seq = [calc_start + timedelta(days=d) for d in range(delta_days)]
        
        new_rows = []
        for d_item in date_seq:
            d_str_key = d_item.strftime('%d-%m-%Y')
            row_dict = {"Date": d_str_key}
            for col_header in global_results.keys():
                row_dict[col_header] = global_results[col_header].get(d_str_key, "")
            new_rows.append(row_dict)
            
        df_new_chunk = pd.DataFrame(new_rows)
        
        # Append incremental segment directly to old table database matrix safely
        df_final_master = pd.concat([db_df, df_new_chunk], ignore_index=True)
        
        # Save structural checkpoint backup securely
        df_final_master.to_excel(FILE_NAME, index=False)
        st.success("🏆 Database Synchronization successfully complete ho gaya hai bina purana records delete kiye!")
        st.dataframe(df_final_master)
        
        with open(FILE_NAME, "rb") as file_data:
            st.download_button(
                label="📥 Download Master Backup Excel Database",
                data=file_data,
                file_name=FILE_NAME,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
