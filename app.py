import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

st.set_page_config(page_title="Satta Data - Clean Excel Format", layout="wide")

st.title("📊 Satta King Data Scraper (Professional Excel Format)")
st.info("Isme ek tarikh ek hi baar aayegi aur saara data uske aage horizontal line mein dikhega.")

# Sidebar Settings
st.sidebar.header("Data Filter")
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

def get_clean_data(start_dt, end_dt):
    base_url = "https://satta-king-fast.com/chart.php"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    all_extracted_data = [] # List of dicts for each row
    
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        params = {'month': str(dt.month).zfill(2), 'year': dt.year}
        try:
            res = requests.get(base_url, params=params, headers=headers)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    if not rows: continue
                    
                    # Headers (Shifts) nikalna
                    raw_headers = [h.text.strip() for h in rows[0].find_all(['th', 'td'])]
                    
                    # Data process karna
                    for row in rows[1:]:
                        cols = [c.text.strip() for c in row.find_all(['td', 'th'])]
                        if not cols or len(cols) < 2: continue
                        
                        # Date saaf karna
                        day_match = re.findall(r'\d+', cols[0])
                        if not day_match: continue
                        day = day_match[0].zfill(2)
                        full_date = f"{day}-{str(dt.month).zfill(2)}-{dt.year}"
                        
                        # Row ka data map karna
                        row_entry = {'DATE': full_date}
                        for idx, h in enumerate(raw_headers):
                            if idx == 0 or not h: continue
                            if idx < len(cols):
                                # Agar cell khali hai toh empty string
                                val = cols[idx] if cols[idx] else ""
                                row_entry[h] = val
                        
                        all_extracted_data.append(row_entry)
            
            progress_bar.progress((i + 1) / len(date_range))
            time.sleep(0.3)
        except Exception as e:
            st.error(f"Error at {dt.month}-{dt.year}: {e}")
            
    return all_extracted_data

if st.button("Generate Master Excel Data"):
    with st.spinner('Data ko format kiya ja raha hai...'):
        data_list = get_clean_data(start_date, end_date)
        
        if data_list:
            # Dataframe banana
            df = pd.DataFrame(data_list)
            
            # 1. Ek hi date ki multiple entries ko merge karna (Group By)
            # Taki 1 tarikh bar-bar na aaye
            df = df.groupby('DATE', sort=False).first().reset_index()
            
            # 2. Columns ko clean karna (Shift names se time hata kar sirf code rakhna agar chahiye)
            # Lekin filhaal hum shift names ko unke time ke order mein rakhenge
            cols = list(df.columns)
            if 'DATE' in cols:
                cols.remove('DATE')
                # Sort columns based on time if possible, else keep as is
                final_cols = ['DATE'] + sorted(cols) # Simple alphabetical for now
                df = df[final_cols]

            st.success(f"Final Data Ready! Total Days: {len(df)}")
            st.dataframe(df) # App mein preview
            
            # CSV Download
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download Clean CSV (Excel Ready)",
                data=csv,
                file_name=f"Satta_Master_History_{start_date}.csv",
                mime="text/csv",
            )
        else:
            st.error("Data fetch nahi ho paya. URL ya Internet check karein.")
            
