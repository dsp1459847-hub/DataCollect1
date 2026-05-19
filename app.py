import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import re

st.set_page_config(page_title="Satta Data - Smart Extractor", layout="wide")

st.title("🛡️ Smart Satta Data Extractor (Anti-Block Mode)")
st.write("Ye code data ko tukdon mein uthayega aur multiple sites use karega taaki block na ho.")

# Sidebar Settings
st.sidebar.header("Data Range")
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

# Multiple mirror sites to rotate
SITES = [
    "https://satta-king-fast.com/chart.php",
    "https://sattaking-fast.com/chart.php",
    "https://satta-fast.com/chart.php"
]

def get_24hr_minutes(shift_name):
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', shift_name, re.IGNORECASE)
    if time_match:
        hr, mn, period = time_match.groups()
        hr = int(hr)
        if period.upper() == 'PM' and hr != 12: hr += 12
        if period.upper() == 'AM' and hr == 12: hr = 0
        return hr * 60 + int(mn)
    return 1440

def scrape_smartly(start_dt, end_dt):
    scraper = cloudscraper.create_scraper()
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    
    all_records = []
    unique_shifts = set()
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        m = str(dt.month).zfill(2)
        y = str(dt.year)
        
        # Site rotation logic
        site_url = random.choice(SITES)
        target_url = f"{site_url}?month={m}&year={y}"
        
        status_text.text(f"Processing: {m}-{y} from {site_url.split('/')[2]}")
        
        try:
            # Browser headers simulate karna
            res = scraper.get(target_url, timeout=20)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table')
                
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        header_cells = rows[0].find_all(['th', 'td'])
                        page_headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in header_cells]
                        
                        for row in rows[1:]:
                            cols = row.find_all(['td', 'th'])
                            if not cols or len(cols) < 2: continue
                            
                            day_only = re.findall(r'\d+', cols[0].text.strip())
                            if not day_only: continue
                            
                            clean_date = f"{day_only[0].zfill(2)}-{m}-{y}"
                            
                            for idx, col in enumerate(cols):
                                if idx == 0 or idx >= len(page_headers): continue
                                shift_name = page_headers[idx]
                                if shift_name and 'DATE' not in shift_name.upper():
                                    val = col.text.strip()
                                    unique_shifts.add(shift_name)
                                    all_records.append({'DATE': clean_date, 'SHIFT': shift_name, 'VALUE': val})
            
            # CHUNKING & SLEEP: Har mahine ke baad thoda break (2 se 4 second random)
            # Taaki site ko lage ki insaan padh raha hai
            time.sleep(random.uniform(2.0, 4.0))
            progress_bar.progress((i + 1) / len(date_range))
            
        except Exception as e:
            st.sidebar.error(f"Error {m}-{y}: {str(e)}")
            time.sleep(10) # Error aane par 10 sec ka lamba break
            
    return all_records, list(unique_shifts)

if st.button("🚀 Start Safe Extraction"):
    with st.spinner('Slow Mode: Data ko tukdon mein surakshit nikala ja raha hai...'):
        records, shifts = scrape_smartly(start_date, end_date)
        
        if records:
            df_raw = pd.DataFrame(records)
            df_pivot = df_raw.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
            
            sorted_cols = sorted(shifts, key=get_24hr_minutes)
            final_cols = ['DATE'] + sorted_cols
            df_pivot = df_pivot.reindex(columns=final_cols)
            
            # Date sorting fix
            df_pivot['dt_obj'] = pd.to_datetime(df_pivot['DATE'], format='%d-%m-%Y', dayfirst=True)
            df_pivot = df_pivot.sort_values('dt_obj').drop('dt_obj', axis=1)

            st.success("Data Extraction Complete!")
            st.dataframe(df_pivot)
            
            csv = df_pivot.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Download Excel CSV", data=csv, file_name="satta_safe_data.csv", mime="text/csv")
        else:
            st.error("Sabhi koshishon ke baad bhi data nahi mila. Site zyada secure hai.")
            
