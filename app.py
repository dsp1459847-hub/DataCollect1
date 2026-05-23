import streamlit as st
import pandas as pd
from collections import Counter, defaultdict
from itertools import combinations

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.markdown("""
<style>
.big-box {
    border: 2px solid #c9c9c9;
    border-radius: 14px;
    padding: 12px;
    margin-bottom: 10px;
    background: #fff;
}
.big-box-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}
.small-box {
    border: 1px solid #d8d8d8;
    border-radius: 10px;
    padding: 10px;
    text-align: center;
    font-weight: 700;
    margin-bottom: 8px;
    background: #f8f8f8;
}
.good { color: #0a7a0a; font-weight: 700; }
.bad { color: #c00000; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("6-shift pooled analysis, unique/common/remainder numbers, probability, and backtest.")

SHIFT_ORDER = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']

if "manual_rows" not in st.session_state:
    st.session_state.manual_rows = {}

def clean_df(uploaded_file):
    uploaded_file.seek(0)
    if uploaded_file.name.lower().endswith('.csv'):
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

def last_valid_value(df_part, col):
    tmp = df_part[['DATE', col]].copy()
    tmp[col] = pd.to_numeric(tmp[col], errors='coerce')
    tmp = tmp.dropna(subset=[col])
    if len(tmp) == 0:
        return None, None
    r = tmp.iloc[-1]
    return int(r[col]), r['DATE'].date()

def build_backtest(df_part, shifts):
    rows = []
    per_shift_vals = {sh: [] for sh in shifts}
    per_shift_hits = {sh: Counter() for sh in shifts}
    per_shift_miss = {sh: Counter() for sh in shifts}

    for i in range(len(df_part)):
        cur = df_part.iloc[i]
        nxt = df_part.iloc[i + 1] if i + 1 < len(df_part) else None

        row = {"DATE": cur["DATE"].date()}
        pass_count = 0
        fail_count = 0

        if nxt is not None:
            nxt_vals = pd.to_numeric(nxt[shifts], errors='coerce').dropna().astype(int).tolist()
            nxt_set = set(nxt_vals)

            for sh in SHIFT_ORDER:
                if sh in shifts and pd.notna(cur[sh]):
                    val = int(cur[sh])
                    per_shift_vals[sh].append(val)
                    hit = any(((val + p) % 100) in nxt_set for p in range(100))
                    row[sh] = f"{val} ✅" if hit else f"{val} ❌"
                    if hit:
                        pass_count += 1
                        per_shift_hits[sh][val] += 1
                    else:
                        fail_count += 1
                        per_shift_miss[sh][val] += 1
                else:
                    row[sh] = ""
        else:
            for sh in SHIFT_ORDER:
                row[sh] = ""

        row["PASS"] = pass_count
        row["FAIL"] = fail_count
        rows.append(row)

    return add_accuracy(rows), per_shift_vals, per_shift_hits, per_shift_miss

def pool_analysis(per_shift_vals):
    all_values = []
    for sh in per_shift_vals:
        all_values.extend([int(x) % 100 for x in per_shift_vals[sh]])

    freq = Counter(all_values)
    unique_nums = sorted([n for n, c in freq.items() if c == 1])
    common_nums = sorted([n for n, c in freq.items() if c > 1])
    remainder_nums = sorted([n for n in range(100) if n not in set(freq.keys())])

    shift_summary = []
    for sh in per_shift_vals:
        vals = [int(x) % 100 for x in per_shift_vals[sh]]
        u = sum(1 for x in vals if freq[x] == 1)
        c = sum(1 for x in vals if freq[x] > 1)
        r = sum(1 for x in vals if x in remainder_nums)
        shift_summary.append({
            "Shift": sh,
            "Total": len(vals),
            "Unique": u,
            "Common": c,
            "Remainder": r
        })

    prob_df = pd.DataFrame([
        {"Number": n, "Count": c, "Probability %": round((c / len(all_values)) * 100, 2)}
        for n, c in freq.most_common(100)
    ])

    return pd.DataFrame(shift_summary), pd.DataFrame({"Number": unique_nums}), pd.DataFrame({"Number": common_nums}), pd.DataFrame({"Number": remainder_nums}), prob_df, freq

def top_shift_for_groups(per_shift_vals, group_nums):
    rows = []
    group_set = set(group_nums)
    for sh in per_shift_vals:
        vals = [int(x) % 100 for x in per_shift_vals[sh]]
        cnt = sum(1 for x in vals if x in group_set)
        rows.append({"Shift": sh, "Match Count": cnt})
    return pd.DataFrame(rows).sort_values("Match Count", ascending=False).reset_index(drop=True)

def render_boxes(items, title):
    st.markdown(f"<div class='big-box'><div class='big-box-title'>{title}</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, txt in enumerate(items):
        with cols[i % 4]:
            st.markdown(f"<div class='small-box'>{txt}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def mark_rank(i):
    if i == 0:
        return "◆"
    if i == 1:
        return "●"
    if i == 2:
        return "■"
    return "•"

def build_prediction_from_numbers(nums):
    out = []
    for i, n in enumerate(nums[:20]):
        out.append(f"{mark_rank(i)} {n}")
    return out

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'], key="data_uploader")

if not uploaded_file:
    st.info("Sidebar में file upload करें.")
    st.stop()

df, err = clean_df(uploaded_file)
if err:
    st.error(err)
    st.stop()

shifts_present = available_shift_cols(df)
if not shifts_present:
    st.error("No shift columns found.")
    st.stop()

for c in shifts_present:
    df[c] = pd.to_numeric(df[c], errors='coerce')

unique_dates = sorted(df['DATE'].dt.date.unique().tolist())

st.sidebar.header("⚙️ Mode")
mode = st.sidebar.selectbox("Select Mode", ["All Code", "Shift Wise"], key="mode_select")

st.sidebar.header("📅 Prediction Date")
prediction_date = st.sidebar.selectbox("Select Prediction Date", unique_dates, index=len(unique_dates)-1, key="pred_date")

st.sidebar.header("📆 History Limit")
history_limit = st.sidebar.radio("Select History Days", [30, 45], index=1, key="history_limit")

st.sidebar.header("✍️ Manual Override")
use_manual_range = st.sidebar.checkbox("Enable manual range override", value=False, key="manual_override")

if use_manual_range:
    manual_range = st.sidebar.date_input("Select Start and End Date", value=(unique_dates[0], prediction_date), min_value=unique_dates[0], max_value=unique_dates[-1], key="date_range")
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

df_range = df[(df['DATE'].dt.date >= start_date) & (df['DATE'].dt.date <= end_date)].copy().reset_index(drop=True)
if df_range.empty:
    st.error("Selected range में data नहीं है.")
    st.stop()

st.success(f"Selected prediction date: {prediction_date} | History range: {start_date} to {end_date}")

def render_all_code():
    st.header("📊 All Code Analysis")
    backtest_df, per_shift_vals, per_shift_hits, per_shift_miss = build_backtest(df_range, shifts_present)

    shift_summary, unique_df, common_df, remainder_df, prob_df, freq = pool_analysis(per_shift_vals)

    c1, c2, c3 = st.columns(3)
    c1.metric("Unique Count", len(unique_df))
    c2.metric("Common Count", len(common_df))
    c3.metric("Remainder Count", len(remainder_df))

    st.markdown("### Shift Wise Group Contribution")
    st.dataframe(shift_summary, use_container_width=True, hide_index=True)

    st.markdown("### Backtest History")
    st.dataframe(backtest_df, use_container_width=True, height=380, hide_index=True)

    st.markdown("### Unique / Common / Remainder")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("Unique")
        st.dataframe(unique_df, use_container_width=True, height=220, hide_index=True)
    with col2:
        st.write("Common")
        st.dataframe(common_df, use_container_width=True, height=220, hide_index=True)
    with col3:
        st.write("Remainder")
        st.dataframe(remainder_df, use_container_width=True, height=220, hide_index=True)

    st.markdown("### Probability / Frequency")
    st.dataframe(prob_df, use_container_width=True, height=260, hide_index=True)

    if len(prob_df) > 0:
        top_numbers = prob_df.head(20)["Number"].tolist()
        render_boxes(build_prediction_from_numbers(top_numbers), "Top 20 Probability Numbers")

    if len(unique_df) > 0:
        top_shift_unique = top_shift_for_groups(per_shift_vals, unique_df["Number"].tolist())
        st.markdown("### Which Shift Has Most Unique Numbers")
        st.dataframe(top_shift_unique, use_container_width=True, hide_index=True)

    if len(common_df) > 0:
        top_shift_common = top_shift_for_groups(per_shift_vals, common_df["Number"].tolist())
        st.markdown("### Which Shift Has Most Common Numbers")
        st.dataframe(top_shift_common, use_container_width=True, hide_index=True)

    if len(remainder_df) > 0:
        top_shift_rem = top_shift_for_groups(per_shift_vals, remainder_df["Number"].tolist())
        st.markdown("### Which Shift Has Most Remainder Numbers")
        st.dataframe(top_shift_rem, use_container_width=True, hide_index=True)

def render_shift_wise():
    st.header("📊 Shift Wise Analysis")
    selected_shift = st.selectbox("Select Shift", shifts_present, key="shift_select")
    backtest_df, per_shift_vals, per_shift_hits, per_shift_miss = build_backtest(df_range, shifts_present)
    shift_summary, unique_df, common_df, remainder_df, prob_df, freq = pool_analysis(per_shift_vals)

    st.markdown(f"### Backtest History - {selected_shift}")
    st.dataframe(backtest_df, use_container_width=True, height=380, hide_index=True)

    last_val, last_date = last_valid_value(df_range, selected_shift)
    if last_val is not None:
        st.caption(f"Last valid {selected_shift}: {last_val} on {last_date}")
        render_boxes(build_prediction_from_numbers([(last_val + i) % 100 for i in range(20)]), f"Current Shift Prediction - {selected_shift}")

    st.markdown("### Probability / Frequency")
    st.dataframe(prob_df, use_container_width=True, height=260, hide_index=True)

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'], key="data_uploader")
if not uploaded_file:
    st.stop()

if mode == "All Code":
    render_all_code()
else:
    render_shift_wise()
