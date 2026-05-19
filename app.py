import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta DB Final", layout="wide")

# Permanent Storage
DB_FILE = "satta_master_db.csv"

st.title("🛡️ Satta Master DB (Permanent Download Fixed)")

# 1. Database Check & Load
if not os.path.exists(DB_FILE):
    # Khali file bana do agar nahi hai
    pd.DataFrame(columns=['DATE', 'SHIFT', 'VALUE']).to_csv(DB_FILE, index=False)

def get_data_count():
    try:
        temp_df = pd.read_csv(DB_FILE)
        return len(temp_df), temp_df
    except:
        return 0, pd.DataFrame()

# --- Scraper Engine ---
def fetch_month(dt):
    m, y = str(dt.month).zfill(2), str(dt.year)
    scraper = cloudscraper.create_scraper()
    url = f"https://satta-king-fast.com/chart.php?month={m}&year={y}"
    try:
        res = scraper.get(url, timeout=25)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if not table: return None
            rows = table.find_all('tr')
            headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in rows[0].find_all(['th', 'td'])]
            recs = []
            for row in rows[1:]:
                cols = row.find_all(['td', 'th'])
                day = re.findall(r'\d+', cols[0].text.strip())
                if not day: continue
                c_date = f"{day[0].zfill(2)}-{m}-{y}"
                for idx, col in enumerate(cols):
                    if 0 < idx < len(headers):
                        val = col.text.strip()
                        if val: recs.append({'DATE': c_date, 'SHIFT': headers[idx], 'VALUE': val})
            return recs
    except: return None
    return None

# --- UI SECTION ---

# Download Button ko HAMESHA sabse upar rakho
count, current_df = get_data_count()

if count > 0:
    st.subheader("📥 Download Zone")
    # Pivot for Excel
    try:
        pivot_df = current_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
        # Sahi date sorting
        pivot_df['dt_obj'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True, errors='coerce')
        pivot_df = pivot_df.sort_values('dt_obj', ascending=False).drop('dt_obj', axis=1)
        
        csv_data = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label=f"Download {count} Records (Excel CSV)",
            data=csv_data,
            file_name=f"Satta_Data_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            key="always_on_download"
        )
    except Exception as e:
        st.error(f"Table Error: {e}")

st.divider()

# Input Controls
c1, c2 = st.columns(2)
with c1: start_date = st.date_input("Start Date", datetime(2018, 1, 1))
with c2: end_date = st.date_input("End Date", datetime.now())

if st.button("🚀 Start Sync / Update"):
    months = pd.date_range(start=start_date, end=end_date, freq='MS')
    pb = st.progress(0)
    st_msg = st.empty()
    
    for i, dt in enumerate(months):
        m_id = dt.strftime("%m-%Y")
        st_msg.info(f"Working on: {m_id}...")
        
        # Har bar fetch karke file mein append karo
        new_recs = fetch_month(dt)
        if new_recs:
            new_df = pd.DataFrame(new_recs)
            old_df = pd.read_csv(DB_FILE)
            combined = pd.concat([old_df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=['DATE', 'SHIFT'], keep='last', inplace=True)
            combined.to_csv(DB_FILE, index=False)
            st_msg.success(f"Saved: {m_id}")
        
        pb.progress((i + 1) / len(months))
        time.sleep(random.uniform(1, 2))
    
    st_msg.success("✅ All data synced! Refreshing...")
    time.sleep(1)
    st.rerun()

if st.sidebar.button("🗑️ Reset All Data"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()
    
