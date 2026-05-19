import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Satta Data - Pro Fix", layout="wide")

st.title("⚡ Satta Extractor (Fixed Multi-Thread)")

# 1. Session State Initialization
if 'master_data' not in st.session_state:
    st.session_state.master_data = []
if 'processed_months' not in st.session_state:
    st.session_state.processed_months = set() # Set for faster lookup
if 'unique_shifts' not in st.session_state:
    st.session_state.unique_shifts = set()

SITES = [
    "https://satta-king-fast.com/chart.php",
    "https://sattaking-fast.com/chart.php",
    "https://satta-fast.com/chart.php"
]

# UI Inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime(2018, 1, 1))
with col2:
    end_date = st.date_input("End Date", datetime.now())

# --- FIXED FUNCTION (Removed Session State access inside thread) ---
def scrape_single_month(dt):
    m = str(dt.month).zfill(2)
    y = str(dt.year)
    month_id = f"{m}-{y}"
    
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
                        
                        day_match = re.findall(r'\d+', cols[0].text.strip())
                        if not day_match: continue
                        
                        clean_date = f"{day_match[0].zfill(2)}-{m}-{y}"
                        
                        for idx, col in enumerate(cols):
                            if idx == 0 or idx >= len(headers): continue
                            shift = headers[idx]
                            if shift and 'DATE' not in shift.upper():
                                month_records.append({
                                    'DATE': clean_date,
                                    'SHIFT': shift,
                                    'VALUE': col.text.strip()
                                })
                    return month_records, headers[1:], month_id
    except Exception:
        return "error"
    return None

# Controls
c1, c2, c3 = st.columns(3)
with c1:
    start_btn = st.button("🚀 Start/Resume Fetching")
with c2:
    if st.button("🛑 Reset Everything"):
        st.session_state.master_data = []
        st.session_state.processed_months = set()
        st.session_state.unique_shifts = set()
        st.rerun()

if start_btn:
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    # FILTERING: Thread ke bahar hi filter kar lo taaki thread ko session_state na dekhna pade
    remaining_months = [dt for dt in date_range if f"{str(dt.month).zfill(2)}-{dt.year}" not in st.session_state.processed_months]
    
    if not remaining_months:
        st.success("Saara data tayyar hai!")
    else:
        st.info(f"Bacha hua data nikal raha hoon... ({len(remaining_months)} mahine)")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Max workers ko 3 rakha hai taaki block na ho
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_month = {executor.submit(scrape_single_month, dt): dt for dt in remaining_months}
            
            for i, future in enumerate(as_completed(future_to_month)):
                dt = future_to_month[future]
                m_id = f"{str(dt.month).zfill(2)}-{dt.year}"
                
                try:
                    result = future.result()
                    if result == "error":
                        status_text.warning(f"Failed: {m_id}. Next time try karenge.")
                    elif result:
                        month_data, month_shifts, res_id = result
                        st.session_state.master_data.extend(month_data)
                        st.session_state.processed_months.add(res_id)
                        st.session_state.unique_shifts.update(month_shifts)
                        status_text.text(f"Done: {res_id}")
                except Exception as e:
                    status_text.error(f"Thread Error: {str(e)}")
                
                progress_bar.progress((i + 1) / len(remaining_months))
                time.sleep(random.uniform(1, 2))

# Result Display
if st.session_state.master_data:
    df_raw = pd.DataFrame(st.session_state.master_data)
    # Pivot for exact Excel format
    df_pivot = df_raw.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    
    # Simple Column Sorting
    shifts_cols = [c for c in df_pivot.columns if c != 'DATE']
    # Final Columns: DATE + Sorted Shifts
    df_pivot = df_pivot[['DATE'] + sorted(shifts_cols)]
    
    st.dataframe(df_pivot)
    
    csv = df_pivot.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Download Full CSV", data=csv, file_name="satta_full_data.csv")
    
