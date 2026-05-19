import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta DB Final Fix", layout="wide")

DB_FILE = "satta_master_db.csv"

# --- Database Load/Save ---
def load_db():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE)
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_to_db(records):
    if not records: return
    new_df = pd.DataFrame(records)
    if os.path.exists(DB_FILE):
        old_df = pd.read_csv(DB_FILE)
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined.drop_duplicates(subset=['DATE', 'SHIFT'], keep='last', inplace=True)
        combined.to_csv(DB_FILE, index=False)
    else:
        new_df.to_csv(DB_FILE, index=False)

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
st.title("🛡️ Satta Master DB (No-Restart Download)")

# Data load karo
master_df = load_db()

# AGAR DATA HAI TO DOWNLOAD PEHLE DIKHAO
if not master_df.empty:
    st.subheader("📥 Download Your Excel File")
    
    # Pivot logic
    pivot_df = master_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    pivot_df['dt_obj'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True, errors='coerce')
    pivot_df = pivot_df.sort_values('dt_obj', ascending=False).drop('dt_obj', axis=1)
    
    csv_data = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    
    # Bada Download Button
    st.download_button(
        label="🟢 CLICK HERE TO DOWNLOAD EXCEL (CSV)",
        data=csv_data,
        file_name=f"Satta_Data_Export_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    st.success(f"Database mein total {len(master_df)} entries saved hain.")
    st.divider()

# Input Section
col1, col2 = st.columns(2)
with col1: start_date = st.date_input("Start Date", datetime(2018, 1, 1))
with col2: end_date = st.date_input("End Date", datetime.now())

if st.button("🚀 Start Sync / Update Data"):
    months = pd.date_range(start=start_date, end=end_date, freq='MS')
    pb = st.progress(0)
    st_msg = st.empty()
    
    for i, dt in enumerate(months):
        m_id = dt.strftime("%m-%Y")
        st_msg.info(f"Syncing: {m_id}...")
        
        data = fetch_month(dt)
        if data:
            save_to_db(data)
            st_msg.success(f"Saved to Disk: {m_id}")
        
        pb.progress((i + 1) / len(months))
        time.sleep(random.uniform(1, 2))
    
    st.balloons() # Kaam khatam hone ka signal
    st_msg.success("✅ ALL DATA DOWNLOADED & SAVED PERMANENTLY!")
    time.sleep(2)
    st.rerun()

# Table Preview (Optional)
if not master_df.empty:
    with st.expander("View Data Table Preview"):
        st.dataframe(pivot_df.head(100))

# Reset Sidebar
if st.sidebar.button("🗑️ Reset Local Database"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()
    
