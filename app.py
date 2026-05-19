import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta DB Pro", layout="wide")

DB_FILE = "satta_master_db.csv"

# --- Functions ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_db(records):
    if not records: return
    new_df = pd.DataFrame(records)
    if os.path.exists(DB_FILE):
        old_df = pd.read_csv(DB_FILE)
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined.drop_duplicates(subset=['DATE', 'SHIFT'], keep='last', inplace=True)
        combined.to_csv(DB_FILE, index=False)
    else:
        new_df.to_csv(DB_FILE, index=False)

def fetch_data(dt):
    m, y = str(dt.month).zfill(2), str(dt.year)
    scraper = cloudscraper.create_scraper()
    url = f"https://satta-king-fast.com/chart.php?month={m}&year={y}"
    try:
        res = scraper.get(url, timeout=20)
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

# --- UI Layout ---
st.title("🗄️ Satta Database Master (Final Fix)")

master_df = load_db()

# DOWNLOAD BUTTON KO SABSE UPAR RAKHA HAI
if not master_df.empty:
    pivot_df = master_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    # Date sorting
    pivot_df['dt_obj'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True)
    pivot_df = pivot_df.sort_values('dt_obj', ascending=False).drop('dt_obj', axis=1)
    
    st.subheader("✅ Data Download Section")
    csv_bytes = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 DOWNLOAD NOW (Abhi Tak Ka Saara Data)",
        data=csv_bytes,
        file_name=f"Satta_Update_{datetime.now().strftime('%d_%m_%Y')}.csv",
        mime="text/csv",
        key='main_download'
    )
    st.divider()

# Inputs
c1, c2 = st.columns(2)
with c1: start_date = st.date_input("Start Date", datetime(2018, 1, 1))
with c2: end_date = st.date_input("End Date", datetime.now())

if st.button("🚀 Sync / Update New Data"):
    months = pd.date_range(start=start_date, end=end_date, freq='MS')
    pb = st.progress(0)
    st_status = st.empty()
    
    for i, dt in enumerate(months):
        m_id = dt.strftime("%m-%Y")
        st_status.info(f"Processing: {m_id}...")
        
        # Hamesha current month update karein ya jo DB mein nahi hai
        if master_df.empty or m_id == datetime.now().strftime("%m-%Y") or not master_df['DATE'].str.contains(m_id).any():
            new_recs = fetch_data(dt)
            if new_recs:
                save_db(new_recs)
                st_status.success(f"Saved to File: {m_id}")
            else:
                st_status.error(f"Skipped/Failed: {m_id}")
        
        pb.progress((i + 1) / len(months))
        time.sleep(random.uniform(1.5, 2.5))
    
    st_status.success("✅ Sab Kuch Update Ho Gaya Hai!")
    time.sleep(1)
    st.rerun()

# Preview niche dikhayenge
if not master_df.empty:
    st.subheader("Preview (Last 50 Days)")
    st.dataframe(pivot_df.head(50))

if st.sidebar.button("🗑️ Reset Database"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()
    
