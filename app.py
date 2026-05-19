import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

st.set_page_config(page_title="Satta King Data - Exact Excel Format", layout="wide")

st.title("📊 Satta King Data Extractor (Exact Excel Sheet Format)")
st.write("Ye code data ko bilkul aapki Excel sheet ke format mein arrange karega.")

# Sidebar Selection
st.sidebar.header("Date Selector")
start_date = st.sidebar.date_input("Start Date:", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date:", datetime.now())

def get_24hr_minutes(shift_name):
    """Shift ke naam se time nikal kar use 24-hour minutes mein convert karna sorting ke liye"""
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', shift_name, re.IGNORECASE)
    if time_match:
        hr, mn, period = time_match.groups()
        hr = int(hr)
        if period.upper() == 'PM' and hr != 12:
            hr += 12
        if period.upper() == 'AM' and hr == 12:
            hr = 0
        return hr * 60 + int(mn)
    return 1440 # Agar time na mile toh aakhiri mein rakhein

def scrape_to_excel_format(start_dt, end_dt):
    base_url = "https://satta-king-fast.com/chart.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='MS')
    all_structured_data = []
    all_shifts_set = set()
    
    progress_bar = st.progress(0)
    
    for i, dt in enumerate(date_range):
        m_str = str(dt.month).zfill(2)
        y_str = str(dt.year)
        
        try:
            res = requests.get(base_url, params={'month': m_str, 'year': y_str}, headers=headers)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table')
                
                if table:
                    rows = table.find_all('tr')
                    if not rows:
                        continue
                    
                    # 1. Page ke headers (Shifts) nikalna
                    page_headers = []
                    for th in rows[0].find_all(['th', 'td']):
                        txt = th.text.strip().replace('\n', ' ').replace('\r', '')
                        txt = re.sub(r'\s+', ' ', txt)
                        page_headers.append(txt)
                    
                    # 2. Rows ka data process karna
                    for row in rows[1:]:
                        cols = row.find_all(['td', 'th'])
                        if not cols or len(cols) < 2:
                            continue
                        
                        # Date nikalna
                        raw_date = cols[0].text.strip()
                        day_match = re.findall(r'\d+', raw_date)
                        if not day_match:
                            continue
                        
                        day = day_match[0].zfill(2)
                        clean_date = f"{day}-{m_str}-{y_str}" # Format: DD-MM-YYYY
                        
                        # Har shift ka data uski date ke sath map karna
                        for idx, col in enumerate(cols):
                            if idx == 0: 
                                continue
                            if idx < len(page_headers):
                                shift_name = page_headers[idx]
                                if shift_name and shift_name.upper() != 'DATE':
                                    all_shifts_set.add(shift_name)
                                    val = col.text.strip()
                                    
                                    all_structured_data.append({
                                        'DATE': clean_date,
                                        'SHIFT': shift_name,
                                        'VALUE': val if val else ""
                                    })
                                    
            progress_bar.progress((i + 1) / len(date_range))
            time.sleep(0.3)
            
        except Exception as e:
            st.sidebar.error(f"Error {m_str}-{y_str}: {e}")
            
    return all_structured_data, list(all_shifts_set)

if st.button("📊 Generate Excel Format Table"):
    with st.spinner('Data ko aapki Excel sheet ke format mein dhal rha hoon...'):
        raw_records, unique_shifts = scrape_to_excel_format(start_date, end_date)
        
        if raw_records:
            # 1. Raw records ka DataFrame banana
            main_df = pd.DataFrame(raw_records)
            
            # 2. Pivot Table lagana (Taki DATE ek baar aaye aur Shifts columns ban jayein)
            # Isse bilkul Excel jaisa structure banta hai
            pivot_df = main_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
            
            # 3. Shifts ko unke sahi time (Subah se Raat) ke hisab se sort karna
            sorted_shifts = sorted(unique_shifts, key=get_24hr_minutes)
            
            # Final columns list: Pehle DATE, phir sorted shifts
            final_columns = ['DATE'] + sorted_shifts
            
            # DataFrame ko sahi column order dena
            pivot_df = pivot_df.reindex(columns=final_columns)
            
            # Date format ko sorting ke liye set karna taaki chronological order dikhe
            pivot_df['temp_date'] = pd.to_datetime(pivot_df['DATE'], format='%D-%M-%Y', errors='coerce')
            # Agar sahi format conversion na ho toh fallback string sort na ho isliye normal treat karenge
            
            st.success(f"Excel Sheet Format Taiyar! Total Days: {len(pivot_df)}")
            
            # UI Preview
            st.dataframe(pivot_df)
            
            # CSV Download button
            csv = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download Excel Ready CSV",
                data=csv,
                file_name=f"Satta_Excel_Perfect_Format_{start_date}_to_{end_date}.csv",
                mime="text/csv",
            )
        else:
            st.error("Koi data nahi mila. Date range check karein.")
        
