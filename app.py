import streamlit as st
import pandas as pd
import os
import time
import re
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="SuperFast Shift Fetcher", layout="wide")
st.title("⚡ SuperFast 100+ Shifts Fetcher")
st.write("Yeh code 'Record Chart' dabayega, aur niche wale 'Neele Button (Mahine ke naam)' daba kar data nikalega.")

FILE_NAME = "All_Shifts_Master_Data.xlsx"

# ==========================================
# 2. HELPER FUNCTIONS (Table & Button Parser)
# ==========================================
MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

def parse_active_table(driver, target_dates, results_dict, col_key):
    """Jo naya table khulega, usme se 1 mahine ka data nikalna"""
    data_found = False
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            if table.is_displayed():
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    # Ek line me do hisse hote hain (Date-Result, Date-Result)
                    for i in range(0, len(cols) - 1, 2):
                        dt_text = cols[i].text.strip().lower()
                        val = cols[i+1].text.strip()
                        
                        if val and val != "XX" and val != "-" and val.lower() != "nan":
                            for t_date in target_dates:
                                dd1 = t_date.strftime('%d') 
                                dd2 = str(t_date.day)       
                                full_d = t_date.strftime('%d-%b-%Y').lower() 
                                
                                if dt_text == dd1 or dt_text == dd2 or full_d in dt_text:
                                    results_dict[t_date][col_key] = val
                                    data_found = True
    except:
        pass
    return data_found

