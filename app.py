import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")
st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

SHIFT_ORDER = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']
MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]

if "history_df" not in st.session_state:
    st.session_state["history_df"] = pd.DataFrame()
if "last_prediction" not in st.session_state:
    st.session_state["last_prediction"] = None
if "status_msg" not in st.session_state:
    st.session_state["status_msg"] = ""

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

def standardize_df(df):
    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    return df, date_col

def merge_history(existing, new_df, date_col):
    if existing is None or existing.empty:
        merged = new_df.copy()
    else:
        merged = pd.concat([existing, new_df], ignore_index=True)
    if date_col and date_col in merged.columns:
        merged[date_col] = pd.to_datetime(merged[date_col], errors="coerce")
        merged = merged.sort_values(date_col).drop_duplicates().reset_index(drop=True)
    else:
        merged = merged.drop_duplicates().reset_index(drop=True)
    return merged

def ordered_shifts(df_cols):
    valid = [c for c in SHIFT_ORDER if c in df_cols]
    return valid

def active_shifts(df, mode):
    valid = ordered_shifts(df.columns)
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
    return [int(x) % 100 for x in df.iloc[idx][shifts].dropna().tolist()]

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
    for x in latest:
        for (prev, nxt), c in seq.most_common():
            if prev == x:
                ordered.append(nxt)
    if not ordered:
        ordered = [n for n, c in freq.most_common(20)]

    ordered = [n % 100 for n in ordered]
    ordered = list(dict.fromkeys(ordered))
    return ordered, freq

def diversify(base_numbers, shift_name):
    if not base_numbers:
        return []
    seed = sum(ord(c) for c in shift_name) % 9 + 1
    out = []
    used = set()
    for n in base_numbers:
        cand = (n + seed * 3) % 100
        if cand not in used:
            out.append(cand)
            used.add(cand)
    return out[:10]

def build_backtest(df, shifts):
    rows = []
    for i in range(len(df) - 1):
        curr = set(row_numbers(df, i, shifts))
        nxt = set(row_numbers(df, i + 1, shifts))
        pred = []
        for v in curr:
            for p in MASTER_PATTERNS:
                cand = (v + p) % 100
                if cand in nxt:
                    pred.append(cand)
        pred = sorted(list(set(pred)))
        rows.append({
            "Day": i,
            "Current": sorted(list(curr)),
            "Next": sorted(list(nxt)),
            "Predicted": pred,
            "Hit": "✅" if pred else "❌"
        })
    return pd.DataFrame(rows)

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=["csv", "xlsx"])
new_history_file = st.sidebar.file_uploader("Append New History File", type=["csv", "xlsx"])

if st.sidebar.button("Update History"):
    if new_history_file is None:
        st.warning("Append करने के लिए new history file upload करो.")
    else:
        new_df = load_file(new_history_file)
        new_df, new_date_col = standardize_df(new_df)

        if st.session_state["history_df"].empty:
            st.session_state["history_df"] = new_df.copy()
        else:
            existing = st.session_state["history_df"].copy()
            if "DATE" in existing.columns and "DATE" not in new_df.columns and new_date_col:
                new_df = new_df.rename(columns={new_date_col: "DATE"})
            st.session_state["history_df"] = merge_history(existing, new_df, "DATE" if "DATE" in new_df.columns or "DATE" in existing.columns else new_date_col)

        st.session_state["status_msg"] = "History updated successfully."

if uploaded_file and st.session_state["history_df"].empty:
    base_df = load_file(uploaded_file)
    base_df, base_date_col = standardize_df(base_df)
    st.session_state["history_df"] = base_df.copy()

df = st.session_state["history_df"]

if st.session_state["status_msg"]:
    st.success(st.session_state["status_msg"])

if not df.empty:
    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    avail = ordered_shifts(df.columns)
    if len(avail) < 1:
        st.error("Shift columns नहीं मिले.")
        st.stop()

    for col in avail:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    st.sidebar.header("Controls")
    mode = st.sidebar.selectbox("Select Shift", ["All Shifts"] + avail, index=0)
    shifts = active_shifts(df, mode)

    pred_window = auto_window_size(len(df))
    st.sidebar.info(f"Auto Prediction Window: {pred_window}")

    if date_col:
        date_options = [d.date() for d in df[date_col].dropna().tolist()]
        selected_date = st.sidebar.date_input("Select Date", value=date_options[-1] if date_options else datetime.today().date()) if date_options else None
    else:
        selected_date = None

    st.header("📊 Summary")
    pred_nums, freq_map = rank_numbers(df, shifts, pred_window)

    c1, c2, c3 = st.columns(3)
    top = freq_map.most_common(3)
    if len(top) > 0:
        c1.metric("Top", str(top[0][0]), f"{top[0][1]} hits")
    if len(top) > 1:
        c2.metric("Second", str(top[1][0]), f"{top[1][1]} hits")
    if len(top) > 2:
        c3.metric("Third", str(top[2][0]), f"{top[2][1]} hits")

    base_pred = pred_nums[:10]
    shift_preds = {s: diversify(base_pred, s) for s in shifts}

    st.subheader("🔢 Prediction Numbers")
    if mode == "All Shifts":
        st.success(f"All Shifts Prediction: {base_pred}")
        st.write(shift_preds)
    else:
        st.success(f"{mode} Prediction: {shift_preds.get(mode, base_pred)}")

    st.divider()
    st.header("✅ Backtest")
    bt = build_backtest(df.tail(min(30, len(df))), shifts)
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
    st.info("Sidebar में अपनी data file upload करो.")
