import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

# Page Setup
st.set_page_config(page_title="Double Jackpot Pattern AI", layout="wide")

st.title("🔥 Double Jackpot & Multi-Timeline Pattern AI")
st.write("Weekly, Monthly, और Double Shift विश्लेषण के साथ सबसे सटीक प्रेडिक्शन टूल।")

# 1. Master Patterns
master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

# 2. Sidebar - File Upload & Settings
uploaded_file = st.sidebar.file_uploader("Data File Upload (CSV/Excel)", type=['csv', 'xlsx'])
window = st.sidebar.select_slider("विश्लेषण के दिन (Lookback Window)", options=[1, 3, 7, 10, 15, 30], value=30)

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    for col in shifts:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- PROCESSING ---
    success_history = [] # For general trends
    shift_wise_success = {s: [] for s in shifts} # For Double Jackpot logic
    
    for i in range(len(df) - 1):
        today_all = set(df.loc[i, shifts].dropna().values)
        tomorrow_all = set(df.loc[i+1, shifts].dropna().values)
        if not today_all or not tomorrow_all: continue
        
        # General Success
        day_found = [p for val in today_all for p in master_patterns if (val + p) % 100 in tomorrow_all]
        success_history.append(list(set(day_found)))
        
        # Shift-wise Success
        for s in shifts:
            s_val = df.loc[i, s]
            if pd.isna(s_val): continue
            s_found = [p for p in master_patterns if (s_val + p) % 100 in tomorrow_all]
            shift_wise_success[s].append(list(set(s_found)))

    # --- SECTION 1: WEEKLY VS MONTHLY JACKPOT ---
    st.header("💎 Weekly & Monthly Trend Analysis")
    col_w, col_m = st.columns(2)
    
    weekly_data = [p for sub in success_history[-7:] for p in sub]
    weekly_freq = Counter(weekly_data)
    
    monthly_data = [p for sub in success_history[-30:] for p in sub]
    monthly_freq = Counter(monthly_data)
    
    with col_w:
        st.subheader("📅 Weekly (Top 5)")
        st.write(weekly_freq.most_common(5))
    with col_m:
        st.subheader("📅 Monthly (Top 5)")
        st.write(monthly_freq.most_common(5))

    # Jackpot: Common Patterns
    jackpot_ps = set([p for p, c in weekly_freq.most_common(10)]).intersection(set([p for p, c in monthly_freq.most_common(10)]))
    st.success(f"🎯 **Jackpot Patterns (Common in Week & Month):** {list(jackpot_ps)}")

    # --- SECTION 2: DOUBLE JACKPOT ALERT (Multi-Shift) ---
    st.divider()
    st.header("🔔 Double Jackpot Alert (Multi-Shift Match)")
    st.info("यह सेक्शन तब अलर्ट देता है जब दो अलग-अलग शिफ्ट एक ही पैटर्न की ओर इशारा करें।")
    
    # Analyze last available day
    last_shift_matches = {}
    for s in shifts:
        if shift_wise_success[s]:
            last_shift_matches[s] = shift_wise_success[s][-1]
    
    # Find patterns appearing in more than one shift
    all_last_ps = [p for sub in last_shift_matches.values() for p in sub]
    double_jackpot_counts = Counter(all_last_ps)
    double_alerts = [p for p, count in double_jackpot_counts.items() if count >= 2]
    
    if double_alerts:
        st.warning(f"🚀 **DOUBLE JACKPOT ALERT!** ये पैटर्न आज 2 या उससे ज्यादा शिफ्ट में मैच हुए हैं: **{double_alerts}**")
    else:
        st.write("आज कोई Double Jackpot मैच नहीं मिला।")

    # --- SECTION 3: SEQUENCE CHAIN (1-5) ---
    st.divider()
    st.header("🔗 Chain Sequence Analysis")
    chain_size = st.radio("Chain Depth", [1, 2, 3, 4, 5], horizontal=True)
    
    recent_data = success_history[-window:]
    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i+1]
        if len(curr) >= chain_size:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt: seq_counter[(combo, n)] += 1
    
    if seq_counter:
        st.table([{"Current Group": k[0], "Next Likely": k[1], "Hits": v} for k, v in seq_counter.most_common(10)])

    # --- SECTION 4: FINAL PREDICTION ---
    st.divider()
    if success_history:
        st.subheader(f"🔮 Today's Analysis Complete")
        final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(success_history[-1]))]
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.write("**टॉप सीक्वेंस प्रेडिक्शन:**")
            st.code(list(set(final_preds))[:10])
        with res_col2:
            st.write("**सुझाव:**")
            st.write("Double Jackpot अलर्ट वाले नंबरों को प्राथमिकता दें।")

else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें (Excel/CSV)।")
