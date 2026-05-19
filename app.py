import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import re

st.set_page_config(page_title="Satta Data Final", layout="wide")

st.title("📊 Satta King Data - Final Stable")

# Simple scrap function
def fetch_now(dt):
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
                cols = [c.text.strip() for c in row.find_all(['td', 'th'])]
                if not cols: continue
                day_match = re.findall(r'\d+', cols[0])
                if not day_match: continue
                c_date = f"{day_match[0].zfill(2)}-{m}-{y}"
                for idx, val in enumerate(cols):
                    if 0 < idx < len(headers):
                        if val: recs.append({'DATE': c_date, 'SHIFT': headers[idx], 'VALUE': val})
            return recs
    except: return None
    return None

start_date = st.date_input("Start Date", datetime(2024, 1, 1))
end_date = st.date_input("End Date", datetime.now())

if st.button("🚀 GET DATA & DOWNLOAD"):
    months = pd.date_range(start=start_date, end=end_date, freq='MS')
    all_data = []
    pb = st.progress(0)
    msg = st.empty()
    
    for i, dt in enumerate(months):
        msg.info(f"Downloading: {dt.strftime('%m-%Y')}...")
        res = fetch_now(dt)
        if res: all_data.extend(res)
        pb.progress((i + 1) / len(months))
        time.sleep(1)

    if all_data:
        df = pd.DataFrame(all_data)
        # Pivot logic
        pivot_df = df.pivot(index='DATE', columns='SHIFT', values='VALUE').reset_index()
        # Sort
        pivot_df['dt'] = pd.to_datetime(pivot_df['DATE'], format='%d-%m-%Y', dayfirst=True, errors='coerce')
        pivot_df = pivot_df.sort_values('dt', ascending=False).drop('dt', axis=1)
        
        st.success("✅ Data fetched successfully!")
        st.dataframe(pivot_df)
        
        csv = pivot_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 DOWNLOAD EXCEL FILE", data=csv, file_name="satta_data.csv", mime="text/csv")
    else:
        st.error("No data found. Site might be blocking. Try after some time.")
        