# ==========================================
# 3. WORKER ENGINE (Fast Scraping Logic)
# ==========================================
def scrape_single_shift(shift_idx, col_key, start_date, end_date, date_list):
    """Ek akela worker jo ek shift ko pakdega, neele button dabayega aur wapas aayega"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except:
        return {}
    
    shift_data = {d: {} for d in date_list}
    
    try:
        driver.get("https://satta-king-fast.com/chart.php")
        time.sleep(3)
        
        # 1. 'Record Chart' button dhundhna aur click karna
        buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
        if shift_idx < len(buttons):
            target_btn = buttons[shift_idx]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(2.5) # Table khulne ka wait
            
            # 2. Loop: Table padho aur Neele Button daba kar piche jao
            current_check_date = end_date
            while current_check_date >= start_date.replace(day=1):
                # Data extract karo current open chart se
                parse_active_table(driver, date_list, shift_data, col_key)
                
                # Agar hum start date se bhi piche chala gaye, toh loop tod do
                if current_check_date.year < start_date.year or (current_check_date.year == start_date.year and current_check_date.month <= start_date.month):
                    break
                
                # 3. Neele Button (Blue Buttons with Month Names) Dhundhna
                # Logic: Find elements near the bottom that look like buttons and contain month names
                blue_buttons_clicked = False
                all_links = driver.find_elements(By.TAG_NAME, "a") + driver.find_elements(By.TAG_NAME, "button")
                
                for link in all_links:
                    if link.is_displayed():
                        link_text = link.text.strip().lower()
                        # Agar button pe kisi mahine ka naam likha hai (e.g. "Oct", "Nov 2023")
                        is_month_btn = any(m in link_text for m in MONTH_NAMES)
                        
                        # Humko pichle mahine me jana hai (Usually left button hota hai, jiska date current se chota hota hai)
                        if is_month_btn:
                            # Hum left wala / pichla dabana chahte hain
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(3) # Naya mahina load hone ka wait
                            blue_buttons_clicked = True
                            break # Sirf ek baar dabana hai aur fir se table padhna hai
                
                # Agar neela button nahi mila (matlab site par piche ka data nahi hai) toh break kar do
                if not blue_buttons_clicked:
                    break
                
                # Mahina piche khiskana apne tracker mein
                month = current_check_date.month - 1
                year = current_check_date.year
                if month == 0:
                    month = 12
                    year -= 1
                current_check_date = current_check_date.replace(year=year, month=month)
                
    except Exception as e:
        pass
    finally:
        driver.quit()
        
    return shift_data

# ==========================================
# 4. MAIN CONTROLLER (Multi-Threading)
# ==========================================
def fetch_fast_all_shifts(start_date, end_date):
    # Pehle ek baar site khol kar saari shiften aur unke naam/time list kar lo
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        service = Service("/usr/bin/chromedriver")
        main_driver = webdriver.Chrome(service=service, options=options)
        main_driver.get("https://satta-king-fast.com/chart.php")
        time.sleep(4)
    except:
        return "DRIVER_ERROR"
        
    buttons = main_driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
    
    strips_info = []
    seen_names = set()
    seen_times = {}
    unique_cols = []
    col_to_name = {}

    # Shift Name & Time Logic (Bina crash ke)
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
            elif rc_idx == 1:
                raw_text = lines[0]
                t_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if t_match:
                    time_str = t_match.group(1).upper()
                    name_str = re.sub(r'(?i)at\s*' + re.escape(t_match.group(0)), '', raw_text).strip()
                else:
                    name_str = raw_text.strip()
            
            t_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', time_str.upper())
            if t_match: time_str = t_match.group(1)
            
            if name_str != "Unknown" and name_str not in seen_names:
                seen_names.add(name_str)
                seen_times[time_str] = seen_times.get(time_str, 0) + 1
                u_col = time_str + (" " * (seen_times[time_str] - 1))
                
                unique_cols.append(u_col)
                col_to_name[u_col] = name_str
                strips_info.append({'idx': idx, 'col_key': u_col})
        except:
            continue
            
    main_driver.quit()

    if not strips_info:
        return "PARSE_ERROR"

    date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    master_results = {d: {} for d in date_list}
    
    total_shifts = len(strips_info)
    # SPEED OPTIMIZATION: 4 browsers ek sath kaam karenge
    MAX_THREADS = 4 
    st.info(f"🚀 Speed Booster On: {total_shifts} shiften mili hain. {MAX_THREADS} browsers ek sath piche kaam kar rahe hain. Neele button click ho rahe hain...")
    progress_bar = st.progress(0)

    # Multi-Threading Engine (Ye time ko 4 guna kam kar dega)
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for strip in strips_info:
            futures.append(executor.submit(scrape_single_shift, strip['idx'], strip['col_key'], start_date, end_date, date_list))
            
        completed = 0
        for future in futures:
            shift_res = future.result()
            # Data merge karna
            for d in date_list:
                if d in shift_res:
                    master_results[d].update(shift_res[d])
            completed += 1
            progress_bar.progress(int((completed / total_shifts) * 100))

    # Excel Tayari
    final_rows = []
    row_names = {"Date": "Date"}
    for c in unique_cols:
        row_names[c] = col_to_name[c]
    final_rows.append(row_names)
    
    for d in date_list:
        r = {"Date": d.strftime('%d-%m-%Y')}
        for c in unique_cols:
            r[c] = master_results[d].get(c, "")
        final_rows.append(r)

    df = pd.DataFrame(final_rows, columns=["Date"] + unique_cols)
    return df

# ==========================================
# 5. UI APP RUN
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")
start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana?):", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

if st.sidebar.button("Nikalna Shuru Karein (Fast Mode)"):
    with st.spinner("⏳ Neele mahino wale buttons par click karke data nikala ja raha hai..."):
        if start_fetch_date > end_fetch_date:
            st.error("Start Date theek karein.")
        else:
            df_new = fetch_fast_all_shifts(start_fetch_date, end_fetch_date)
            
            if isinstance(df_new, str):
                st.error(f"Error: {df_new}")
            elif df_new is not None and not df_new.empty:
                df_new.to_excel(FILE_NAME, index=False)
                st.success("✅ Kaam Poora Hua! Neele Button daba kar sara data nikal liya gaya hai.")
                st.dataframe(df_new)
                with open(FILE_NAME, "rb") as file:
                    st.download_button(label="📥 Download Data", data=file, file_name=FILE_NAME, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.error("Data fail.")
            
