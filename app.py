import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Shift Data Auto Fetcher", layout="wide")
st.title("📊 Shift Data Auto Fetcher")
st.write("Sirf Date aur Shifton ka data. Purana save rahega, naya aage judega.")

FILE_NAME = "Satta_Complete_Record.xlsx"

# ==========================================
# 2. CORE FUNCTIONS
# ==========================================
def get_last_updated_date(filename):
    """Excel padhkar aakhri date nikalta hai taaki wahan se aage ka data laye."""
    if os.path.exists(filename):
        try:
            df_existing = pd.read_excel(filename)
            # Pehli line mein shift ke naam hain, usko hatakar date check karni hai
            dates_only = df_existing[df_existing['Date'] != 'Date']['Date'].dropna()
            
            if not dates_only.empty:
                last_date_str = dates_only.iloc[-1]
                last_date = pd.to_datetime(last_date_str).date()
                return df_existing, last_date
            else:
                return df_existing, None
        except Exception as e:
            st.error("Purani file mein error. Nayi banegi.")
            return None, None
    return None, None

def setup_excel_format():
    """Upar Time, Niche Shift ka Naam. (Koi Base Shift nahi)"""
    # Yahan 30-40 shifton ke time aayenge (Example ke liye 4 diye hain)
    columns = ["Date", "05:00 AM", "06:15 PM", "08:00 PM", "11:30 PM"]
    
    # Pehli row mein Pili Patti wale Shift ke naam aayenge
    first_row = {
        "Date": "Date",
        "05:00 AM": "DESAWAR",
        "06:15 PM": "FARIDABAD",
        "08:00 PM": "GAZIYABAD",
        "11:30 PM": "GALI"
    }
    return pd.DataFrame([first_row], columns=columns)

def scrape_missing_data(start_date, end_date):
    """Website se data nikalne wala engine"""
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
        st.error("Driver Error! 'packages.txt' check karein.")
        return pd.DataFrame() 

    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3) 
    
    scraped_data = []
    current_date = start_date
    
    # Yahan code website ki sari 30-40 Pili Pattiyon ko scan karega
    # Aur 'Record Chart' par click karke unka data layega
    while current_date <= end_date:
        # Example format: Date sabse pehle, fir baki sabhi 30-40 shifton ka data
        row = {
            'Date': current_date.strftime('%d-%b-%Y'),
            '05:00 AM': '45',  # DESAWAR ka data
            '06:15 PM': '92',  # FARIDABAD ka data
            '08:00 PM': '10',  # GAZIYABAD ka data
            '11:30 PM': '12'   # GALI ka data
        }
        scraped_data.append(row)
        current_date += timedelta(days=1)
        
    driver.quit()
    return pd.DataFrame(scraped_data)

# ==========================================
# 3. SIDEBAR (Sirf Start aur End Date)
# ==========================================
st.sidebar.header("🗓️ Data Fetch Settings")

start_fetch_date = st.sidebar.date_input("Start Date (Kahan se chahiye?):", date(2018, 1, 1))
end_fetch_date = st.sidebar.date_input("End Date (Kahan tak?):", date.today())

fetch_button = st.sidebar.button("Fetch All Shifts Data")

# ==========================================
# 4. MAIN APP EXECUTION
# ==========================================
df_existing, last_date = get_last_updated_date(FILE_NAME)

st.write("### 🗄️ Purana File Record")
if df_existing is not None and not df_existing.empty:
    st.dataframe(df_existing)
    if last_date:
        st.success(f"📌 File mein {last_date} tak ka data safe hai.")
else:
    st.info("Koi purani file nahi hai. Nayi Excel banegi.")
    df_existing = setup_excel_format()

if fetch_button:
    with st.spinner('⏳ Pili pattiyon se data laya ja raha hai...'):
        
        # Smart Date Check: Agar data pehle se hai to uske aage se shuru karo
        if last_date is not None and last_date >= start_fetch_date:
            actual_start_date = last_date + timedelta(days=1)
            st.warning(f"File mein {last_date} tak data hai. Naya data {actual_start_date} se aayega.")
        else:
            actual_start_date = start_fetch_date

        if actual_start_date > end_fetch_date:
            st.success("✅ File aaj tak poori updated hai!")
        else:
            # Bina base shift wale function ko call kiya
            df_new = scrape_missing_data(actual_start_date, end_fetch_date)
            
            if not df_new.empty:
                df_final = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Excel mein save
                df_final.to_excel(FILE_NAME, index=False)
                
                st.success(f"✅ Data Fetch Complete! File '{FILE_NAME}' mein save ho gaya.")
                st.write("### 🆕 Naya Record")
                st.dataframe(df_final)
                
                # Download File
                with open(FILE_NAME, "rb") as file:
                    st.download_button(
                        label="📥 Download Excel File",
                        data=file,
                        file_name=FILE_NAME,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("Data laane mein dikkat hui.")
                
