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
st.set_page_config(page_title="Live Shift Data Fetcher", layout="wide")
st.title("📊 Live Shift Data Fetcher")
st.write("Yeh app Pili/Safed pattiyon se sirf Start aur End date ke hisab se data nikalegi.")

FILE_NAME = "Fresh_Satta_Record.xlsx"

# ==========================================
# 2. CORE LIVE SCRAPING ENGINE (No Base Shift)
# ==========================================
def fetch_live_data(start_date, end_date):
    """Asli data fetch karne wala engine jo Record Chart par click karega"""
    options = Options()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-dev-shm-usage') 
    options.add_argument('--disable-gpu') 
    options.add_argument('--window-size=1920,1080') 
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        st.error("Driver Load Error! Kripya GitHub par 'packages.txt' file check karein.")
        return None

    # Site par jana
    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(4) # Site load hone ka intezar
    
    # Pattiyon (Strips) se Time aur Naam nikalna
    strips_info = []
    
    # 'RECORD CHART' wale sabhi buttons dhundhna
    record_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'RECORD CHART') or contains(text(), 'Record Chart')]")
    
    for idx, button in enumerate(record_buttons):
        try:
            # Patti ka poora text padhna
            strip_element = button.find_element(By.XPATH, "..")
            text = strip_element.text.split("RECORD")[0].strip()
            
            # Text ko tod kar Naam aur Time alag karna
            words = text.split()
            if len(words) >= 2:
                shift_name = words[0] # Pehla word naam hota hai
                
                # Time dhundhna (AM/PM ke hisab se)
                time_str = "Time N/A"
                for i in range(len(words)):
                    if words[i] in ['AM', 'PM'] and i > 0:
                        time_str = f"{words[i-1]} {words[i]}"
                        break
                
                strips_info.append({
                    'index': idx,
                    'name': shift_name,
                    'time': time_str,
                    'button': button
                })
        except:
            continue

    # Excel ka Structure Taiyar Karna
    # Row 1: Time, Row 2: Naam
    columns_time = ["Date"]
    row_names = {"Date": "Date"}
    
    for strip in strips_info:
        columns_time.append(strip['time'])
        row_names[strip['time']] = strip['name']
        
    all_data_rows = [row_names] # Pehli data row mein Naam aayenge
    
    # Dates ke hisab se Data Fetch karna
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%d-%b-%Y') # Site ka format
        daily_record = {
            "Date": current_date.strftime('%d-%m-%Y')
        }
        
        # Har patti ke Record chart par click karke data lana
        for strip in strips_info:
            data_number = "" # Khali jagah agar data na mile
            try:
                # Button par click karna
                driver.execute_script("arguments[0].scrollIntoView();", strip['button'])
                driver.execute_script("arguments[0].click();", strip['button'])
                time.sleep(1.5) # Table load hone ka wait
                
                # Niche khule hue table se is date ka number nikalna
                tables = driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    if table.is_displayed():
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        for row in rows:
                            # Agar date match ho jaye
                            if str(current_date.day) in row.text or date_str in row.text:
                                cols = row.find_elements(By.TAG_NAME, "td")
                                if len(cols) > 1:
                                    data_number = cols[1].text.strip()
                                    break
            except:
                pass 
                
            daily_record[strip['time']] = data_number
            
        all_data_rows.append(daily_record)
        current_date += timedelta(days=1)
        
    driver.quit()
    
    # Final DataFrame banana
    df = pd.DataFrame(all_data_rows, columns=columns_time)
    return df

# ==========================================
# 3. SIDEBAR MENUS
# ==========================================
st.sidebar.header("🗓️ Date Settings")

st.sidebar.subheader("Select Dates")
start_fetch_date = st.sidebar.date_input("Start Date:", date(2023, 11, 1))
end_fetch_date = st.sidebar.date_input("End Date:", date.today())

fetch_button = st.sidebar.button("Fetch Live Data")

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
if fetch_button:
    with st.spinner('⏳ Live site se fresh data laya ja raha hai. Kripya pratiksha karein...'):
        
        if start_fetch_date > end_fetch_date:
            st.error("Start Date, End Date se aage nahi ho sakti.")
        else:
            df_final = fetch_live_data(start_fetch_date, end_fetch_date)
            
            if df_final is not None and not df_final.empty:
                # Excel mein save karna
                df_final.to_excel(FILE_NAME, index=False)
                
                st.success("✅ Fresh Data successfully nikal liya gaya hai!")
                st.write("### 🆕 Excel Format Preview (Upar Time, Niche Naam)")
                st.dataframe(df_final)
                
                # Download File
                with open(FILE_NAME, "rb") as file:
                    st.download_button(
                        label="📥 Download Fresh Excel File",
                        data=file,
                        file_name=FILE_NAME,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("Data laane mein dikkat aayi. Driver aur Net connection check karein.")
                
