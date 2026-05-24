import streamlit as st
import pandas as pd
from collections import Counter
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")
st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")

SHIFT_ORDER = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']
MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
CANDIDATE_WINDOWS = [30, 60, 90, 100, 180, 500]

if "history_df" not in st.session_state:
    st.session_state["history_df"] = pd.DataFrame()
if "last_key" not in st.session_state:
    st.session_state["last_key"] = None
if "last_prediction" not in st.session_state:
    st.session_state["last_prediction"] = []

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

def normalize_df(df):
    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    return df, date_col

def merge_history(base, new_df):
    if base is None or base.empty:
        merged = new_df.copy()
    else:
        merged = pd.concat([base, new_df], ignore_index=True)
    merged.columns = merged.columns.astype(str).str.strip().str.upper()
    date_col = detect_date_col(merged)
    if date_col:
        merged[date_col] = pd.to_datetime(merged[date_col], errors="coerce")
        merged = merged.sort_values(date_col)
        merged = merged.drop_duplicates(subset=[date_col] + [c for c in merged.columns if c != date_col], keep="last")
    else:
        merged = merged.drop_duplicates(keep="last")
    return merged.reset_index(drop=True)

def available_shifts(df):
    return [c for c in SHIFT_ORDER if c in df.columns]

def get_shifts(df, mode):
    shifts = available_shifts(df)
    if mode == "All Shifts":
        return shifts
    return [mode] if mode in shifts else shifts[:1]

def row_values(df, idx, shifts):
    vals = df.iloc[idx][shifts].dropna().tolist()
    out = []
    for v in vals:
        try:
            out.append(int(float(v)) % 100)
        except:
            pass
    return out

def build_chain(df, shifts):
    chain = []
    for i in range(len(df) - 1):
        curr = set(row_values(df, i, shifts))
        nxt = set(row_values(df, i + 1, shifts))
        if curr and nxt:
            hits = []
            for v in curr:
                for p in MASTER_PATTERNS:
                    cand = (v + p) % 100
                    if cand in nxt:
                        hits.append(cand)
            chain.append(sorted(set(hits)))
        else:
            chain.append([])
    return chain

def score_frequency(chain):
    flat = [x for row in chain for x in row]
    return Counter(flat)

def evaluate_window(df, shifts, window):
    sub = df.tail(min(window, len(df))).copy()
    if len(sub) < 2:
        return 0
    chain = build_chain(sub, shifts)
    freq = score_frequency(chain)
    if not chain:
        return 0
    recent = chain[-1] if chain[-1] else []
    score = len(recent) * 10
    score += sum(c for n, c in freq.most_common(5))
    score += len(freq)
    return score

def best_window_picker(df, shifts, candidates=CANDIDATE_WINDOWS):
    best_w = candidates[0]
    best_score = -1
    details = []
    for w in candidates:
        s = evaluate_window(df, shifts, w)
        details.append((w, s))
        if s > best_score:
            best_score = s
            best_w = w
    return best_w, details

def predict_for_shift(df, shift, window):
    if shift not in df.columns or len(df) < 2:
        return []
    sub = df.tail(min(window, len(df))).copy()
    chain = build_chain(sub, [shift])
    freq = score_frequency(chain)
    latest = chain[-1] if chain else []
    result = []
    for x in latest:
        result.append(x)
    for n, c in freq.most_common(20):
        result.append(n)
    result = [int(x) % 100 for x in result if 0 <= int(x) < 100]
    return list(dict.fromkeys(result[:10]))

def predict_all(df, shifts, window):
    out = {}
    for s in shifts:
        out[s] = predict_for_shift(df, s, window)
    return out

def build_backtest(df, shifts, window):
    sub = df.tail(min(window, len(df))).copy()
    rows = []
    for s in shifts:
        chain = build_chain(sub, [s])
        freq = score_frequency(chain)
        rows.append({
            "Shift": s,
            "Top 5 Frequencies": freq.most_common(5),
            "Latest Hits": chain[-1] if chain else [],
        })
    return pd.DataFrame(rows)

uploaded_file = st.sidebar.file_uploader("Base Data File Upload Karein", type=["csv", "xlsx"])
append_file = st.sidebar.file_uploader("Append History File", type=["csv", "xlsx"])

if st.sidebar.button("Update History"):
    if append_file is None:
        st.warning("Append करने के लिए file upload करो.")
    else:
        new_df = load_file(append_file)
        new_df, _ = normalize_df(new_df)
        st.session_state["history_df"] = merge_history(st.session_state["history_df"], new_df)
        st.session_state["last_prediction"] = []
        st.session_state["last_key"] = None
        st.success("History updated.")

if st.session_state["history_df"].empty and uploaded_file is not None:
    base_df = load_file(uploaded_file)
    base_df, _ = normalize_df(base_df)
    st.session_state["history_df"] = base_df.copy()

df = st.session_state["history_df"]

if df.empty:
    st.info("Sidebar में data file upload करो.")
    st.stop()

df, date_col = normalize_df(df)
shifts = available_shifts(df)
if not shifts:
    st.error("No valid shift columns found.")
    st.stop()

for c in shifts:
    df[c] = pd.to_numeric(df[c], errors="coerce")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Select Shift", ["All Shifts"] + shifts, index=0)
selected_shift = mode

if date_col:
    dates = sorted([d.date() for d in df[date_col].dropna().tolist()])
    selected_date = st.sidebar.date_input("Select Date", value=dates[-1], min_value=dates[0], max_value=dates[-1]) if dates else None
else:
    selected_date = None

manual_window = st.sidebar.checkbox("Manual Window", value=False)
if manual_window:
    pred_window = st.sidebar.select_slider("Prediction Window", options=CANDIDATE_WINDOWS, value=90)
else:
    pred_window, win_details = best_window_picker(df, shifts)
    st.sidebar.info(f"Auto Best Window: {pred_window}")
    st.sidebar.write({w: s for w, s in win_details})

key = (selected_shift, str(selected_date), len(df), pred_window)
if st.session_state["last_key"] != key:
    st.session_state["last_key"] = key
    st.session_state["last_prediction"] = []

if selected_date and date_col:
    filtered_df = df[df[date_col].dt.date <= selected_date].copy()
else:
    filtered_df = df.copy()
filtered_df = filtered_df.reset_index(drop=True)

st.header("📊 Pattern Summary")

if selected_shift == "All Shifts":
    pred_map = predict_all(filtered_df, shifts, pred_window)
    combined = []
    for s in shifts:
        combined.extend(pred_map[s])
    combined = list(dict.fromkeys([n for n in combined if 0 <= n < 100]))
    st.success(f"All Shifts Prediction: {combined[:10]}")
    st.write(pred_map)
    st.session_state["last_prediction"] = combined[:10]
else:
    pred_nums = predict_for_shift(filtered_df, selected_shift, pred_window)
    st.success(f"{selected_shift} Prediction: {pred_nums}")
    st.session_state["last_prediction"] = pred_nums

st.divider()
st.header("✅ Backtest")
bt = build_backtest(filtered_df, shifts, min(30, len(filtered_df)))
if not bt.empty:
    st.dataframe(bt, use_container_width=True)

st.divider()
st.header("📅 Selected Date View")
if date_col and selected_date:
    idxs = df.index[df[date_col].dt.date == selected_date].tolist()
    if idxs:
        i = idxs[0]
        st.write(f"**[DATE]** {selected_date}")
        st.write(f"**[ROW]** {row_values(df, i, shifts)}")
