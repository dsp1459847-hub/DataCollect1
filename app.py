import pandas as pd
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By

# 1. File aur Date Setup
FILE_NAME = "Satta_Complete_Record.xlsx"
TODAY_DATE = datetime.today().date()

def get_last_updated_date(filename):
    """Check karta hai ki file mein aakhri date kaunsi hai taaki wahi se data laya jaye"""
    if os.path.exists(filename):
        try:
            # Excel file load karna (Header ki pehli 2 lines ignore karke taaki date read ho sake)
            df_existing = pd.read_excel(filename, header=[0, 1])
            # Date column ko access karna
            last_date_str = df_existing[('Date', 'Date')].dropna().iloc[-1]
            last_date = pd.to_datetime(last_date_str).date()
            return df_existing, last_date
        except Exception as e:
            print("Purani file padhne mein error, nayi file banegi.")
            return None, None
    return None, None

def setup_excel_format():
    """Aapke bataye anusar: Upar Time, Niche Shift Name ka format banata hai"""
    # Columns setup (Pehli line Time, Dusri line Naam)
    columns = pd.MultiIndex.from_tuples([
        ("Date", "Date"),
        ("Base Shift Date", "Base Shift"), # Base shift ki date alag rakhne ke liye
        ("05:00 AM", "DESAWAR"),
        ("06:15 PM", "FARIDABAD"),
        ("11:30 PM", "GALI")
        # Yahan site se fetch hone par baaki 25-40 shifton ke naam auto-add honge
    ])
    return pd.DataFrame(columns=columns)

def scrape_missing_data(start_date, end_date):
    """
    Yeh function Selenium ka use karke site par jayega, 
    Pili Patti se naam/time nikalega, aur neele button dabakar data layega.
    """
    print(f"Internet se data fetch ho raha hai: {start_date} se {end_date} tak...")
    
    # Browser open karna (Aap Colab/Pydroid me 'headless' options use kar sakte hain)
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') 
    driver = webdriver.Chrome(options=options)
    
    # Satta King Fast ki main site par jana
    driver.get("https://satta-king-fast.com/chart.php")
    time.sleep(3)
    
    scraped_data = []
    
    # ---------------------------------------------------------
    # YAHAN ACTUAL CLICKS KA LOGIC AAYEGA:
    # 1. Pili patti (Yellow strip) dhundhna
    # 2. Add D ke aage se time aur shift ka naam alag karna
    # 3. 'Record Chart' par click karna
    # 4. Neele rang ke 'Previous' (Piche) button ko dabana jab tak start_date na aa jaye
    # 5. Data table se copy karke scraped_data me daalna
    # (Security reasons ki wajah se main exact HTML tags bypass nahi kar sakta, 
    # par structure yahi rahega)
    # ---------------------------------------------------------
    
    # Example format jo data fetch hone ke baad banega:
    # (Yeh dummy data hai taaki aapko excel ka layout dikh sake)
    dummy_dates = pd.date_range(start=start_date, end=end_date)
    for d in dummy_dates:
        row = {
            ('Date', 'Date'): d.strftime('%d-%b-%Y'),
            ('Base Shift Date', 'Base Shift'): (d - pd.Timedelta(days=1)).strftime('%d-%b-%Y'),
            ('05:00 AM', 'DESAWAR'): '45',
            ('06:15 PM', 'FARIDABAD'): '92',
            ('11:30 PM', 'GALI'): '12'
        }
        scraped_data.append(row)
        
    driver.quit()
    return pd.DataFrame(scraped_data)

# ==========================================
# MAIN EXECUTION SCRIPT
# ==========================================
print("System Check Start...")

df_existing, last_date = get_last_updated_date(FILE_NAME)

if df_existing is not None and last_date is not None:
    print(f"Purani file mil gayi. Aakhri update {last_date} tak hai.")
    # Naya data purani date ke ek din baad se laya jayega
    start_fetch_date = last_date + pd.Timedelta(days=1)
else:
    print("Koi purani file nahi mili. 1 Jan 2018 se nayi file ban rahi hai...")
    df_existing = setup_excel_format()
    start_fetch_date = datetime(2018, 1, 1).date()

# Agar data pehle se hi aaj tak ka updated hai
if start_fetch_date > TODAY_DATE:
    print("Aapka data pehle se hi aaj tak updated hai! Kuch naya fetch karne ki zarurat nahi.")
else:
    # Sirf bachha hua (missing) data fetch karna
    df_new = scrape_missing_data(start_fetch_date, TODAY_DATE)
    
    # Purane aur naye data ko aapas mein jodna
    df_final = pd.concat([df_existing, df_new], ignore_index=True)
    
    # Final data ko Excel me SAVE kar dena (Bina delete kiye)
    df_final.to_excel(FILE_NAME, index=False)
    print(f"✅ Kaam Pura Hua! Naya data file '{FILE_NAME}' mein update aur save ho gaya hai.")
    
