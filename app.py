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
# 2. CORE LIVE SCRAPING ENGINE (Crash-Proof)
# ==========================================
def fetch_live_data(start_date, end_date):
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
    time.sleep(4) 
    
    strips_info = []
    
    # 'RECORD CHART' wale sabhi buttons dhundhna
    record_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'RECORD CHART') or contains(text(), 'Record Chart')]")
    
    for idx, button in enumerate(record_buttons):
        try:
            strip_element = button.find_element(By.XPATH, "..")
            text = strip_element.text.split("RECORD")[0].strip()
            
            words = text.split()
            if len(words) >= 2:
                shift_name = words[0] 
                
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

    # ---------------------------------------------------------
    # ERROR FIX: Duplicate Column Hamesha Ke Liye Khatam
    # ---------------------------------------------------------
    columns_time = ["Date"]
    row_names = {"Date": "Date"}
    
    seen_shift_names = set() # Check karne ke liye ki shift pehle aa chuki hai ya nahi
    unique_strips = []
    
    for strip in strips_info:
        # Agar yeh shift name pehle nahi dekha gaya hai, tabhi isko list mein daalna hai
        if strip['name'] not in seen_shift_names:
            seen_shift_names.add(strip['name'])
            
            unique_col_name = f"{strip['time']} ({strip['name']})"
            
            # Agar fir bhi galti se column name match kar jaye (100% safety)
            while unique_col_name in columns_time:
                unique_col_name += " *"
                
            strip['unique_col'] = unique_col_name
            columns_time.append(unique_col_name)
            row_names[unique_col_name] = strip['name']
            
            unique_strips.append(strip) # Sirf unique strips ko aage click karne ke liye save kiya
            
    all_data_rows = [row_names] 
    
    # Dates ke hisab se Data Fetch karna
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%d-%b-%Y') 
        daily_record = {
            "Date": current_date.strftime('%d-%m-%Y')
        }
        
        # Ab sirf UNIQUE strips ke button par click karega (Koi duplicate clash nahi hoga)
        for strip in unique_strips:
            data_number = "" 
            try:
                driver.execute_script("arguments[0].scrollIntoView();", strip['button'])
                driver.execute_script("arguments[0].click();", strip['button'])
                time.sleep(1.5) 
                
                tables = driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    if table.is_displayed():
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        for row in rows:
                            if str(current_date.day) in row.text or date_str in row.text:
                                cols = row.find_elements(By.TAG_NAME, "td")
                                if len(cols) > 1:
                                    data_number = cols[1].text.strip()
                                    break
            except:
                pass 
                
            daily_record[strip['unique_col']] = data_number
            
        all_data_rows.append(daily_record)
        current_date += timedelta(days=1)
        
    driver.quit()
    
    # Ab data banate waqt koi duplicate column naam nahi milega
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
                df_final.to_excel(FILE_NAME, index=False)
                
                st.success("✅ Fresh Data successfully nikal liya gaya hai!")
                st.write("### 🆕 Excel Format Preview (Upar Time+Naam, Niche Naam)")
                st.dataframe(df_final)
                
                with open(FILE_NAME, "rb") as file:
                    st.download_button(
                        label="📥 Download Fresh Excel File",
                        data=file,
                        file_name=FILE_NAME,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("Data laane mein dikkat aayi. Driver aur Net connection check karein.")
                
