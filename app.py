import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

# Page Setup
st.set_page_config(page_title="Ultimate Jackpot AI", layout="wide")

st.title("🚀 Ultimate Automatic Number Generator & Pattern AI")
st.write("यह सिस्टम खुद ही पैटर्न चुनता है और आपके लिए फाइनल नंबर तैयार करता है।")

# 1. Master Patterns & Config
master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

# 2. Sidebar - Input & Settings
st.sidebar.header("📥 डेटा और इनपुट")
uploaded_file = st.sidebar.file_uploader("Data File (CSV/Excel)", type=['csv', 'xlsx'])
window = st.sidebar.select_slider("विश्लेषण अवधि (Days)", options=[1, 3, 7, 10, 15, 30], value=30)

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    for col in shifts:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

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

    # --- SECTION 1: TREND ANALYSIS ---
    st.header("📊 Trend & Jackpot Alerts")
    recent_data = success_history[-window:]
    flat_recent = [p for sub in recent_data for p in sub]
    top_patterns = [p for p, c in Counter(flat_recent).most_common(10)]
    
    # Double Jackpot Alert
    last_shift_matches = {s: shift_wise_success[s][-1] for s in shifts if shift_wise_success[s]}
    all_last_ps = [p for sub in last_shift_matches.values() for p in sub]
    double_alerts = [p for p, count in Counter(all_last_ps).items() if count >= 2]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"📅 पिछले {window} दिन के टॉप पैटर्न: {top_patterns[:5]}")
    with col_b:
        if double_alerts:
            st.warning(f"🚀 DOUBLE JACKPOT ALERT: {double_alerts}")
        else:
            st.success("आज कोई Double Jackpot अलर्ट नहीं है।")

    # --- SECTION 2: AUTOMATIC NUMBER GENERATOR ---
    st.divider()
    st.header("🎯 Final Automatic Number Predictions")
    st.write("सिस्टम ने आज के नंबरों और सबसे मजबूत पैटर्नों को मिलाकर ये नंबर निकाले हैं:")

    today_nums = df.iloc[-1][shifts].dropna().to_dict()
    
    # Logic: Apply Top Patterns + Sequence Patterns + Double Jackpot Patterns
    final_pattern_pool = set(top_patterns) | set(double_alerts)
    
    generated_numbers = []
    for s_name, s_val in today_nums.items():
        for p in final_pattern_pool:
            res = int((s_val + p) % 100)
            generated_numbers.append(res)
    
    # Frequency of generated numbers (Bar Counter)
    num_counts = Counter(generated_numbers)
    
    # Display in Bar Groups
    res_col1, res_col2, res_col3 = st.columns(3)
    
    with res_col1:
        st.subheader("🔥 Super Strong (Bar 4+)")
        super_s = [n for n, c in num_counts.items() if c >= 4]
        st.write(sorted(super_s))

    with res_col2:
        st.subheader("⭐ Strong (Bar 2-3)")
        strong_s = [n for n, c in num_counts.items() if 2 <= c <= 3]
        st.write(sorted(strong_s))

    with res_col3:
        st.subheader("📍 Normal (Bar 1)")
        normal_s = [n for n, c in num_counts.items() if c == 1]
        st.write(sorted(normal_s))

    # --- SECTION 3: SEQUENCE CHAIN ---
    st.divider()
    st.header("🔗 Sequence Chain (History)")
    chain_size = st.select_slider("सीक्वेंस गहराई", options=[1, 2, 3, 4, 5], value=1)
    
    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i+1]
        if len(curr) >= chain_size:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt: seq_counter[(combo, n)] += 1
    
    if seq_counter:
        st.table([{"आज के पैटर्न": k[0], "कल का पैटर्न": k[1], "कितनी बार आया": v} for k, v in seq_counter.most_common(8)])

else:
    st.info("शुरू करने के लिए अपनी एक्सेल फाइल साइडबार में अपलोड करें।")
                
