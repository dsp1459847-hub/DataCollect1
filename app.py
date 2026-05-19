import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

st.set_page_config(page_title="Satta King Pro - Fixed", layout="wide")

st.title("📊 Satta King Data Extractor (Fixed Version)")
st.info("Agar 'No Data' aaye toh Date Range thodi peeche ki select karke check karein.")

# Sidebar
st.sidebar.header("Settings")
start_date = st.sidebar.date_input("Start Date", datetime(2024, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

def get_24hr_minutes(shift_name):
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', shift_name, re.IGNORECASE)
    if time_match:
        hr, mn, period = time_match.groups()
        hr = int(hr)
        if period.upper() == 'PM' and hr != 12: hr += 12
        if period.upper() == 'AM' and hr == 12: hr = 0
        return hr * 60 + int(mn)
    return 1440

def scrape_data(start_dt, end_dt):
    base_url = "https://satta-king-fast.com/chart.php"
    # Modern Browser Headers (Isse block hone ke chances kam hote hain)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }
    
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    all_extracted_records = []
    unique_shifts = set()
    
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        m = str(dt.month).zfill(2)
        y = str(dt.year)
        
        try:
            res = requests.get(base_url, params={'month': m, 'year': y}, headers=headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # Sabse bada table dhundna
                table = soup.find('table')
                
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        # Headers nikalna
                        header_cells = rows[0].find_all(['th', 'td'])
                        page_headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in header_cells]
                        
                        for row in rows[1:]:
                            cols = row.find_all(['td', 'th'])
                            if not cols or len(cols) < 2: continue
                            
                            # Clean Date
                            raw_date = cols[0].text.strip()
                            day_only = re.findall(r'\d+', raw_date)
                            if not day_only: continue
                            
                            clean_date = f"{day_only[0].zfill(2)}-{m}-{y}"
                            
                            for idx, col in enumerate(cols):
                                if idx == 0 or idx >= len(page_headers): continue
                                shift_name = page_headers[idx]
                                if shift_name and 'DATE' not in shift_name.upper():
                                    val = col.text.strip()
                                    unique_shifts.add(shift_name)
                                    all_extracted_records.append({
                                        'DATE': clean_date,
                                        'SHIFT': shift_name,
                                        'VALUE': val
                                    })
            
            progress_bar.progress((i + 1) / len(date_range))
            time.sleep(0.5)
        except Exception as e:
            st.sidebar.warning(f"Error in {m}-{y}: {str(e)}")
            
    return all_extracted_records, list(unique_shifts)

if st.button("Generate Excel Format Table"):
    with st.spinner('Data nikalne ki koshish kar raha hoon...'):
        records, shifts = scrape_data(start_date, end_date)
        
        if records:
            df_raw = pd.DataFrame(records)
            # Pivot logic: DATE niche, SHIFTS upar
            df_pivot = df_raw.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
            
            # Time sorting
            sorted_cols = sorted(shifts, key=get_24hr_minutes)
            final_cols = ['DATE'] + sorted_cols
            df_pivot = df_pivot.reindex(columns=final_cols)
            
            st.success(f"Success! {len(df_pivot)} dino ka data mila.")
            st.dataframe(df_pivot)
            
            csv = df_pivot.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Download Excel CSV", data=csv, file_name="satta_data.csv", mime="text/csv")
        else:
            st.error("Abhi bhi data nahi mil raha. Iska matlab site ne scraper block kiya hai ya URL change ho gaya hai.")
    
