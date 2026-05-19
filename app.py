import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

st.set_page_config(page_title="Satta Data Scraper - Perfect Excel Format", layout="wide")

st.title("📊 Satta King Data Scraper (Perfect Excel Format)")
st.write("Ye code data ko exact time order (Subah se Raat) aur sahi DATE ke sath arrange karega.")

# Sidebar Date Selection
st.sidebar.header("Date Range Select Karein")
start_date = st.sidebar.date_input("Start Date", datetime(2018, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())

def parse_satta_page(html_content, year, month_str):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    if not table:
        return None
    
    rows = table.find_all('tr')
    if not rows:
        return None

    # 1. Headers (Shifts) ko extract aur saaf karna
    header_row = rows[0].find_all(['th', 'td'])
    headers = [h.text.strip() for h in header_row]
    
    # 2. Shifts ke andar se Time nikal kar unhe chronological order (Time ke hisab se) mein set karna
    # Example format: "GALI (11:50 PM)" ya "DESAWAR (05:00 AM)"
    shift_time_map = {}
    for idx, h in enumerate(headers):
        if idx == 0 or not h: # Pehla column 'DATE' hota hai
            continue
        
        # Time nikalne ke liye regex (e.g., 05:00 AM or 11:50 PM)
        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', h, re.IGNORECASE)
        if time_match:
            hr, mn, period = time_match.groups()
            hr = int(hr)
            if period.upper() == 'PM' and hr != 12:
                hr += 12
            if period.upper() == 'AM' and hr == 12:
                hr = 0
            # 24-hour format minutes mein convert kiya sorting ke liye
            total_minutes = hr * 60 + int(mn)
            shift_time_map[h] = total_minutes
        else:
            # Agar kisi mein time na ho to use raat ke aakhiri mein dal denge
            shift_time_map[h] = 1440 

    # Shifts ko time ke hisab se sort karna (Subah se Sham)
    sorted_shifts = sorted(shift_time_map, key=shift_time_map.get)
    final_headers = ['DATE'] + sorted_shifts

    # 3. Rows ka data process karna
    month_data = []
    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        if not cols:
            continue
        
        row_cells = [c.text.strip() for c in cols]
        if not row_cells or len(row_cells) < len(headers):
            continue
            
        # Sahi Date format banana (DD-MM-YYYY)
        raw_date_text = row_cells[0]
        # Sirf number nikalna (e.g., "01" ya "01 (Sat)")
        date_digit = re.findall(r'\d+', raw_date_text)
        if not date_digit:
            continue
        
        day_str = date_digit[0].zfill(2)
        formatted_date = f"{day_str}-{month_str}-{year}"
        
        # Ek row ka data dict mein map karna taaki sorted headers ke hisab se arrange ho sake
        row_dict = {'DATE': formatted_date}
        for idx, h in enumerate(headers):
            if idx == 0:
                continue
            if idx < len(row_cells):
                row_dict[h] = row_cells[idx]
        
        # Sorted order mein data row banana
        sorted_row = [row_dict.get(sh, '') for sh in final_headers]
        month_data.append(sorted_row)
        
    return final_headers, month_data

if st.button("Fetch & Process Satta Data"):
    if start_date > end_date:
        st.error("Start Date, End Date se badi nahi ho sakti.")
    else:
        base_url = "https://satta-king-fast.com/chart.php"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
        progress_bar = st.progress(0)
        
        master_data = []
        global_headers = set()
        all_months_extracted = []

        with st.spinner('Website se shifts ka time check karke data filter kiya ja raha hai...'):
            for i, dt in enumerate(date_range):
                m_str = str(dt.month).zfill(2)
                y_str = dt.year
                
                try:
                    res = requests.get(base_url, params={'month': m_str, 'year': y_str}, headers=headers)
                    if res.status_code == 200:
                        parsed = parse_satta_page(res.text, y_str, m_str)
                        if parsed:
                            page_headers, page_rows = parsed
                            # Headers ko master list mein track karna
                            global_headers.update(page_headers)
                            all_months_extracted.append((page_headers, page_rows))
                    
                    progress_bar.progress((i + 1) / len(date_range))
                    time.sleep(0.3)
                except Exception as e:
                    st.sidebar.error(f"Error fetching {m_str}-{y_str}: {e}")

        if all_months_extracted:
            # Sabhi unique headers ko merge karke final DataFrame banana
            # Taki agar kisi saal koi shift nayi aayi ho toh column aage piche na ho
            all_dfs = []
            for p_headers, p_rows in all_months_extracted:
                temp_df = pd.DataFrame(p_rows, columns=p_headers)
                all_dfs.append(temp_df)
                
            final_df = pd.concat(all_dfs, ignore_index=True)
            
            # DATE ko pehle rakhna aur baaki columns ko shift names par standardise karna
            cols = list(final_df.columns)
            if 'DATE' in cols:
                cols.remove('DATE')
                # Columns ko clean sorted banana
                final_cols = ['DATE'] + cols
                final_df = final_df[final_cols]
            
            st.success("Data successfully arrange ho gaya hai!")
            st.dataframe(final_df)
            
            # CSV conversion
            csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download Sorted Excel CSV",
                data=csv,
                file_name=f"Satta_Master_Data_{start_date}_to_{end_date}.csv",
                mime="text/csv",
            )
        else:
            st.error("Koi data nahi mila. Ek baar date range badal kar check karein.")
        
