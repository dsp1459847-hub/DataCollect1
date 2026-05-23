import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']
SHIFT_PRIORITY = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']

if "last_prediction" not in st.session_state:
    st.session_state["last_prediction"] = None

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

def load_file(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df

def detect_date_col(df):
    for c in ["DATE", "DAY", "DATETIME", "TIME", "SHIFT_DATE"]:
        if c in df.columns:
            return c
    return None

def prepare_df(df):
    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.sort_values(date_col).reset_index(drop=True)
    return df, date_col

def ordered_shifts(df_cols):
    valid = [c for c in EXPECTED_SHIFTS if c in df_cols]
    ordered = [s for s in SHIFT_PRIORITY if s in valid]
    ordered += [s for s in valid if s not in ordered]
    return ordered

def get_active_shifts(df, mode):
    valid = ordered_shifts(df.columns)
    if mode == "All Shifts":
        return valid
    return [mode] if mode in valid else valid[:2]

def auto_window_size(n):
    if n < 20:
        return 10
    if n < 60:
        return 30
    if n < 120:
        return 90
    if n < 250:
        return 100
    if n < 600:
        return 180
    return 500

def build_success_history(df, active_shifts):
    history = []
    for i in range(len(df) - 1):
        today_vals = set(df.loc[i, active_shifts].dropna().astype(int).values)
        next_vals = set(df.loc[i + 1, active_shifts].dropna().astype(int).values)
        if not today_vals or not next_vals:
            history.append([])
            continue
        matched = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    matched.append(p)
        history.append(sorted(list(set(matched))))
    return history

def build_backtest(df, active_shifts):
    rows = []
    for i in range(len(df) - 1):
        today_vals = set(df.loc[i, active_shifts].dropna().astype(int).values)
        next_vals = set(df.loc[i + 1, active_shifts].dropna().astype(int).values)
        predicted = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    predicted.append((val + p) % 100)
        predicted = sorted(list(set(predicted)))
        actual_hit = len(predicted) > 0
        rows.append({
            "Day": i,
            "Today Values": sorted(list(today_vals)),
            "Next Values": sorted(list(next_vals)),
            "Predicted Numbers": predicted,
            "Pass": "✅" if actual_hit else "❌"
        })
    return pd.DataFrame(rows)

def predict_numbers_from_history(df, active_shifts, history_window):
    sub = df.tail(history_window) if len(df) > history_window else df.copy()
    success = build_success_history(sub, active_shifts)
    flat_patterns = [p for sublist in success for p in sublist]
    freq = Counter(flat_patterns)

    seq_counter = Counter()
    for i in range(len(success) - 1):
        curr, nxt = success[i], success[i + 1]
        if curr and nxt:
            for combo in combinations(sorted(curr), 1):
                for n in nxt:
                    seq_counter[(combo, n)] += 1

    latest = success[-1] if success else []
    predicted_numbers = []
    for (prev, nxt), cnt in seq_counter.most_common(50):
        if set(prev).issubset(set(latest)):
            predicted_numbers.append((nxt) % 100)

    if not predicted_numbers:
        for p, c in freq.most_common(10):
            predicted_numbers.append((p) % 100)

    return sorted(list(set([n for n in predicted_numbers if 0 <= n < 100]))), freq

if uploaded_file:
    df = load_file(uploaded_file)
    df, date_col = prepare_df(df)

    avail = ordered_shifts(df.columns)
    if len(avail) < 2:
        st.error("कम से कम 2 shift columns required हैं.")
        st.stop()

    for col in avail:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("Controls")
    mode = st.sidebar.selectbox("Select Shift", ["All Shifts"] + avail, index=0)
    active_shifts = get_active_shifts(df, mode)

    auto_window = auto_window_size(len(df))
    backtest_window = st.sidebar.select_slider("Backtest Window", options=[30, 60, 90, 100, 180, 500], value=30)
    pred_window = auto_window

    st.sidebar.info(f"Auto Prediction Window: {pred_window}")

    actual_result = st.sidebar.text_input("Enter actual result (comma separated)", value="")

    date_options = [d.date() for d in df[date_col].dropna().tolist()] if date_col else []
    selected_date = st.sidebar.date_input("Select Date", value=date_options[-1] if date_options else datetime.today().date()) if date_options else None

    st.header(f"📊 Pattern Summary")
    predicted_numbers, freq_map = predict_numbers_from_history(df, active_shifts, pred_window)

    top_3 = freq_map.most_common(3)
    c1, c2, c3 = st.columns(3)
    if len(top_3) > 0:
        c1.metric("🥇 Top Pattern", f"{top_3[0][0]}", f"{top_3[0][1]} Hits")
    if len(top_3) > 1:
        c2.metric("🥈 Second Best", f"{top_3[1][0]}", f"{top_3[1][1]} Hits")
    if len(top_3) > 2:
        c3.metric("🥉 Third Best", f"{top_3[2][0]}", f"{top_3[2][1]} Hits")

    st.subheader("🔢 Predicted Numbers")
    if predicted_numbers:
        st.success(f"Prediction Numbers: {predicted_numbers}")
        st.session_state["last_prediction"] = predicted_numbers
    else:
        st.info("Number prediction नहीं मिली।")

    st.divider()
    st.header("✅ Backtest")
    backtest_df = build_backtest(df.tail(backtest_window), active_shifts)
    if not backtest_df.empty:
        st.dataframe(backtest_df, use_container_width=True)
        pass_rate = round((backtest_df["Pass"].eq("✅").mean() * 100), 2)
        st.success(f"Backtest Accuracy: {pass_rate}%")

    st.divider()
    st.header("📅 Selected Date History")
    if date_col and selected_date:
        idxs = df.index[df[date_col].dt.date == selected_date].tolist()
        if idxs:
            idx = idxs[0]
            vals = df.loc[idx, active_shifts].dropna().astype(int).tolist()
            st.write(f"**[SELECTED DATE]** {selected_date}")
            st.write(f"**[ACTIVE SHIFTS]** {active_shifts}")
            st.write(f"**[HISTORY VALUES]** {vals}")

    st.divider()
    st.header("🎯 Actual Result Check")
    if actual_result.strip():
        actual_vals = [int(x.strip()) for x in actual_result.split(",") if x.strip().isdigit()]
        if actual_vals:
            matched = any(v in predicted_numbers for v in actual_vals)
            if matched:
                st.success(f"✅ PASS: {actual_vals} matches {predicted_numbers}")
            else:
                st.error(f"❌ FAIL: {actual_vals} does not match {predicted_numbers}")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
