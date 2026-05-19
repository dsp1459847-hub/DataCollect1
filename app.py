import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Satta Data - Ultra Fast & Resume", layout="wide")

st.title("⚡ Ultra Fast Satta Extractor (Resume Enabled)")
st.write("Ye version data ko 'Resume' kar sakta hai aur multiple threads se fast download karta hai.")

# 1. Session State Initialize (Resume karne ke liye)
if 'master_data' not in st.session_state:
    st.session_state.master_data = []
if 'processed_months' not in st.session_state:
    st.session_state.processed_months = []
if 'unique_shifts' not in st.session_state:
    st.session_state.unique_shifts = set()

# Mirror Sites
SITES = [
    "https://satta-king-fast.com/chart.php",
    "https://sattaking-fast.com/chart.php",
    "https://satta-fast.com/chart.php",
    "https://satta-king-chart.org/chart.php"
]

# UI for Inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime(2020, 1, 1))
with col2:
    end_date = st.date_input("End Date", datetime.now())

def scrape_single_month(dt):
    """Ek single mahine ka data nikalne ka function"""
    m = str(dt.month).zfill(2)
    y = str(dt.year)
    month_id = f"{m}-{y}"
    
    # Agar ye mahina pehle hi process ho chuka hai, toh skip karein
    if month_id in st.session_state.processed_months:
        return None

    scraper = cloudscraper.create_scraper()
    site_url = random.choice(SITES)
    target_url = f"{site_url}?month={m}&year={y}"
    
    try:
        res = scraper.get(target_url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    header_cells = rows[0].find_all(['th', 'td'])
                    headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in header_cells]
                    
                    month_records = []
                    for row in rows[1:]:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) < 2: continue
                        
                        day = re.findall(r'\d+', cols[0].text.strip())
                        if not day: continue
                        
                        clean_date = f"{day[0].zfill(2)}-{m}-{y}"
                        
                        for idx, col in enumerate(cols):
                            if idx == 0 or idx >= len(headers): continue
                            shift = headers[idx]
                            if shift and 'DATE' not in shift.upper():
                                month_records.append({
                                    'DATE': clean_date,
                                    'SHIFT': shift,
                                    'VALUE': col.text.strip(),
                                    'month_id': month_id
                                })
                    return month_records, headers[1:]
    except:
        return "error"
    return None

# Buttons
c1, c2, c3 = st.columns(3)
with c1:
    start_btn = st.button("🚀 Start/Resume Fetching")
with c2:
    if st.button("🛑 Clear Memory/Reset"):
        st.session_state.master_data = []
        st.session_state.processed_months = []
        st.session_state.unique_shifts = set()
        st.rerun()

if start_btn:
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    # Filter out already processed months
    remaining_months = [dt for dt in date_range if f"{str(dt.month).zfill(2)}-{dt.year}" not in st.session_state.processed_months]
    
    if not remaining_months:
        st.success("Saara data pehle hi nikal chuka hai!")
    else:
        st.info(f"Bacha hua data nikal raha hoon... ({len(remaining_months)} mahine baaki)")
        progress_bar = st.progress(0)
        
        # MULTI-THREADING: 4 mahine ek saath load honge
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_month = {executor.submit(scrape_single_month, dt): dt for dt in remaining_months}
            
            for i, future in enumerate(as_completed(future_to_month)):
                result = future.result()
                dt = future_to_month[future]
                m_id = f"{str(dt.month).zfill(2)}-{dt.year}"
                
                if result == "error":
                    st.warning(f"Atak gaya: {m_id}. Agle button click par resume hoga.")
                elif result:
                    month_data, month_shifts = result
                    st.session_state.master_data.extend(month_data)
                    st.session_state.processed_months.append(m_id)
                    st.session_state.unique_shifts.update(month_shifts)
                
                progress_bar.progress((i + 1) / len(remaining_months))
                # Chhota delay taaki anti-bot trigger na ho
                time.sleep(random.uniform(1, 2))

# Display Data if exists
if st.session_state.master_data:
    df = pd.DataFrame(st.session_state.master_data)
    # Pivot for Excel structure
    pivot_df = df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    
    # Sorting (Latest Date at bottom)
    pivot_df['dt_obj'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True)
    pivot_df = pivot_df.sort_values('dt_obj').drop('dt_obj', axis=1, errors='ignore')
    
    st.subheader("Data Preview (Live)")
    st.dataframe(pivot_df)
    
    csv = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Download Full CSV", data=csv, file_name="satta_final_resume.csv")
            
