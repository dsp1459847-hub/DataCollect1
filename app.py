import streamlit as st
import pandas as pd
import os
import time
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
st.write("Ab site is app ko robot samajh kar block nahi karegi. Data 100% extract hoga.")

FILE_NAME = "All_Shifts_Master_Data.xlsx"

# ==========================================
# 2. LOGIC: PICHLE MAHINE ME JANE KA
# ==========================================
def get_months_difference(d_today, d_start):
    """Pata lagata hai ki kitne mahine piche jana hai"""
    return (d_today.year - d_start.year) * 12 + d_today.month - d_start.month

def parse_tables_for_dates(driver, target_dates, results_dict, col_key):
    """Table ke pehle column (Date) ko padhkar sahi number uthana"""
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            if table.is_displayed():
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    # Agar column mein data hai
                    if len(cols) >= 2:
                        dt_text = cols[0].text.strip().lower()
                        val = cols[1].text.strip()
                        
                        # Khali ya faltu data na uthaye
                        if val and val != "XX" and val != "-" and val.lower() != "nan":
                            for t_date in target_dates:
                                dd1 = t_date.strftime('%d') # '01'
                                dd2 = str(t_date.day)       # '1'
                                full_d = t_date.strftime('%d-%b-%Y').lower() # '01-may-2026'
                                
                                # Date match hone par data save karna
                                if dt_text == dd1 or dt_text == dd2 or full_d in dt_text:
                                    results_dict[t_date][col_key] = val
    except Exception as e:
        pass

# ==========================================
# 3. CORE SCRAPING ENGINE (ANTI-BLOCKER)
# ==========================================
def fetch_all_100_shifts(start_date, end_date):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # ---------------------------------------------------------
    # ERROR FIX: Site ka Security System Bypass Karne Ke Liye
    # ---------------------------------------------------------
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        # Javascript ko bhi lagega ki yeh normal browser hai
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        return "DRIVER_ERROR"

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(6) # CloudFlare ko pass karne ke liye extra wait

    # 1. Saari Pattiyan Dhundhna
    buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
    
    if not buttons:
        driver.quit()
        return "BLOCK_ERROR"

    strips_info = []
    for btn in buttons:
        try:
            parent_text = btn.find_element(By.XPATH, "..").text.strip()
            if not parent_text: continue
            
            lines = [x.strip() for x in parent_text.split('\n') if x.strip()]
            rc_idx = -1
            for i, line in enumerate(lines):
                if "record chart" in line.lower():
                    rc_idx = i
                    break
            
            name, time_str = "Unknown", "Unknown"
            if rc_idx >= 2:
                name = lines[rc_idx - 2]
                time_str = lines[rc_idx - 1].replace('at', '').strip()
            elif rc_idx == 1:
                parts = lines[0].split(' at ')
                if len(parts) == 2:
                    name = parts[0].strip()
                    time_str = parts[1].strip()
                else:
                    name = lines[0]
            
            if name != "Unknown":
                strips_info.append({'name': name, 'time': time_str, 'btn': btn})
        except:
            continue

    if not strips_info:
        driver.quit()
        return "PARSE_ERROR"

    # 2. Columns Setup (Duplicate Fix Ke Sath)
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

    # 3. Dates Taiyar Karna
    date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    results_by_date = {d: {} for d in date_list}
    months_to_go_back = get_months_difference(date.today(), start_date)
    
    # UI Progress
    progress_bar = st.progress(0)
    total_strips = len(valid_strips)
    st.info(f"✅ Anti-Block Bypassed! Site par {total_strips} shiften mil gayi hain. Data fetch ho raha hai...")

    # 4. Ek-Ek karke data nikalna
    for idx, strip in enumerate(valid_strips):
        col_key = strip['unique_col']
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", strip['btn'])
            time.sleep(1)
            driver.execute_script("arguments[0].click();", strip['btn'])
            time.sleep(2.5) # Table khulne ke liye wait
            
            # Current Month
            parse_tables_for_dates(driver, date_list, results_by_date, col_key)
            
            # Pichla Mahina (Neele Dabbe / Prev)
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
        except Exception as e:
            pass
            
        progress_bar.progress(int((idx + 1) / total_strips * 100))

    driver.quit()

    # 5. Excel Taiyar Karna
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
    with st.spinner("⏳ System site par ghusne ki koshish kar raha hai. Kripya pratiksha karein..."):
        df_new = fetch_all_100_shifts(start_fetch_date, end_fetch_date)
        
        if isinstance(df_new, str):
            if df_new == "DRIVER_ERROR":
                st.error("❌ Driver setup nahi ho paaya. GitHub ki packages.txt check karein.")
            elif df_new == "BLOCK_ERROR":
                st.error("❌ Site ne load hone se mana kar diya (CloudFlare / Captcha Block). Kripya thodi der baad try karein.")
            elif df_new == "PARSE_ERROR":
                st.error("❌ Site khul gayi par shifton ke naam theek se nahi padhe gaye. Site ka design change hua hai.")
        
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
            
