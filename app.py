import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re
from datetime import datetime

def fetch_and_format_satta_data(start_year, end_year):
    all_raw_data = []
    base_url = "https://satta-king-fast.com/chart.php"
    master_raw_file = "satta_master_raw.csv"
    final_excel_file = f"Satta_Report_{start_year}_to_{end_year}.csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"Extraction shuru: {start_year} se {end_year} tak...")

    # 1. SCRAPING SECTION
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Future months skip karne ke liye (agar current year hai)
            if year == datetime.now().year and month > datetime.now().month:
                break
                
            str_month = str(month).zfill(2)
            params = {'month': str_month, 'year': year}
            
            try:
                response = requests.get(base_url, params=params, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table')
                    
                    if table:
                        current_day1, current_day2 = 18, 19 # Default days
                        rows = table.find_all('tr')
                        
                        for row in rows:
                            cols = [ele.text.strip() for ele in row.find_all(['td', 'th'])]
                            if not cols or len(cols) < 3: continue
                            
                            col0 = cols[0]
                            # Day info nikalna agar row 'Regional' wali hai
                            if "Regional Offline" in col0:
                                d1_m = re.search(r'(\d+)', cols[1])
                                d2_m = re.search(r'(\d+)', cols[2])
                                if d1_m: current_day1 = int(d1_m.group(1))
                                if d2_m: current_day2 = int(d2_m.group(1))
                                continue

                            # Meta rows skip karein
                            if any(x in col0 for x in ["NEXT", "Satta King", "SHOW YOUR GAME"]):
                                continue

                            # Game Name clean karein (Extra text hatayein)
                            clean_name = col0.split('\n')[0].strip()
                            
                            # Record for Day 1
                            date1 = f"{year}-{str_month}-{str(current_day1).zfill(2)}"
                            all_raw_data.append({'Date': date1, 'Game': clean_name, 'Result': cols[1]})
                            
                            # Record for Day 2
                            date2 = f"{year}-{str_month}-{str(current_day2).zfill(2)}"
                            all_raw_data.append({'Date': date2, 'Game': clean_name, 'Result': cols[2]})
                        
                        print(f"Fetched: {str_month}-{year}")
                time.sleep(1) # IP Block se bachne ke liye delay
                
            except Exception as e:
                print(f"Error at {str_month}-{year}: {e}")

    # 2. DATA FORMATTING SECTION (Excel Style)
    if all_raw_data:
        # Step A: DataFrame banayein
        df_long = pd.DataFrame(all_raw_data)
        
        # Step B: Pivot karein (Taaki Games Columns ban jayein aur Date Rows)
        # Yeh wahi format hai jo aapki original Excel sheet mein tha
        df_pivot = df_long.pivot_table(index='Date', columns='Game', values='Result', aggfunc='first')
        
        # Step C: Dates ko sahi karke Sort karein (Latest Date sabse upar)
        df_pivot.index = pd.to_datetime(df_pivot.index)
        df_pivot = df_pivot.sort_index(ascending=False)
        
        # Step D: Final CSV Save karein
        df_pivot.to_csv(final_excel_file)
        
        print(f"\n--- MUBARAK HO ---")
        print(f"Aapka vyavasthit data yahan save hai: {final_excel_file}")
        print(f"Total Dates covered: {len(df_pivot)}")
        print(f"Total Games found: {len(df_pivot.columns)}")
    else:
        print("Koi data nahi mil paya.")

# Code Run karein
fetch_and_format_satta_data(2018, 2026)
        
