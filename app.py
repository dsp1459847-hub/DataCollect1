import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta Database Manager", layout="wide")

# Permanent Storage File
DB_FILE = "satta_master_db.csv"

st.title("🗄️ Smart Satta Database (Incremental Update)")

# --- Storage Logic ---
def load_db():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

def save_db(new_records):
    if not new_records: return
    new_df = pd.DataFrame(new_records)
    if os.path.exists(DB_FILE):
        old_df = pd.read_csv(DB_FILE)
        # Naye aur purane data ko jodna, duplicate hatana
        final_df = pd.concat([old_df, new_df], ignore_index=True)
        final_df.drop_duplicates(subset=['DATE', 'SHIFT'], keep='last', inplace=True)
        final_df.to_csv(DB_FILE, index=False)
    else:
        new_df.to_csv(DB_FILE, index=False)

# --- Scraper ---
SITES = ["https://satta-king-fast.com/chart.php", "https://sattaking-fast.com/chart.php"]

def fetch_month_data(dt):
    m, y = str(dt.month).zfill(2), str(dt.year)
    scraper = cloudscraper.create_scraper()
    try:
        res = scraper.get(f"{random.choice(SITES)}?month={m}&year={y}", timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if not table: return None
            
            rows = table.find_all('tr')
            headers = [re.sub(r'\s+', ' ', h.text.strip()) for h in rows[0].find_all(['th', 'td'])]
            
            records = []
            for row in rows[1:]:
                cols = row.find_all(['td', 'th'])
                day = re.findall(r'\d+', cols[0].text.strip())
                if not day: continue
                clean_date = f"{day[0].zfill(2)}-{m}-{y}"
                for idx, col in enumerate(cols):
                    if 0 < idx < len(headers):
                        val = col.text.strip()
                        if val: records.append({'DATE': clean_date, 'SHIFT': headers[idx], 'VALUE': val})
            return records
    except: return None
    return None

# --- UI & Logic ---
master_df = load_db()

# Stats
if not master_df.empty:
    last_date = master_df['DATE'].iloc[-1]
    st.success(f"Dabaase mein data hai. Aakhiri record: {last_date}")
else:
    st.warning("Database khali hai. 2018 se fetch karna hoga.")

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Kahan se shuru karein", datetime(2018, 1, 1))
with c2:
    end_date = st.date_input("Kab tak ka update", datetime.now())

if st.button("🚀 Sync / Update Data"):
    # 1. Sirf wahi mahine nikalna jo missing hain
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    # Simple Check: Agar database khali nahi hai, toh check karein kaunse mahine bache hain
    # (Note: Current month hamesha fetch karenge naye updates ke liye)
    months_to_fetch = []
    for dt in all_months:
        m_id = dt.strftime("%m-%Y")
        # Agar mahina current hai ya database mein nahi hai, toh fetch karo
        if master_df.empty or m_id == datetime.now().strftime("%m-%Y"):
            months_to_fetch.append(dt)
        elif not master_df['DATE'].str.contains(m_id).any():
            months_to_fetch.append(dt)

    if not months_to_fetch:
        st.info("Data pehle se hi up-to-date hai!")
    else:
        progress = st.progress(0)
        status = st.empty()
        
        for i, dt in enumerate(months_to_fetch):
            m_id = dt.strftime("%m-%Y")
            status.text(f"Updating: {m_id}...")
            
            new_data = fetch_month_data(dt)
            if new_data:
                save_db(new_data)
                status.success(f"Saved: {m_id}")
            
            progress.progress((i + 1) / len(months_to_fetch))
            time.sleep(random.uniform(1, 2))
        
        status.info("✅ Update Complete! Refreshing...")
        time.sleep(1)
        st.rerun()

# --- Display & Final Download ---
updated_df = load_db()
if not updated_df.empty:
    # Format for Excel
    pivot_df = updated_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    
    # Date Sorting (Latest on top)
    pivot_df['temp_dt'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True)
    pivot_df = pivot_df.sort_values('temp_dt', ascending=False).drop('temp_dt', axis=1)
    
    st.subheader("Your Data (Excel Format)")
    st.dataframe(pivot_df)
    
    # YAHAN DOWNLOAD BUTTON AAYEGA
    csv = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Download Updated Excel File",
        data=csv,
        file_name=f"Satta_Master_Database.csv",
        mime="text/csv"
    )

if st.sidebar.button("🗑️ Reset Database"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()
    
