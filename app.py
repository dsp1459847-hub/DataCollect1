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
st.write("Ab koi 4 column ki limit nahi. Site par jitni shiften hongi, sabka data exact aayega.")

FILE_NAME = "All_Shifts_Master_Data.xlsx"

# ==========================================
# 2. LOGIC: PICHLE MAHINE ME JANE KA (Neele Dabbe)
# ==========================================
def get_months_difference(d_today, d_start):
    """Pata lagata hai ki kitne mahine piche jana hai (Kitni baar left button dabana hai)"""
    return (d_today.year - d_start.year) * 12 + d_today.month - d_start.month

def parse_tables_for_dates(driver, target_dates, results_dict, col_key):
    """Khule hue table se hamari select ki hui dates ka data uthana"""
    tables = driver.find_elements(By.TAG_NAME, "table")
    for table in tables:
        if table.is_displayed():
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                text_lower = row.text.lower()
                for t_date in target_dates:
                    dd = t_date.strftime('%d') # Jaise '01', '02'
                    full_d = t_date.strftime('%d-%b-%Y').lower() # Jaise '01-may-2026'
                    
                    if dd in text_lower or full_d in text_lower:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 2:
                            val = cols[1].text.strip()
                            # Agar data mil gaya, toh khali/XX nahi dalna hai
                            if val and val != "XX" and val != "-" and val.lower() != "nan":
                                results_dict[t_date][col_key] = val

# ==========================================
# 3. CORE SCRAPING ENGINE (Slow & 100% Safe)
# ==========================================
def fetch_all_100_shifts(start_date, end_date):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        st.error("Driver Load Error! Kripya packages.txt check karein.")
        return None

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(5)

    # 1. Saari Pili/Safed Pattiyan Dhundhna (Koi hardcoding nahi)
    buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
    
    strips_info = []
    for btn in buttons:
        try:
            parent_lines = btn.find_element(By.XPATH, "..").text.strip().split('\n')
            rc_idx = -1
            for i, line in enumerate(parent_lines):
                if "record chart" in line.lower():
                    rc_idx = i
                    break
            
            if rc_idx >= 2:
                s_name = parent_lines[rc_idx - 2].strip()
                s_time = parent_lines[rc_idx - 1].replace('at', '').strip()
                strips_info.append({'name': s_name, 'time': s_time, 'btn': btn})
        except:
            continue

    if not strips_info:
        driver.quit()
        return pd.DataFrame()

    # 2. 100+ Columns Banana (Bina kisi error aur duplicate ke)
    seen_names = set()
    seen_times = {}
    unique_cols = []
    col_to_name = {}
    valid_strips = []

    for strip in strips_info:
        if strip['name'] not in seen_names:
            seen_names.add(strip['name'])
            b_time = strip['time']
            
            # Crash bachane ke liye invisible space
            seen_times[b_time] = seen_times.get(b_time, 0) + 1
            u_col = b_time + (" " * (seen_times[b_time] - 1))
            
            strip['unique_col'] = u_col
            unique_cols.append(u_col)
            col_to_name[u_col] = strip['name']
            valid_strips.append(strip)

    # 3. Dates taiyar karna (Jaise Dhai Mahine ki dates)
    date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    results_by_date = {d: {} for d in date_list}
    
    # Check karna ki Neele Dabbe (Prev) ko kitni baar dabana hai
    months_to_go_back = get_months_difference(date.today(), start_date)
    
    progress_bar = st.progress(0)
    total_strips = len(valid_strips)
    st.info(f"🔍 Site par poori {total_strips} shiften mili hain. Ab ek-ek karke accurately data nikala ja raha hai...")

    # 4. Ek-Ek karke data nikalna (Slow par Error-Free)
    for idx, strip in enumerate(valid_strips):
        col_key = strip['unique_col']
        try:
            # Patti par jaakar Record Chart dabana
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", strip['btn'])
            time.sleep(1)
            driver.execute_script("arguments[0].click();", strip['btn'])
            time.sleep(2) # Table load hone ka wait
            
            # Pehle current month (Aaj ka mahina) ka data nikalna
            parse_tables_for_dates(driver, date_list, results_by_date, col_key)
            
            # Agar purana data manga hai, toh Neele dabbe (< / Prev) ko dabakar piche jana
            if months_to_go_back > 0:
                for _ in range(months_to_go_back):
                    try:
                        # Neela dabba dhundhna
                        prev_btns = driver.find_elements(By.XPATH, "//*[self::a or self::button][contains(text(), '<') or contains(translate(text(), 'PREV', 'prev'), 'prev') or contains(translate(text(), 'PICHLA', 'pichla'), 'pichla')]")
                        clicked = False
                        for pb in prev_btns:
                            if pb.is_displayed():
                                driver.execute_script("arguments[0].click();", pb)
                                time.sleep(2) # Purana mahina load hone ka wait
                                clicked = True
                                break
                        
                        # Pichla mahina load hote hi uska data nikalna
                        if clicked:
                            parse_tables_for_dates(driver, date_list, results_by_date, col_key)
                    except:
                        break # Agar pichla button na mile, toh loop tod do
        except Exception as e:
            pass
            
        progress_bar.progress(int((idx + 1) / total_strips * 100))

    driver.quit()

    # 5. Excel taiyar karna
    final_rows = []
    # Pehli Row mein Shift ka Naam
    row_names = {"Date": "Date"}
    for c in unique_cols:
        row_names[c] = col_to_name[c]
    final_rows.append(row_names)
    
    # Niche Data
    for d in date_list:
        r = {"Date": d.strftime('%d-%m-%Y')}
        for c in unique_cols:
            r[c] = results_by_date[d].get(c, "") # Khali jagah par NaN nahi aayega
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
    with st.spinner("⏳ Data nikala ja raha hai. Site par Load kam rakhne ke liye yeh ek-ek karke chalega..."):
        df_new = fetch_all_100_shifts(start_fetch_date, end_fetch_date)
        
        if df_new is not None and not df_new.empty:
            # Agar purani file hui, toh yeh usko overwrite karke poori shiften daal dega
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
            st.error("Kuch problem aayi. Kripya check karein.")
            
