import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म और लॉन्ग-टर्म डेटा से pattern analysis, backtest, tier matching, और prediction.")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
SHIFT_ORDER = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']

def clean_df(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    df.columns = df.columns.astype(str).str.strip().str.upper()
    if 'DATE' not in df.columns:
        return None, "DATE column file mein nahi mili."
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df = df.dropna(subset=['DATE']).copy()
    df = df.sort_values('DATE').reset_index(drop=True)
    return df, None

def available_shift_cols(df):
    return [c for c in SHIFT_ORDER if c in df.columns]

def has_hit(val, nxt_vals):
    return any(((val + p) % 100) in nxt_vals for p in MASTER_PATTERNS)

def safe_window_default(n):
    options = [1, 3, 7, 10, 15, 30, 45]
    valid = [x for x in options if x <= n]
    return max(valid) if valid else 1

def add_accuracy(df_rows):
    out = []
    for r in df_rows:
        p = int(r.get("PASS", 0))
        f = int(r.get("FAIL", 0))
        total = p + f
        acc = round((p / total) * 100, 2) if total > 0 else 0.0
        rr = dict(r)
        rr["ACCURACY %"] = acc
        out.append(rr)
    return pd.DataFrame(out)

def build_all_history(df_part, shifts):
    success_history = []
    backtest_rows = []
    seq_counter = Counter()
    tier_rows = []

    for i in range(len(df_part) - 1):
        cur = df_part.iloc[i]
        nxt = df_part.iloc[i + 1]

        cur_vals = pd.to_numeric(cur[shifts], errors='coerce').dropna().astype(int).tolist()
        nxt_vals = pd.to_numeric(nxt[shifts], errors='coerce').dropna().astype(int).tolist()
        nxt_set = set(nxt_vals)

        found_patterns = []
        for v in set(cur_vals):
            for p in MASTER_PATTERNS:
                if (v + p) % 100 in nxt_set:
                    found_patterns.append(p)
        found_patterns = list(dict.fromkeys(found_patterns))
        success_history.append(found_patterns)

        for combo_size in [1, 2, 3]:
            if len(found_patterns) >= combo_size:
                for combo in combinations(sorted(found_patterns), combo_size):
                    for n in nxt_vals:
                        seq_counter[(combo, n)] += 1

        row = {"DATE": cur["DATE"].date()}
        pass_count = 0
        fail_count = 0
        for sh in SHIFT_ORDER:
            if sh in shifts and pd.notna(cur[sh]):
                val = int(cur[sh])
                hit = has_hit(val, nxt_set)
                row[sh] = f"{val} ✅" if hit else f"{val} ❌"
                pass_count += 1 if hit else 0
                fail_count += 0 if hit else 1
            else:
                row[sh] = ""
        row["PASS"] = pass_count
        row["FAIL"] = fail_count
        backtest_rows.append(row)

    for rank, ((combo, num), count) in enumerate(seq_counter.most_common(20), start=1):
        tier_rows.append({
            "Tier": f"Tier {rank}",
            "Combo": str(combo),
            "Generated": num,
            "Hits": count
        })

    return success_history, add_accuracy(backtest_rows), pd.DataFrame(tier_rows), seq_counter

def build_shift_history(df_part, shift, available_shifts):
    success_history = []
    rows = []
    seq_counter = Counter()
    tier_rows = []

    for i in range(len(df_part) - 1):
        cur = df_part.iloc[i]
        nxt = df_part.iloc[i + 1]

        cur_val_s = pd.to_numeric(pd.Series([cur[shift]]), errors='coerce').dropna()
        nxt_vals = pd.to_numeric(nxt.reindex(available_shifts), errors='coerce').dropna().astype(int).tolist()
        nxt_set = set(nxt_vals)

        if len(cur_val_s) == 0:
            success_history.append([])
            continue

        val = int(cur_val_s.iloc[0])
        found = [p for p in MASTER_PATTERNS if (val + p) % 100 in nxt_set]
        found = list(dict.fromkeys(found))
        success_history.append(found)

        for combo_size in [1, 2, 3]:
            if len(found) >= combo_size:
                for combo in combinations(sorted(found), combo_size):
                    for n in nxt_vals:
                        seq_counter[(combo, n)] += 1

        hit = has_hit(val, nxt_set)
        rows.append({
            "DATE": cur["DATE"].date(),
            shift: f"{val} ✅" if hit else f"{val} ❌",
            "PASS": 1 if hit else 0,
            "FAIL": 0 if hit else 1
        })

    for rank, ((combo, num), count) in enumerate(seq_counter.most_common(20), start=1):
        tier_rows.append({
            "Tier": f"Tier {rank}",
            "Combo": str(combo),
            "Generated": num,
            "Hits": count
        })

    return success_history, add_accuracy(rows), pd.DataFrame(tier_rows), seq_counter

def support_box(freq_map):
    top3 = freq_map.most_common(3)
    c1, c2, c3 = st.columns(3)
    if len(top3) > 0:
        c1.metric("Top 1", str(top3[0][0]), f"{top3[0][1]} Hits")
    if len(top3) > 1:
        c2.metric("Top 2", str(top3[1][0]), f"{top3[1][1]} Hits")
    if len(top3) > 2:
        c3.metric("Top 3", str(top3[2][0]), f"{top3[2][1]} Hits")

    if len(freq_map) > 3:
        rest = pd.DataFrame(freq_map.most_common()[3:], columns=["Pattern", "Hits"])
        st.markdown("### बाकी patterns")
        st.dataframe(rest, use_container_width=True, height=160, hide_index=True)

def best_tier_summary(tier_df):
    if tier_df.empty:
        return pd.DataFrame()
    return tier_df.sort_values("Hits", ascending=False).head(5).reset_index(drop=True)

def tier_vs_shift_summary(seq_counter, selected_shift):
    rows = []
    items = seq_counter.most_common(20)
    for rank, ((combo, num), count) in enumerate(items, start=1):
        rows.append({
            "Shift": selected_shift,
            "Tier": f"Tier {rank}",
            "Combo": str(combo),
            "Generated": num,
            "Hits": count
        })
    return pd.DataFrame(rows)

def show_prediction_box(numbers, title="Prediction Box"):
    st.markdown(f"### 🔮 {title}")
    st.dataframe(pd.DataFrame({"Generated Number": numbers}), use_container_width=True, height=180, hide_index=True)

def get_last_valid_value(df_part, col):
    tmp = df_part[['DATE', col]].copy()
    tmp[col] = pd.to_numeric(tmp[col], errors='coerce')
    tmp = tmp.dropna(subset=[col])
    if len(tmp) == 0:
        return None, None
    last_row = tmp.iloc[-1]
    return int(last_row[col]), last_row['DATE'].date()

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

if not uploaded_file:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
    st.stop()

df, err = clean_df(uploaded_file)
if err:
    st.error(err)
    st.stop()

shifts_present = available_shift_cols(df)
if len(shifts_present) == 0:
    st.error("No shift columns found.")
    st.stop()

for c in shifts_present:
    df[c] = pd.to_numeric(df[c], errors='coerce')

unique_dates = sorted(df['DATE'].dt.date.unique().tolist())
if not unique_dates:
    st.error("No valid dates found.")
    st.stop()

st.sidebar.header("⚙️ Mode")
mode = st.sidebar.selectbox("Select Mode", ["All Code", "Shift Wise"], index=0)

st.sidebar.header("📅 Prediction Date")
prediction_date = st.sidebar.selectbox("Select Prediction Date", unique_dates, index=len(unique_dates)-1)

st.sidebar.header("📆 History Limit")
history_limit = st.sidebar.radio("Select History Days", [30, 45], index=1)

st.sidebar.header("✍️ Manual Override")
use_manual_range = st.sidebar.checkbox("Enable manual range override", value=False)

if use_manual_range:
    manual_range = st.sidebar.date_input(
        "Select Start and End Date",
        value=(unique_dates[0], prediction_date),
        min_value=unique_dates[0],
        max_value=unique_dates[-1]
    )
    if isinstance(manual_range, tuple) and len(manual_range) == 2:
        start_date, end_date = manual_range
    else:
        st.warning("Please select both start and end dates.")
        st.stop()
else:
    pred_idx = unique_dates.index(prediction_date)
    start_idx = max(0, pred_idx - history_limit + 1)
    start_date = unique_dates[start_idx]
    end_date = prediction_date

st.success(f"Selected prediction date: {prediction_date} | History range: {start_date} to {end_date}")

df_range = df[(df['DATE'].dt.date >= start_date) & (df['DATE'].dt.date <= end_date)].copy().reset_index(drop=True)
if len(df_range) < 2:
    st.error("Selected range में पर्याप्त data नहीं है.")
    st.stop()

def render_all_code():
    st.header("📊 All Code Analysis")
    success_history, backtest_df, tier_df, seq_counter = build_all_history(df_range, shifts_present)

    window_options = [1, 3, 7, 10, 15, 30, 45]
    default_window = safe_window_default(len(success_history))
    window = st.sidebar.select_slider("Select Days", options=window_options, value=default_window)

    recent_data = success_history[-window:] if window <= len(success_history) else success_history
    flat = [p for sub in recent_data for p in sub]
    freq_map = Counter(flat)

    support_box(freq_map)

    st.markdown("### 4-Tier Matching")
    st.dataframe(tier_df, use_container_width=True, height=240, hide_index=True)

    st.markdown("### Best Tier Summary")
    st.dataframe(best_tier_summary(tier_df), use_container_width=True, height=180, hide_index=True)

    st.markdown("### ✅ Backtest History")
    st.dataframe(backtest_df, use_container_width=True, height=420, hide_index=True)

    last_ps = success_history[-1]
    seq_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
    final_unique = list(dict.fromkeys(seq_preds))[:10]
    show_prediction_box(final_unique, "Current Prediction")

def render_shift_wise():
    st.header("📊 Shift Wise Analysis")
    selected_shift = st.selectbox("Select Shift", shifts_present, index=0)

    success_history, shift_df, tier_df, seq_counter = build_shift_history(df_range, selected_shift, shifts_present)

    window_options = [1, 3, 7, 10, 15, 30, 45]
    default_window = safe_window_default(len(success_history))
    window = st.sidebar.select_slider("Select Days", options=window_options, value=default_window)

    recent_data = success_history[-window:] if window <= len(success_history) else success_history
    flat = [p for sub in recent_data for p in sub]
    freq_map = Counter(flat)

    support_box(freq_map)

    st.markdown(f"### 4-Tier Matching - {selected_shift}")
    st.dataframe(tier_df, use_container_width=True, height=240, hide_index=True)

    st.markdown("### Best Tier Summary")
    st.dataframe(best_tier_summary(tier_df), use_container_width=True, height=180, hide_index=True)

    st.markdown(f"### ✅ Backtest History - {selected_shift}")
    st.dataframe(shift_df, use_container_width=True, height=420, hide_index=True)

    st.markdown("### Which Tier Passes More")
    st.dataframe(tier_vs_shift_summary(seq_counter, selected_shift), use_container_width=True, height=220, hide_index=True)

    last_val, last_date = get_last_valid_value(df_range, selected_shift)
    if last_val is None:
        st.warning("No valid latest value.")
        return

    st.caption(f"Last valid {selected_shift}: {last_val} on {last_date}")
    pred_nums = [(last_val + p) % 100 for p in MASTER_PATTERNS]
    pred_nums = list(dict.fromkeys(pred_nums))[:10]
    show_prediction_box(pred_nums, "Current Shift Prediction")

if mode == "All Code":
    render_all_code()
else:
    render_shift_wise()
