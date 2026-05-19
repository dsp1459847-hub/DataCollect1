import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from datetime import datetime
import re

st.set_page_config(page_title="Satta Master Database", layout="wide")

# Permanent File Name
DB_FILE = "satta_master_database.csv"

st.title("🗄️ Satta Master Database (Auto-Update Mode)")
st.info("Ye app purana data save rakhta hai. Agle din sirf naya data add hoga.")

# --- Functions to Manage Permanent Storage ---
def load_existing_db():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

def save_to_db(new_df):
    if os.path.exists(DB_FILE):
        old_df = pd.read_csv(DB_FILE)
        # Purane aur naye data ko jodna aur duplicates hatana
        combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset=['DATE', 'SHIFT'], keep='last')
        combined_df.to_csv(DB_FILE, index=False)
    else:
        new_df.to_csv(DB_FILE, index=False)

# --- Scraper Setup ---
SITES = ["https://satta-king-fast.com/chart.php", "https://sattaking-fast.com/chart.php"]

def fetch_month(dt):
    m, y = str(dt.month).zfill(2), str(dt.year)
    scraper = cloudscraper.create_scraper()
    try:
        res = scraper.get(f"{random.choice(SITES)}?month={m}&year={y}", timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if table:
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
                            if val: # Sirf wo data lein jo khali nahi hai
                                records.append({'DATE': clean_date, 'SHIFT': headers[idx], 'VALUE': val})
                return records
    except: return None
    return None

# --- Main UI ---
existing_data = load_existing_db()

# Statistics dikhana
if not existing_data.empty:
    st.success(f"Database mein pehle se {existing_data['DATE'].nunique()} dino ka data saved hai.")
else:
    st.warning("Database khali hai. Pehli baar download karne mein samay lagega.")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Kahan se shuru karein", datetime(2018, 1, 1))
with col2:
    end_date = st.date_input("Kab tak ka update chahiye", datetime.now())

if st.button("🚀 Sync / Update Data"):
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    # Check karein kaunse mahine ka data missing ho sakta hai (Latest month hamesha fetch karein update ke liye)
    progress_bar = st.progress(0)
    status = st.empty()
    
    total_new_records = []
    
    for i, dt in enumerate(date_range):
        m_id = dt.strftime("%m-%Y")
        status.text(f"Checking data for: {m_id}")
        
        # Mahine ka data fetch karna
        month_data = fetch_month(dt)
        if month_data:
            total_new_records.extend(month_data)
            status.success(f"Fetched: {m_id}")
        
        progress_bar.progress((i + 1) / len(date_range))
        time.sleep(random.uniform(1, 2))
    
    if total_new_records:
        new_df = pd.DataFrame(total_new_records)
        save_to_db(new_df)
        st.rerun() # Page refresh karke naya data dikhayein

# --- Display & Download ---
final_df = load_existing_db()
if not final_df.empty:
    # Pivot for Excel Format
    pivot_df = final_df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
    
    # Date Sorting
    pivot_df['temp_dt'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True)
    pivot_df = pivot_df.sort_values('temp_dt', ascending=False).drop('temp_dt', axis=1)
    
    st.subheader("Final Excel Sheet View")
    st.dataframe(pivot_df)
    
    # Download Button
    csv = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Download Updated Excel (CSV)",
        data=csv,
        file_name=f"Satta_Master_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )

if st.sidebar.button("🗑️ Reset Database"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        st.rerun()
        
