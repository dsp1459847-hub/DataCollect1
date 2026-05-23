import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import timedelta

# Page Setup
st.set_page_config(page_title="Date-Wise Jackpot AI", layout="wide")

st.title("📅 Date-Wise Automatic Number Generator")
st.write("यह ऐप आपकी फाइल से तारीख पढ़कर कल और परसों की सटीक भविष्यवाणी करता है।")

# 1. Master Patterns
master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

# 2. Sidebar - File Upload
uploaded_file = st.sidebar.file_uploader("Data File Upload (CSV/Excel)", type=['csv', 'xlsx'])
window = st.sidebar.select_slider("विश्लेषण अवधि (Days)", options=[1, 3, 7, 10, 15, 30], value=30)

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Date Handling
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'])
        last_date = df['DATE'].max()
        tomorrow = last_date + timedelta(days=1)
        day_after = last_date + timedelta(days=2)
    else:
        last_date = "Unknown"
        tomorrow = "Tomorrow"
        day_after = "Day After"

    for col in shifts:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- INFO BOX ---
    st.info(f"✅ **डेटा अपडेट:** {last_date.strftime('%d-%b-%Y') if last_date != 'Unknown' else 'Unknown'}")
    st.success(f"🎯 **अगला प्रेडिक्शन (Day 1):** {tomorrow.strftime('%d-%b-%Y') if last_date != 'Unknown' else 'कल'}")
    st.warning(f"🎯 **प्रेडिक्शन (Day 2):** {day_after.strftime('%d-%b-%Y') if last_date != 'Unknown' else 'परसों'}")

    # --- SUCCESS EXTRACTION ---
    success_history = []
    shift_wise_success = {s: [] for s in shifts}
    for i in range(len(df) - 1):
        today_all = set(df.loc[i, shifts].dropna().values)
        tomorrow_all = set(df.loc[i+1, shifts].dropna().values)
        if not today_all or not tomorrow_all: continue
        day_found = [p for val in today_all for p in master_patterns if (val + p) % 100 in tomorrow_all]
        success_history.append(list(set(day_found)))
        for s in shifts:
            s_val = df.loc[i, s]
            if not pd.isna(s_val):
                s_found = [p for p in master_patterns if (s_val + p) % 100 in tomorrow_all]
                shift_wise_success[s].append(list(set(s_found)))

    # --- TRENDS & ALERTS ---
    st.divider()
    recent_data = success_history[-window:]
    flat_recent = [p for sub in recent_data for p in sub]
    top_patterns = [p for p, c in Counter(flat_recent).most_common(10)]
    
    last_shift_matches = {s: shift_wise_success[s][-1] for s in shifts if shift_wise_success[s]}
    double_alerts = [p for p, count in Counter([p for sub in last_shift_matches.values() for p in sub]).items() if count >= 2]
    
    # --- AUTOMATIC GENERATOR ---
    st.header(f"🔮 {tomorrow.strftime('%d-%b-%Y') if last_date != 'Unknown' else 'कल'} के लिए फाइनल नंबर")
    
    today_nums = df.iloc[-1][shifts].dropna().to_dict()
    final_pattern_pool = set(top_patterns) | set(double_alerts)
    
    generated_numbers = []
    for s_val in today_nums.values():
        for p in final_pattern_pool:
            generated_numbers.append(int((s_val + p) % 100))
    
    num_counts = Counter(generated_numbers)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🔥 Super Strong (4+ Bar)")
        st.write(sorted([n for n, c in num_counts.items() if c >= 4]))
    with c2:
        st.subheader("⭐ Strong (2-3 Bar)")
        st.write(sorted([n for n, c in num_counts.items() if 2 <= c <= 3]))
    with c3:
        st.subheader("📍 Normal (1 Bar)")
        st.write(sorted([n for n, c in num_counts.items() if c == 1]))

    # --- SEQUENCE LOGIC ---
    st.divider()
    st.header("🔗 पैटर्न चेन विश्लेषण")
    chain_size = st.radio("Chain Depth", [1, 2, 3], horizontal=True)
    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i+1]
        if len(curr) >= chain_size:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt: seq_counter[(combo, n)] += 1
    
    if seq_counter:
        st.write(f"पिछले {window} दिनों के सीक्वेंस के आधार पर:")
        st.table([{"आज का पैटर्न": k[0], "अगला संभावित": k[1], "हिट्स": v} for k, v in seq_counter.most_common(5)])

else:
    st.info("Sidebar में अपनी फाइल अपलोड करें। ध्यान रखें कि फाइल में 'DATE' नाम का कॉलम होना चाहिए।")
    
