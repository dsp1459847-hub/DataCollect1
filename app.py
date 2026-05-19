import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Satta Data Scraper - Excel Format", layout="wide")

st.title("📊 Satta King Data Scraper (Excel Format)")
st.write("Ye tool aapki Excel sheet ke format ke hisab se data arrange karta hai.")

# Sidebar Selection
st.sidebar.header("Date Range")
start_date = st.sidebar.date_input("Start Date", datetime(2020, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

def fetch_formatted_data(start_dt, end_dt):
    base_url = "https://satta-king-fast.com/chart.php"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    final_data = []
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        params = {'month': str(dt.month).zfill(2), 'year': dt.year}
        try:
            response = requests.get(base_url, params=params, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if table:
                    # Headers nikalna (Shifts ke naam)
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = [ele.text.strip() for ele in row.find_all(['td', 'th'])]
                        if len(cols) > 2:
                            final_data.append(cols)
            
            progress_bar.progress((i + 1) / len(date_range))
            time.sleep(0.3)
        except Exception as e:
            st.error(f"Error: {dt.year}-{dt.month}: {e}")
            
    return final_data

if st.button("Fetch & Format Data"):
    with st.spinner('Excel format mein data taiyar ho raha hai...'):
        raw_data = fetch_formatted_data(start_date, end_date)
        
        if raw_data:
            # Excel format ke hisab se columns set karna (DATE, DS, FD, GD, GL...)
            df = pd.DataFrame(raw_data)
            
            # [span_3](start_span)Excel format jaisa header set karna[span_3](end_span)
            columns_list = ['DATE', 'DS', 'FD', 'GD', 'GL', 'DB', 'SG', 'ZA']
            # Agar columns zyada ya kam hain toh adjust karega
            df.columns = columns_list[:len(df.columns)]
            
            st.success("Data successfully fetched in Excel format!")
            st.dataframe(df)
            
            # CSV Download with UTF-8 for Hindi/Special chars
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="Download Excel-Ready CSV",
                data=csv,
                file_name=f"Satta_Excel_Format_{start_date}.csv",
                mime="text/csv",
            )
        else:
            st.error("Data nahi mila.")
            
