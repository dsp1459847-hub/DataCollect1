import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime

# 1. Page ki setting aur Title
st.set_page_config(page_title="Data Auto Fetcher & Updater", layout="wide")
st.title("📊 Shift Data Auto Fetcher & Updater")
st.write("Yeh app aapka purana data save rakhegi aur sirf naya data site se fetch karegi.")

# 2. File ka naam jahan data hamesha SAVE rahega
FILE_NAME = "satta_record_saved.csv"

# 3. Purana data load karne ka function (Taaki net band hone par bhi data dikhe)
def load_saved_data():
    if os.path.exists(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    else:
        # Agar pehli baar chala rahe hain, to blank format ready karein
        return pd.DataFrame(columns=["Date"])

df_saved = load_saved_data()

# Screen par purana data dikhana
st.write("### 🗄️ Purana Saved Data (Offline File)")
if not df_saved.empty:
    st.dataframe(df_saved)
    last_date = df_saved["Date"].max()
    st.success(f"📌 File mein aakhri update is date tak ka maujud hai: {last_date}")
else:
    st.info("Abhi tak koi data save nahi hai. Niche di gayi date se naya data lana shuru karein.")
    last_date = None

st.markdown("---")
st.write("### 🔄 Naya Data Fetch Karein (Sirf missing data)")

col1, col2 = st.columns(2)
with col1:
    # Agar purana data hai, to start date wahi se uthayega warna default lega
    start_date = st.date_input("Kahan se data fetch karna shuru karein?", datetime(2023, 11, 1).date())
with col2:
    end_date = st.date_input("Kahan tak ka data chahiye?", datetime.today().date())

# Button dabane par data laane ka kaam shuru
if st.button("Fetch & Update Data (Tukdon Mein)"):
    st.warning("⏳ Data site se laya ja raha hai. Site crash na ho isliye ruk-ruk kar (chunks mein) process chal rahi hai...")
    
    progress_bar = st.progress(0)
    
    # Yahan tumhara scraping engine kaam karega jo neele dabbe (URL month) wala logic lagayega
    new_data_list = []
    
    # DUMMY LOOP: Yahan original web scraping ka background task chalega jo mahine-dar-mahine data nikalega.
    # Har mahine ka data nikalne ke baad yeh 3 second ka break lega taaki site par load na pade.
    total_months_to_fetch = 3 
    for i in range(1, total_months_to_fetch + 1): 
        st.write(f"Mahine {i} ka data aa raha hai...")
        
        # Site ko saans lene ke liye 3 second ka delay (Tukdon mein kaam)
        time.sleep(3) 
        
        progress_bar.progress(i * (100 // total_months_to_fetch))
        
        # Pili patti aur time (Add D) extract karke columns banaye gaye
        new_data_list.append({
            "Date": str(end_date), 
            "DESAWAR Add D 05:00 AM": "45", # Yahan asli site ka data aayega
            "FARIDABAD Add D 06:15 PM": "92", 
            "GALI Add D 11:30 PM": "23"
        })
    
    # List ko DataFrame (Excel/Table) format me badalna
    df_new = pd.DataFrame(new_data_list)
    
    # 4. Asli Magic: Purane aur naye data ko aapas me jodna (Merge)
    if not df_saved.empty:
        # Puraane mein naya jodega, aur double (duplicate) date hui to usko hata dega
        df_final = pd.concat([df_saved, df_new]).drop_duplicates(subset=["Date"], keep="last")
    else:
        df_final = df_new
        
    # Naye Final Data ko wapas us CSV me SAVE kar dena (Offline storage)
    df_final.to_csv(FILE_NAME, index=False)
    
    st.success("✅ Naya Data successfully nikal liya gaya hai aur File mein Update/Save ho gaya hai!")
    st.dataframe(df_final)
    
    # 5. Tumhara Excel/CSV Download karne ka Button
    st.write("### 📥 Updated Excel/CSV File Download Karein")
    csv_data = df_final.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Final Record (Excel/CSV)",
        data=csv_data,
        file_name="Updated_Shift_Record.csv",
        mime="text/csv"
    )
    
