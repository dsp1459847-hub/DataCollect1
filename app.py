import streamlit as st
import pandas as pd
from collections import Counter, defaultdict
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")
st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

SHIFT_ORDER = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']
MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]

if "last_prediction" not in st.session_state:
    st.session_state["last_prediction"] = None

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

def load_file(file):
    if file.name.endswith(".csv"):
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
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    return df, date_col

def active_shifts(df, mode):
    valid = [c for c in SHIFT_ORDER if c in df.columns]
    if mode == "All Shifts":
        return valid
    return [mode] if mode in valid else valid[:1]

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

def row_numbers(df, idx, shifts):
    vals = df.iloc[idx][shifts].dropna().astype(int).tolist()
    return [v % 100 for v in vals]

def build_shift_history(df, shifts):
    hist = []
    for i in range(len(df) - 1):
        curr = set(row_numbers(df, i, shifts))
        nxt = set(row_numbers(df, i + 1, shifts))
        if not curr or not nxt:
            hist.append([])
            continue
        hits = []
        for v in curr:
            for p in MASTER_PATTERNS:
                cand = (v + p) % 100
                if cand in nxt:
                    hits.append(cand)
        hist.append(sorted(list(set(hits))))
    return hist

def build_backtest(df, shifts):
    rows = []
    for i in range(len(df) - 1):
        curr = set(row_numbers(df, i, shifts))
        nxt = set(row_numbers(df, i + 1, shifts))
        predicted = []
        score = Counter()
        if curr and nxt:
            for v in curr:
                for p in MASTER_PATTERNS:
                    cand = (v + p) % 100
                    if cand in nxt:
                        predicted.append(cand)
                        score[cand] += 1
        predicted = sorted(list(set(predicted)))
        rows.append({
            "Day": i,
            "Current": sorted(list(curr)),
            "Next": sorted(list(nxt)),
            "Predicted": predicted,
            "Hit": "✅" if predicted else "❌"
        })
    return pd.DataFrame(rows)

def rank_numbers(df, shifts, window):
    sub = df.tail(window).copy()
    history = build_shift_history(sub, shifts)
    flat = [x for sublist in history for x in sublist]
    freq = Counter(flat)

    seq = Counter()
    for i in range(len(history) - 1):
        a, b = history[i], history[i + 1]
        if a and b:
            for x in a:
                for y in b:
                    seq[(x, y)] += 1

    latest = history[-1] if history else []
    ordered = []

    if latest:
        for x in latest:
            for (prev, nxt), c in seq.most_common():
                if prev == x:
                    ordered.append(nxt)

    if not ordered:
        ordered = [n for n, c in freq.most_common(20)]

    ordered = [n % 100 for n in ordered]
    ordered = list(dict.fromkeys(ordered))
    return ordered, freq, seq

def diversify_by_shift(base_numbers, shift_name):
    if not base_numbers:
        return []
    shift_seed = sum(ord(c) for c in shift_name) % 7 + 1
    result = []
    used = set()
    for n in base_numbers:
        cand = (n + shift_seed * 3) % 100
        if cand not in used:
            result.append(cand)
            used.add(cand)
    if not result:
        result = base_numbers[:]
    return result[:10]

if uploaded_file:
    df = load_file(uploaded_file)
    df, date_col = prepare_df(df)

    avail = [c for c in SHIFT_ORDER if c in df.columns]
    if len(avail) < 1:
        st.error("Shift columns नहीं मिले.")
        st.stop()

    for col in avail:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    st.sidebar.header("Controls")
    mode = st.sidebar.selectbox("Select Shift", ["All Shifts"] + avail, index=0)
    shifts = active_shifts(df, mode)

    backtest_window = st.sidebar.select_slider("Backtest Window", options=[30, 60, 90, 100, 180, 500], value=90)
    pred_window = auto_window_size(len(df))
    st.sidebar.info(f"Auto Prediction Window: {pred_window}")

    date_options = [d.date() for d in df[date_col].dropna().tolist()] if date_col else []
    selected_date = st.sidebar.date_input("Select Date", value=date_options[-1] if date_options else datetime.today().date()) if date_options else None

    st.header("📊 Summary")
    pred_nums, freq_map, seq_map = rank_numbers(df, shifts, pred_window)

    c1, c2, c3 = st.columns(3)
    top = freq_map.most_common(3)
    if len(top) > 0:
        c1.metric("Top", str(top[0][0]), f"{top[0][1]} hits")
    if len(top) > 1:
        c2.metric("Second", str(top[1][0]), f"{top[1][1]} hits")
    if len(top) > 2:
        c3.metric("Third", str(top[2][0]), f"{top[2][1]} hits")

    st.subheader("🔢 Prediction Numbers")
    main_pred = pred_nums[:10]
    shift_preds = {}
    for s in shifts:
        shift_preds[s] = diversify_by_shift(main_pred, s)

    if mode == "All Shifts":
        st.success(f"All Shifts Prediction: {main_pred}")
        st.write(shift_preds)
    else:
        st.success(f"{mode} Prediction: {shift_preds.get(mode, main_pred)}")

    st.divider()
    st.header("✅ Backtest")
    bt = build_backtest(df.tail(backtest_window), shifts)
    if not bt.empty:
        st.dataframe(bt, use_container_width=True)
        hit_rate = round((bt["Hit"].eq("✅").mean() * 100), 2)
        st.success(f"Backtest Accuracy: {hit_rate}%")

    st.divider()
    st.header("📅 Selected Date")
    if date_col and selected_date:
        idxs = df.index[df[date_col].dt.date == selected_date].tolist()
        if idxs:
            idx = idxs[0]
            vals = row_numbers(df, idx, shifts)
            st.write(f"**[DATE]** {selected_date}")
            st.write(f"**[SHIFTS]** {shifts}")
            st.write(f"**[VALUES]** {vals}")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
