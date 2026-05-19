import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta DB Master", layout="wide")

DB_FILE = "satta_master_db.csv"

# --- Storage Helper Functions ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def save_db(records):
    if not records: return
    new_df = pd.DataFrame(records)
    if os.path.exists(DB_FILE):
        try:
            old_df = pd.read_csv(DB_FILE)
            combined = pd.concat([old_df, new_df], ignore_index=True)
            # Duplicate hatana zaroori hai
            combined.drop_duplicates(subset=['DATE', 'SHIFT'], keep='last', inplace=True)
            combined.to_csv(DB_FILE, index=False)
        except:
            new_df.to_csv(DB_FILE, index=False)
    else:
        new_df.to_csv(DB_FILE, index=False)

# --- Scraper Engine ---
def fetch_month_data(dt):
    m, y = str(dt.month).zfill(2), str(dt.year)
    scraper = cloudscraper.create_scraper()
    # Multiple sites try karne ke liye
    urls = [
        f"https://satta-king-fast.com/chart.php?month={m}&year={y}",
        f"https://sattaking-fast.com/chart.php?month={m}&year={y}"
    ]
    
    for url in urls:
        try:
            res = scraper.get(url, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                table = soup.find('table')
                if not table: continue
                
                rows = table.find_all('tr')
                headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in rows[0].find_all(['th', 'td'])]
                
                records = []
                for row in rows[1:]:
                    cols = row.find_all(['td', 'th'])
                    if not cols: continue
                    day_text = cols[0].text.strip()
                    day_match = re.findall(r'\d+', day_text)
                    if not day_match: continue
                    
                    clean_date = f"{day_match[0].zfill(2)}-{m}-{y}"
                    for idx, col in enumerate(cols):
                        if 0 < idx < len(headers):
                            val = col.text.strip()
                            if val:
                                records.append({'DATE': clean_date, 'SHIFT': headers[idx], 'VALUE': val})
                if records: return records
        except:
            continue
    return None

# --- Main App Interface ---
st.title("🗄️ Satta Master Database - Fixed Version")

master_df = load_db()

# Statistics Area
if not master_df.empty:
    st.sidebar.success(f"Database Loaded: {len(master_df)} Records Found")
    # Latest data dikhana preview ke liye
    st.sidebar.info(f"Last Date in DB: {master_df['DATE'].iloc[-1]}")
else:
    st.sidebar.warning("Database Khali Hai (Zero Records)")

# Date Inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Kahan se shuru karein", datetime(2018, 1, 1))
with col2:
    end_date = st.date_input("Kab tak ka data chahiye", datetime.now())

# Sync Button
if st.button("🚀 Sync & Update Data (Incremental)"):
    months_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    status = st.empty()
    bar = st.progress(0)
    
    found_any_new = False
    for i, dt in enumerate(months_range):
        m_id = dt.strftime("%m-%Y")
        status.text(f"Checking Month: {m_id}...")
        
        # Incremental logic: Agar current month hai ya data missing hai toh fetch karo
        is_current_month = (dt.month == datetime.now().month and dt.year == datetime.now().year)
        
        data_exists = False
        if not master_df.empty:
            data_exists = master_df['DATE'].str.contains(m_id).any()
        
        if not data_exists or is_current_month:
            new_records = fetch_month_data(dt)
            if new_records:
                save_db(new_records)
                found_any_new = True
                status.success(f"Updated: {m_id}")
            else:
                status.error(f"Failed to fetch: {m_id}")
        
        bar.progress((i + 1) / len(months_range))
        time.sleep(random.uniform(1, 2))
    
    status.success("✅ Process Completed!")
    time.sleep(1)
    st.rerun()

# --- Display Data Table ---
final_df = load_db()
if not final_df.empty:
    # Transform to Excel Format
    pivot_df = final_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    
    # Sort dates properly
    pivot_df['dt_obj'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True)
    pivot_df = pivot_df.sort_values('dt_obj', ascending=False).drop('dt_obj', axis=1)
    
    st.divider()
    # Download Button at Top
    csv_data = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Download Full Excel CSV",
        data=csv_data,
        file_name="Satta_Master_Database.csv",
        mime="text/csv",
        key="top_dl"
    )
    
    st.subheader("Data Preview")
    st.dataframe(pivot_df, use_container_width=True)

if st.sidebar.button("🗑️ Reset/Delete Local Database"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        st.rerun()
        
