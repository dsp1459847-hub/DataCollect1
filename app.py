import streamlit as st
import pandas as pd
import os
import time
import re
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="100+ Shifts Original Fetcher", layout="wide")
st.title("📊 All 100+ Shifts Live Data Fetcher")
st.write("Ab yeh code site ke andar ke design (HTML) ko deep-scan karke saari shiften nikalega.")

FILE_NAME = "All_Shifts_Master_Data.xlsx"

# ==========================================
# 2. HELPER FUNCTIONS (Mahina & Table)
# ==========================================
def get_months_difference(d_today, d_start):
    return (d_today.year - d_start.year) * 12 + d_today.month - d_start.month

def parse_tables_for_dates(driver, target_dates, results_dict, col_key):
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            if table.is_displayed():
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 2:
                        dt_text = cols[0].text.strip().lower()
                        val = cols[1].text.strip()
                        
                        if val and val != "XX" and val != "-" and val.lower() != "nan":
                            for t_date in target_dates:
                                dd1 = t_date.strftime('%d') 
                                dd2 = str(t_date.day)       
                                full_d = t_date.strftime('%d-%b-%Y').lower() 
                                
                                if dt_text == dd1 or dt_text == dd2 or full_d in dt_text:
                                    results_dict[t_date][col_key] = val
    except:
        pass

# ==========================================
# 3. CORE SCRAPING ENGINE (Deep HTML Climber)
# ==========================================
def fetch_all_100_shifts(start_date, end_date):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # Anti-Blocker
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except:
        return "DRIVER_ERROR"

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(6) 

    buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
    
    if not buttons:
        driver.quit()
        return "BLOCK_ERROR"

    strips_info = []
    
    # ---------------------------------------------------------
    # ERROR FIX: Deep HTML Climber Logic
    # ---------------------------------------------------------
    for btn in buttons:
        try:
            node = btn
            lines = []
            rc_idx = -1
            
            # Button se upar 5 level tak HTML padhega jab tak Naam na mil jaye
            for _ in range(5):
                node = node.find_element(By.XPATH, "..")
                lines = [x.strip() for x in node.text.split('\n') if x.strip()]
                
                for i, line in enumerate(lines):
                    if "record chart" in line.lower():
                        rc_idx = i
                        break
                
                if rc_idx >= 1: # Yaani Record Chart ke upar Naam aur Time mil gaya
                    break
            
            if rc_idx == -1:
                continue

            name_str = "Unknown"
            time_str = "Time N/A"

            # Agar alag-alag lines mein hain
            if rc_idx >= 2:
                name_str = lines[rc_idx - 2].strip()
                time_str = lines[rc_idx - 1].strip()
            # Agar ek hi line mein Naam aur Time juda hua hai
            elif rc_idx == 1:
                raw_text = lines[0]
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if time_match:
                    time_str = time_match.group(1).upper()
                    name_str = re.sub(r'(?i)at\s*' + re.escape(time_match.group(0)), '', raw_text).strip()
                else:
                    name_str = raw_text.strip()
            
            # Sirf exact Time nikalna (baaki kooda hatana)
            time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', time_str, re.IGNORECASE)
            if time_match:
                time_str = time_match.group(1).upper()

            # Clean aur filter
            if name_str and name_str != "Unknown" and len(name_str) < 40:
                strips_info.append({'name': name_str, 'time': time_str, 'btn': btn})
        except:
            continue

    if not strips_info:
        driver.quit()
        return "PARSE_ERROR"

    # ==========================================
    # Columns setup aur Duplicate Fix
    seen_names = set()
    seen_times = {}
    unique_cols = []
    col_to_name = {}
    valid_strips = []

    for strip in strips_info:
        if strip['name'] not in seen_names:
            seen_names.add(strip['name'])
            b_time = strip['time']
            
            seen_times[b_time] = seen_times.get(b_time, 0) + 1
            u_col = b_time + (" " * (seen_times[b_time] - 1))
            
            strip['unique_col'] = u_col
            unique_cols.append(u_col)
            col_to_name[u_col] = strip['name']
            valid_strips.append(strip)

    # ==========================================
    # Extracting Data
    date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    results_by_date = {d: {} for d in date_list}
    months_to_go_back = get_months_difference(date.today(), start_date)
    
    progress_bar = st.progress(0)
    total_strips = len(valid_strips)
    st.info(f"✅ HTML Design Bypass! Site par {total_strips} shiften mil gayi hain. Data fetch ho raha hai...")

    for idx, strip in enumerate(valid_strips):
        col_key = strip['unique_col']
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", strip['btn'])
            time.sleep(1)
            driver.execute_script("arguments[0].click();", strip['btn'])
            time.sleep(2.5) 
            
            parse_tables_for_dates(driver, date_list, results_by_date, col_key)
            
            if months_to_go_back > 0:
                for _ in range(months_to_go_back):
                    try:
                        prev_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '<') or contains(translate(text(), 'PREV', 'prev'), 'prev') or contains(translate(text(), 'PICHLA', 'pichla'), 'pichla')]")
                        clicked = False
                        for pb in prev_btns:
                            if pb.is_displayed():
                                driver.execute_script("arguments[0].click();", pb)
                                time.sleep(2)
                                clicked = True
                                break
                        if clicked:
                            parse_tables_for_dates(driver, date_list, results_by_date, col_key)
                        else:
                            break
                    except:
                        break 
        except:
            pass
            
        progress_bar.progress(int((idx + 1) / total_strips * 100))

    driver.quit()

    # Excel me feed karna
    final_rows = []
    row_names = {"Date": "Date"}
    for c in unique_cols:
        row_names[c] = col_to_name[c]
    final_rows.append(row_names)
    
    for d in date_list:
        r = {"Date": d.strftime('%d-%m-%Y')}
        for c in unique_cols:
            r[c] = results_by_date[d].get(c, "") 
        final_rows.append(r)

    df = pd.DataFrame(final_rows, columns=["Date"] + unique_cols)
    return df

# ==========================================
# 4. SIDEBAR & EXECUTION
# ==========================================
st.sidebar.header("🗓️ Dates Set Karein")

start_fetch_date = st.sidebar.date_input("Start Date (Kitna purana chahiye?):", date(2026, 3, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

fetch_btn = st.sidebar.button("Nikalna Shuru Karein (Start)")

if fetch_btn:
    with st.spinner("⏳ App site ke naye design ke andar ghus kar data scan kar rahi hai..."):
        df_new = fetch_all_100_shifts(start_fetch_date, end_fetch_date)
        
        if isinstance(df_new, str):
            if df_new == "DRIVER_ERROR":
                st.error("❌ Driver setup error. GitHub ki packages.txt check karein.")
            elif df_new == "BLOCK_ERROR":
                st.error("❌ Site ne block kiya (CloudFlare). Kripya kuch der baad try karein.")
            elif df_new == "PARSE_ERROR":
                st.error("❌ Site khul gayi par design abhi bhi read nahi ho raha. Check karein site down toh nahi.")
        
        elif df_new is not None and not df_new.empty:
            df_new.to_excel(FILE_NAME, index=False)
            
            st.success("✅ Kaam Poora Hua! Poori shiften accurately nikal li gayi hain.")
            st.dataframe(df_new)
            
            with open(FILE_NAME, "rb") as file:
                st.download_button(
                    label="📥 Download Corrected Excel File",
                    data=file,
                    file_name=FILE_NAME,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("❌ Kuch unknown problem aayi hai.")
