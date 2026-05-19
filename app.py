import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ==========================================
# 1. PAGE SETUP AUR UI
# ==========================================
st.set_page_config(page_title="Shift Data Auto Fetcher", layout="wide")
st.title("📊 Shift Data Auto Fetcher & Updater")
st.write("Yeh app purana data save rakhegi aur sirf naya data site se fetch karegi.")

FILE_NAME = "Satta_Complete_Record.xlsx"

# ==========================================
# 2. FUNCTIONS
# ==========================================
def get_last_updated_date(filename):
    """Excel file padhta hai aur aakhri date nikalta hai."""
    if os.path.exists(filename):
        try:
            df_existing = pd.read_excel(filename, header=[0, 1])
            last_date_str = df_existing[('Date', 'Date')].dropna().iloc[-1]
            last_date = pd.to_datetime(last_date_str).date()
            return df_existing, last_date
        except Exception as e:
            st.error("Purani file padhne mein error. Nayi file banegi.")
            return None, None
    return None, None

def setup_excel_format():
    """Header setup: Upar Time, Niche Shift Name."""
    columns = pd.MultiIndex.from_tuples([
        ("Date", "Date"),
        ("Base Shift Date", "Base Shift Data"), # Base shift logic alag se
        ("05:00 AM", "DESAWAR"),
        ("06:15 PM", "FARIDABAD"),
        ("08:00 PM", "GAZIYABAD"),
        ("11:30 PM", "GALI")
    ])
    return pd.DataFrame(columns=columns)

def scrape_missing_data(start_date, end_date, base_date):
    """Cloud par Selenium chalane ka crash-proof function."""
    
    # Cloud-specific Chrome Options
    options = Options()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-dev-shm-usage') 
    options.add_argument('--disable-gpu') 
    options.add_argument('--window-size=1920,1080') 
    
    # Streamlit Cloud ke driver ka rasta (packages.txt se aata hai)
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        st.error("Driver Load Error! Check packages.txt")
        return pd.DataFrame() # Khali data return karega error me

    # Site par jana
    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3) # Site load hone ka intezar
    
    scraped_data = []
    
    # DUMMY LOGIC: Yahan actual HTML click aur copy ka logic aayega
    # (Abhi yeh dummy data generate karega taki excel format sahi bane)
    current_date = start_date
    while current_date <= end_date:
        row = {
            ('Date', 'Date'): current_date.strftime('%d-%b-%Y'),
            ('Base Shift Date', 'Base Shift Data'): base_date.strftime('%d-%b-%Y'),
            ('05:00 AM', 'DESAWAR'): '45', # Data from site
            ('06:15 PM', 'FARIDABAD'): '92',
            ('08:00 PM', 'GAZIYABAD'): '10',
            ('11:30 PM', 'GALI'): '12'
        }
        scraped_data.append(row)
        current_date += timedelta(days=1)
        
    driver.quit()
    return pd.DataFrame(scraped_data)

# ==========================================
# 3. SIDEBAR MENUS (Dates Select Karne Ke Liye)
# ==========================================
st.sidebar.header("🗓️ Date Settings")

# Base shift ke liye alag se date setting
st.sidebar.subheader("Base Shift Settings")
selected_base_shift_date = st.sidebar.date_input("Base Shift ki Date:", date.today() - timedelta(days=1))

st.sidebar.markdown("---")

# Baaki sabhi shifton ke liye date setting
st.sidebar.subheader("Other Shifts Settings")
start_fetch_date = st.sidebar.date_input("Start Date:", date(2018, 1, 1))
end_fetch_date = st.sidebar.date_input("End Date (Aaj tak):", date.today())

fetch_button = st.sidebar.button("Fetch & Update Data")

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
df_existing, last_date = get_last_updated_date(FILE_NAME)

st.write("### 🗄️ Purana Saved Data")
if df_existing is not None and not df_existing.empty:
    st.dataframe(df_existing)
    st.success(f"📌 File mein aakhri entry is date tak hai: {last_date}")
else:
    st.info("Abhi tak koi Excel file save nahi hai. Nayi file banegi.")
    df_existing = setup_excel_format()

if fetch_button:
    with st.spinner('⏳ Internet se missing data fetch ho raha hai... Kripya pratiksha karein...'):
        
        # Agar purana data hai, to start date uske agle din se set karo
        if last_date is not None and last_date >= start_fetch_date:
            actual_start_date = last_date + timedelta(days=1)
            st.warning(f"Data pehle se {last_date} tak update hai. Naya data {actual_start_date} se fetch hoga.")
        else:
            actual_start_date = start_fetch_date

        if actual_start_date > end_fetch_date:
            st.success("✅ Aapka data pehle se hi aakhri date tak updated hai!")
        else:
            # Data nikalne wala function call karna
            df_new = scrape_missing_data(actual_start_date, end_fetch_date, selected_base_shift_date)
            
            if not df_new.empty:
                # Purane aur naye data ko jodna
                df_final = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Excel me save karna
                df_final.to_excel(FILE_NAME, index=False)
                
                st.success(f"✅ Naya data successfully file '{FILE_NAME}' mein update ho gaya hai!")
                st.write("### 🆕 Updated Record")
                st.dataframe(df_final)
                
                # Download button
                with open(FILE_NAME, "rb") as file:
                    st.download_button(
                        label="📥 Download Updated Excel File",
                        data=file,
                        file_name=FILE_NAME,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("Data fetch karne me dikkat aayi. Kripya apne packages.txt ko check karein.")

