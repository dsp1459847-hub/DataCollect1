import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

# Setup
st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म (Weekly) और लॉन्ग-टर्म (Monthly) डेटा का उपयोग करके सबसे पक्के पैटर्न खोजें।")

# 1. Master Patterns
master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

# 2. File Upload
uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    for col in shifts:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- PROCESSING SUCCESS HISTORY ---
    success_history = []
    for i in range(len(df) - 1):
        today = set(df.loc[i, shifts].dropna().values)
        tomorrow = set(df.loc[i+1, shifts].dropna().values)
        if not today or not tomorrow: continue
        found = [p for val in today for p in master_patterns if (val + p) % 100 in tomorrow]
        success_history.append(list(set(found)))

    # --- SIDEBAR: WINDOW SELECTOR ---
    st.sidebar.header("⏱️ विश्लेषण की अवधि")
    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30], value=30)
    recent_data = success_history[-window:] if window <= len(success_history) else success_history

    # --- TOP ROW: SUMMARY CARDS ---
    st.header(f"📊 पिछले {window} दिनों का सारांश")
    flat_list = [p for sublist in recent_data for p in sublist]
    freq_map = Counter(flat_list)
    top_3 = freq_map.most_common(3)
    
    c1, c2, c3 = st.columns(3)
    if len(top_3) >= 1: c1.metric("🥇 Top Pattern", f"{top_3[0][0]}", f"{top_3[0][1]} Hits")
    if len(top_3) >= 2: c2.metric("🥈 Second Best", f"{top_3[1][0]}", f"{top_3[1][1]} Hits")
    if len(top_3) >= 3: c3.metric("🥉 Third Best", f"{top_3[2][0]}", f"{top_3[2][1]} Hits")

    # --- BAR CHART ANALYSIS ---
    st.subheader("📈 Pattern Bar Counter (Frequency Graph)")
    chart_df = pd.DataFrame(freq_map.items(), columns=['Pattern', 'Hits']).sort_values('Hits', ascending=False)
    st.bar_chart(chart_df.set_index('Pattern'))

    # --- JACKPOT LOGIC: WEEKLY VS MONTHLY ---
    st.divider()
    st.header("💎 Monthly vs Weekly Jackpot Logic")
    
    col_w, col_m = st.columns(2)
    
    with col_w:
        st.subheader("📅 Weekly Trends (Last 7 Days)")
        weekly_data = [p for sub in success_history[-7:] for p in sub]
        weekly_freq = Counter(weekly_data)
        st.write(weekly_freq.most_common(5))
        
    with col_m:
        st.subheader("📅 Monthly Trends (Last 30 Days)")
        monthly_data = [p for sub in success_history[-30:] for p in sub]
        monthly_freq = Counter(monthly_data)
        st.write(monthly_freq.most_common(5))

    # Jackpot: Common in both Weekly and Monthly
    weekly_set = set([p for p, c in weekly_freq.most_common(10)])
    monthly_set = set([p for p, c in monthly_freq.most_common(10)])
    jackpot_patterns = weekly_set.intersection(monthly_set)

    st.warning(f"🎯 **Jackpot Patterns (Common in Week & Month):** {list(jackpot_patterns)}")

    # --- SEQUENCE CHAIN (1 TO 5) ---
    st.divider()
    st.header("🔗 Sequence Chain Analysis")
    chain_size = st.radio("Chain की गहराई चुनें:", [1, 2, 3, 4, 5], horizontal=True)
    
    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i+1]
        if len(curr) >= chain_size:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt:
                    seq_counter[(combo, n)] += 1
    
    if seq_counter:
        st.table([{"Current Group": k[0], "Next Likely": k[1], "Total Hits": v} for k, v in seq_counter.most_common(10)])
    else:
        st.write("पर्याप्त डेटा नहीं है।")

    # --- FINAL PREDICTOR ---
    st.divider()
    if success_history:
        last_ps = success_history[-1]
        st.subheader(f"🔮 Today's Success: {last_ps}")
        final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
        if final_preds:
            st.success(f"कल के लिए 'Jackpot' सुझाव: **{list(set(final_preds))}**")

else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
