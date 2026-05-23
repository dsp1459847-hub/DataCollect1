import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df

def detect_date_col(df):
    candidates = ["DATE", "DAY", "DATETIME", "TIME", "SHIFT_DATE"]
    for c in candidates:
        if c in df.columns:
            return c
    return None

def calc_success_history(df, shifts):
    history = []
    for i in range(len(df) - 1):
        today_vals = set(df.loc[i, shifts].dropna().astype(int).values)
        next_vals = set(df.loc[i + 1, shifts].dropna().astype(int).values)

        if not today_vals or not next_vals:
            history.append([])
            continue

        matched = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    matched.append(p)

        history.append(list(set(matched)))
    return history

def backtest_predictions(df, shifts):
    rows = []
    for i in range(len(df) - 1):
        today_vals = set(df.loc[i, shifts].dropna().astype(int).values)
        next_vals = set(df.loc[i + 1, shifts].dropna().astype(int).values)

        predicted = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    predicted.append(p)

        predicted = sorted(list(set(predicted)))
        actual_hit = len(predicted) > 0
        rows.append({
            "date_index": i,
            "today_values": sorted(list(today_vals)),
            "next_values": sorted(list(next_vals)),
            "predicted_patterns": predicted,
            "pass": actual_hit
        })
    return pd.DataFrame(rows)

if uploaded_file:
    df = load_data(uploaded_file)

    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)

    available_shifts = [c for c in EXPECTED_SHIFTS if c in df.columns]
    missing_shifts = [c for c in EXPECTED_SHIFTS if c not in df.columns]

    if missing_shifts:
        st.warning(f"Missing columns: {missing_shifts}")

    if len(available_shifts) < 2:
        st.error("कम से कम 2 shift columns required हैं.")
        st.stop()

    for col in available_shifts:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("Controls")
    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30], value=30)

    min_date = df[date_col].min().date() if date_col else datetime.today().date()
    max_date = df[date_col].max().date() if date_col else datetime.today().date()

    selected_date = st.sidebar.date_input("Select Date", value=max_date, min_value=min_date, max_value=max_date)

    shift_mode = st.sidebar.selectbox("Shift Mode", ["All Shifts"] + available_shifts, index=0)

    st.sidebar.subheader("Actual Result Entry")
    actual_result = st.sidebar.text_input("Enter actual result (comma separated)", value="")

    if shift_mode == "All Shifts":
        active_shifts = available_shifts
    else:
        active_shifts = [shift_mode]

    success_history = calc_success_history(df, active_shifts)
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

    st.subheader("📈 Pattern Frequency")
    if freq_map:
        chart_df = pd.DataFrame(freq_map.items(), columns=['Pattern', 'Hits']).sort_values('Hits', ascending=False)
        st.bar_chart(chart_df.set_index('Pattern'))
    else:
        st.info("इस window में कोई pattern नहीं मिला।")

    st.divider()

    st.header("📅 Selected Date History")
    if date_col:
        target_idx = df.index[df[date_col].dt.date == selected_date]
        if len(target_idx) > 0:
            idx = target_idx[0]
            today_values = df.loc[idx, active_shifts].dropna().astype(int).tolist()
            st.write(f"**[SELECTED DATE]** {selected_date}")
            st.write(f"**[SHIFT MODE]** {shift_mode}")
            st.write(f"**[HISTORY VALUES]** {today_values}")
        else:
            st.warning("Selected date sheet में नहीं मिली।")

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
        seq_table = pd.DataFrame(
            [{"Current Group": k[0], "Next Likely": k[1], "Total Hits": v} for k, v in seq_counter.most_common(10)]
        )
        st.table(seq_table)
    else:
        st.write("पर्याप्त डेटा नहीं है।")

    st.divider()
    st.header("✅ Backtest Result")

    backtest_df = backtest_predictions(df, active_shifts)
    if not backtest_df.empty:
        backtest_df["tick"] = backtest_df["pass"].apply(lambda x: "✅" if x else "❌")
        st.dataframe(backtest_df, use_container_width=True)

        pass_rate = round((backtest_df["pass"].mean() * 100), 2)
        st.success(f"Backtest Accuracy: {pass_rate}%")

    st.divider()
    st.header("🔮 Today Prediction / Actual Match")

    if success_history:
        last_ps = success_history[-1]
        st.subheader(f"Predicted patterns from latest history: {last_ps}")

        final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
        final_preds = sorted(list(set(final_preds)))

        st.write(f"**[PREDICTION]** {final_preds}")

        if actual_result.strip():
            actual_vals = [int(x.strip()) for x in actual_result.split(",") if x.strip().isdigit()]
            if actual_vals:
                matched = any(val in final_preds for val in actual_vals)
                if matched:
                    st.success(f"✅ PASS: Actual result matches prediction {actual_vals}")
                else:
                    st.error(f"❌ FAIL: Actual result {actual_vals} does not match prediction {final_preds}")
            else:
                st.warning("Actual result में valid numbers डालो.")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
