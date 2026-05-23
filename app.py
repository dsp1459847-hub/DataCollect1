import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
expected_shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.astype(str).str.strip().str.upper()

    date_col = None
    for c in df.columns:
        if c in ['DATE', 'DAY', 'DATETIME', 'TIME', 'SHIFT_DATE']:
            date_col = c
            break

    if date_col:
        df = df.sort_values(date_col).reset_index(drop=True)

    available_shifts = [c for c in expected_shifts if c in df.columns]
    missing_shifts = [c for c in expected_shifts if c not in df.columns]

    if missing_shifts:
        st.warning(f"Missing columns: {missing_shifts}")

    if len(available_shifts) < 2:
        st.error("कम से कम 2 shift columns required हैं.")
        st.stop()

    for col in available_shifts:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    success_history = []
    backtest_rows = []

    for i in range(len(df) - 1):
        today_vals = set(df.loc[i, available_shifts].dropna().astype(int).values)
        next_vals = set(df.loc[i + 1, available_shifts].dropna().astype(int).values)

        if not today_vals or not next_vals:
            success_history.append([])
            continue

        matched = []
        for val in today_vals:
            for p in master_patterns:
                if (val + p) % 100 in next_vals:
                    matched.append(p)

        matched = list(set(matched))
        success_history.append(matched)

        backtest_rows.append({
            "today_index": i,
            "today_values": sorted(today_vals),
            "next_values": sorted(next_vals),
            "matched_patterns": matched
        })

    st.sidebar.header("⏱️ विश्लेषण की अवधि")
    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30], value=30)

    recent_data = success_history[-window:] if window <= len(success_history) else success_history
    flat_list = [p for sublist in recent_data for p in sublist]
    freq_map = Counter(flat_list)
    top_3 = freq_map.most_common(3)

    st.header(f"📊 पिछले {window} दिनों का सारांश")
    c1, c2, c3 = st.columns(3)
    if len(top_3) >= 1:
        c1.metric("🥇 Top Pattern", f"{top_3[0][0]}", f"{top_3[0][1]} Hits")
    if len(top_3) >= 2:
        c2.metric("🥈 Second Best", f"{top_3[1][0]}", f"{top_3[1][1]} Hits")
    if len(top_3) >= 3:
        c3.metric("🥉 Third Best", f"{top_3[2][0]}", f"{top_3[2][1]} Hits")

    st.subheader("📈 Pattern Frequency")
    if freq_map:
        chart_df = pd.DataFrame(freq_map.items(), columns=['Pattern', 'Hits']).sort_values('Hits', ascending=False)
        st.bar_chart(chart_df.set_index('Pattern'))
    else:
        st.info("इस window में कोई pattern नहीं मिला।")

    st.divider()
    st.header("💎 Weekly vs Monthly Logic")

    weekly_data = [p for sub in success_history[-7:] for p in sub]
    monthly_data = [p for sub in success_history[-30:] for p in sub]

    weekly_freq = Counter(weekly_data)
    monthly_freq = Counter(monthly_data)

    st.subheader("Weekly Trends")
    st.write(weekly_freq.most_common(5))

    st.subheader("Monthly Trends")
    st.write(monthly_freq.most_common(5))

    weekly_set = set([p for p, c in weekly_freq.most_common(10)])
    monthly_set = set([p for p, c in monthly_freq.most_common(10)])
    jackpot_patterns = weekly_set.intersection(monthly_set)

    st.warning(f"🎯 Jackpot Patterns: {list(jackpot_patterns)}")

    st.divider()
    st.header("🔗 Sequence Chain Analysis")

    chain_size = st.radio("Chain की गहराई चुनें:", [1, 2, 3, 4, 5], horizontal=True)

    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i + 1]
        if len(curr) >= chain_size and len(nxt) > 0:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt:
                    seq_counter[(combo, n)] += 1

    if seq_counter:
        st.table([{"Current Group": k[0], "Next Likely": k[1], "Total Hits": v} for k, v in seq_counter.most_common(10)])
    else:
        st.write("पर्याप्त डेटा नहीं है।")

    st.divider()
    if success_history:
        last_ps = success_history[-1]
        st.subheader(f"🔮 Today's Success: {last_ps}")
        final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
        if final_preds:
            st.success(f"कल के लिए Jackpot सुझाव: {list(set(final_preds))}")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
