import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म (Weekly) और लॉन्ग-टर्म (Monthly) डेटा का उपयोग करके सबसे पक्के पैटर्न खोजें।")

master_patterns = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
shifts = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"File read error: {e}")
        st.stop()

    df.columns = df.columns.astype(str).str.strip().str.upper()
    shifts = [c.strip().upper() for c in shifts]

    if 'DATE' not in df.columns:
        st.error("DATE column file mein nahi mili.")
        st.stop()

    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df = df.dropna(subset=['DATE']).copy()
    df = df.sort_values('DATE').reset_index(drop=True)

    available_shifts = [c for c in shifts if c in df.columns]
    missing_shifts = [c for c in shifts if c not in df.columns]

    if missing_shifts:
        st.warning(f"Missing columns: {missing_shifts}")

    if len(available_shifts) < 2:
        st.error("Kam se kam 2 shift columns required hain.")
        st.stop()

    for col in available_shifts:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("📅 Date Selection")
    unique_dates = sorted(df['DATE'].dt.date.unique().tolist())

    selected_date = st.sidebar.selectbox(
        "Select Date",
        unique_dates,
        index=len(unique_dates) - 1
    )

    history_days = st.sidebar.slider("History Days", 7, 100, 30)
    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30, 60, 90], value=30)

    df_filtered = df[df['DATE'].dt.date <= selected_date].copy().reset_index(drop=True)
    df_recent = df_filtered.tail(history_days).copy().reset_index(drop=True)

    st.header(f"📊 Selected Date: {selected_date}")
    st.write(f"Using last {len(df_recent)} rows for analysis.")

    if len(df_recent) < 2:
        st.warning("Backtest ke liye enough data nahi hai.")
        st.stop()

    success_history = []
    row_dates = []

    for i in range(len(df_recent) - 1):
        today_vals = pd.to_numeric(df_recent.iloc[i][available_shifts], errors='coerce').dropna()
        tomorrow_vals = pd.to_numeric(df_recent.iloc[i + 1][available_shifts], errors='coerce').dropna()

        today = set(today_vals.astype(int).tolist())
        tomorrow = set(tomorrow_vals.astype(int).tolist())

        row_dates.append(df_recent.iloc[i]['DATE'].date())

        if not today or not tomorrow:
            success_history.append([])
            continue

        found = []
        for val in today:
            for p in master_patterns:
                candidate = (val + p) % 100
                if candidate in tomorrow:
                    found.append(p)

        success_history.append(list(set(found)))

    recent_data = success_history[-window:] if window <= len(success_history) else success_history

    st.header(f"📊 पिछले {window} दिनों का सारांश")
    flat_list = [p for sublist in recent_data for p in sublist]
    freq_map = Counter(flat_list)
    top_3 = freq_map.most_common(3)

    c1, c2, c3 = st.columns(3)
    if len(top_3) >= 1:
        c1.metric("🥇 Top Pattern", f"{top_3[0][0]}", f"{top_3[0][1]} Hits")
    if len(top_3) >= 2:
        c2.metric("🥈 Second Best", f"{top_3[1][0]}", f"{top_3[1][1]} Hits")
    if len(top_3) >= 3:
        c3.metric("🥉 Third Best", f"{top_3[2][0]}", f"{top_3[2][1]} Hits")

    st.subheader("📈 Pattern Bar Counter (Frequency Graph)")
    if freq_map:
        chart_df = pd.DataFrame(freq_map.items(), columns=['Pattern', 'Hits']).sort_values('Hits', ascending=False)
        st.bar_chart(chart_df.set_index('Pattern'))
    else:
        st.info("इस window में कोई pattern नहीं मिला।")

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

    weekly_set = set([p for p, c in weekly_freq.most_common(10)])
    monthly_set = set([p for p, c in monthly_freq.most_common(10)])
    jackpot_patterns = weekly_set.intersection(monthly_set)

    st.warning(f"🎯 Jackpot Patterns (Common in Week & Month): {list(jackpot_patterns)}")

    st.divider()
    st.header("🔗 Sequence Chain Analysis")
    chain_size = st.radio("Chain की depth चुनें:", [1, 2, 3, 4, 5], horizontal=True)

    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i + 1]
        if len(curr) >= chain_size and len(nxt) > 0:
            for combo in combinations(sorted(curr), chain_size):
                for n in nxt:
                    seq_counter[(combo, n)] += 1

    if seq_counter:
        st.table([
            {"Current Group": k[0], "Next Likely": k[1], "Total Hits": v}
            for k, v in seq_counter.most_common(10)
        ])
    else:
        st.write("पर्याप्त डेटा नहीं है।")

    st.divider()
    if success_history:
        last_ps = success_history[-1]
        st.subheader(f"🔮 Selected-date latest success: {last_ps}")
        final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
        if final_preds:
            st.success(f"कल के लिए 'Jackpot' सुझाव: {list(set(final_preds))}")

    st.divider()
    st.subheader("📋 Backtest Table")
    bt_rows = []
    for i in range(max(0, len(success_history) - 10), len(success_history)):
        bt_rows.append({
            "Row": i + 1,
            "Date": str(row_dates[i]) if i < len(row_dates) else "",
            "Patterns Found": success_history[i]
        })

    if bt_rows:
        st.dataframe(pd.DataFrame(bt_rows), use_container_width=True)
    else:
        st.info("Backtest ke liye पर्याप्त data नहीं है.")

else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
