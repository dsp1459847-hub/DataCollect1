import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

st.set_page_config(page_title="Satta Data Pro - Ultra Fix", layout="wide")

st.title("📊 Satta King Data Extractor (Universal Fix)")
st.write("Ye version site ki security bypass karke data nikalne ke liye design kiya gaya hai.")

# Sidebar
st.sidebar.header("Settings")
start_date = st.sidebar.date_input("Start Date", datetime(2025, 1, 1))
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

def scrape_with_bypass(start_dt, end_dt):
    # Cloudscraper site ki security (Cloudflare/DDoS) bypass karne ke liye
    scraper = cloudscraper.create_scraper() 
    
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    all_records = []
    unique_shifts = set()
    
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        m = str(dt.month).zfill(2)
        y = str(dt.year)
        # Aapka diya hua exact URL format
        target_url = f"https://satta-king-fast.com/chart.php?month={m}&year={y}"
        
        try:
            res = scraper.get(target_url, timeout=20)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table')
                
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        # Headers (Shifts)
                        header_cells = rows[0].find_all(['th', 'td'])
                        page_headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in header_cells]
                        
                        for row in rows[1:]:
                            cols = row.find_all(['td', 'th'])
                            if not cols or len(cols) < 2: continue
                            
                            # Date cleaning
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
                                    all_records.append({
                                        'DATE': clean_date,
                                        'SHIFT': shift_name,
                                        'VALUE': val
                                    })
            
            progress_bar.progress((i + 1) / len(date_range))
            time.sleep(1) # Site ko suspicious na lage isliye thoda gap
        except Exception as e:
            st.sidebar.error(f"Error {m}-{y}: {str(e)}")
            
    return all_records, list(unique_shifts)

if st.button("🚀 Fetch Data in Excel Format"):
    with st.spinner('Site ki security bypass karke data nikala ja raha hai...'):
        records, shifts = scrape_with_bypass(start_date, end_date)
        
        if records:
            df_raw = pd.DataFrame(records)
            # Pivot table (DATE side mein, SHIFTS upar)
            df_pivot = df_raw.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
            
            # Shifts ko time ke hisab se sort karna
            sorted_cols = sorted(shifts, key=get_24hr_minutes)
            final_cols = ['DATE'] + sorted_cols
            df_pivot = df_pivot.reindex(columns=final_cols)
            
            # Excel format sorting (Latest date niche)
            df_pivot['dt_obj'] = pd.to_datetime(df_pivot['DATE'], format='%d-%m-%Y')
            df_pivot = df_pivot.sort_values('dt_obj').drop('dt_obj', axis=1)

            st.success(f"Success! {len(df_pivot)} dino ka data mil gaya.")
            st.dataframe(df_pivot)
            
            csv = df_pivot.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Download Excel Ready CSV", data=csv, file_name="satta_perfect_data.csv", mime="text/csv")
        else:
            st.error("Data abhi bhi nahi mila. Site ne connection block kar diya hai.")
                                     
