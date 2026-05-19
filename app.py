import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Satta Data Scraper", layout="wide")

st.title("📊 Satta Data Scraper & CSV Exporter")
st.write("Date range select karein aur data download karein.")

# Sidebar Settings
st.sidebar.header("Data Selection")
start_date = st.sidebar.date_input("Kahan se shuru karein (Start Date):", datetime(2020, 1, 1))
end_date = st.sidebar.date_input("Kahan tak (End Date):", datetime.now())

def fetch_data(start_dt, end_dt):
    base_url = "https://satta-king-fast.com/chart.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_rows = []
    # Month-Year ki list banana range ke hisab se
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    
    progress_bar = st.progress(0)
    total_months = len(date_range)
    
    for i, dt in enumerate(date_range):
        year = dt.year
        month = str(dt.month).zfill(2)
        params = {'month': month, 'year': year}
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = [ele.text.strip() for ele in row.find_all(['td', 'th'])]
                        if cols:
                            cols.append(month) # Month reference
                            cols.append(str(year)) # Year reference
                            all_rows.append(cols)
            
            progress_bar.progress((i + 1) / total_months)
            time.sleep(0.5) 
            
        except Exception as e:
            st.error(f"Error: {month}-{year} fetch nahi ho paya: {e}")
            
    return all_rows

if st.button("Data Nikalein"):
    if start_date > end_date:
        st.warning("Start date, End date se badi nahi ho sakti!")
    else:
        with st.spinner('Pura data scrape kiya ja raha hai...'):
            data = fetch_data(start_date, end_date)
            
            if data:
                df = pd.DataFrame(data)
                st.success(f"Success! {len(df)} lines ka data mila.")
                st.dataframe(df.head(50)) # Preview
                
                # CSV Conversion
                csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                
                st.download_button(
                    label="Download CSV File",
                    data=csv,
                    file_name=f"satta_history_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                )
            else:
                st.error("Koi data nahi mila. Site structure ya connection check karein.")
              
