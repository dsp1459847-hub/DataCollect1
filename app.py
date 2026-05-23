import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म (Weekly) और लॉन्ग-टर्म (Monthly) डेटा का उपयोग करके pattern analysis, backtest, और shift-wise prediction.")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
SHIFT_ORDER = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

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

def get_available_shifts(df):
    return [c for c in SHIFT_ORDER if c in df.columns]

def detect_hit(curr_val, next_vals):
    return any(((curr_val + p) % 100) in next_vals for p in MASTER_PATTERNS)

def build_combined_history(df_part, shifts):
    success_history = []
    rows = []
    for i in range(len(df_part) - 1):
        cur = df_part.iloc[i]
        nxt = df_part.iloc[i + 1]
        cur_vals = pd.to_numeric(cur[shifts], errors='coerce').dropna().astype(int).tolist()
        nxt_vals = pd.to_numeric(nxt[shifts], errors='coerce').dropna().astype(int).tolist()
        cur_set = set(cur_vals)
        nxt_set = set(nxt_vals)
        found = []
        for v in cur_set:
            for p in MASTER_PATTERNS:
                if (v + p) % 100 in nxt_set:
                    found.append(p)
        found = list(dict.fromkeys(found))
        success_history.append(found)
        row = {"DATE": cur["DATE"].date()}
        pass_count = 0
        fail_count = 0
        for sh in SHIFT_ORDER:
            if sh in shifts and pd.notna(cur[sh]):
                val = int(cur[sh])
                hit = detect_hit(val, nxt_set)
                row[sh] = f"{val} ✅" if hit else f"{val} ❌"
                pass_count += 1 if hit else 0
                fail_count += 0 if hit else 1
            else:
                row[sh] = ""
        row["PASS"] = pass_count
        row["FAIL"] = fail_count
        rows.append(row)
    return success_history, rows

def build_shiftwise_history(df_part, selected_shift):
    if selected_shift not in df_part.columns:
        return [], []
    history = []
    rows = []
    s = selected_shift
    for i in range(len(df_part) - 1):
        cur = df_part.iloc[i]
        nxt = df_part.iloc[i + 1]
        cur_val = pd.to_numeric(pd.Series([cur[s]]), errors='coerce').dropna()
        nxt_vals = pd.to_numeric(nxt[SHIFT_ORDER if all(x in df_part.columns for x in SHIFT_ORDER) else [s]], errors='coerce').dropna().astype(int).tolist()
        if len(cur_val) == 0:
            history.append([])
            continue
        val = int(cur_val.iloc[0])
        found = [p for p in MASTER_PATTERNS if (val + p) % 100 in nxt_vals]
        found = list(dict.fromkeys(found))
        history.append(found)
        row = {"DATE": cur["DATE"].date(), s: f"{val} ✅" if detect_hit(val, set(nxt_vals)) else f"{val} ❌"}
        rows.append(row)
    return history, rows

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

if not uploaded_file:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
    st.stop()

df, err = clean_df(uploaded_file)
if err:
    st.error(err)
    st.stop()

available_shifts = get_available_shifts(df)
if len(available_shifts) == 0:
    st.error("Shift columns नहीं मिलीं.")
    st.stop()

for c in available_shifts:
    df[c] = pd.to_numeric(df[c], errors='coerce')

unique_dates = sorted(df['DATE'].dt.date.unique().tolist())
if not unique_dates:
    st.error("No valid dates found.")
    st.stop()

st.sidebar.header("⚙️ Mode")
mode = st.sidebar.selectbox("Select Mode", ["All Code", "Shift Wise"], index=0)

st.sidebar.header("📅 Prediction Date")
prediction_date = st.sidebar.selectbox("Select Prediction Date", unique_dates, index=len(unique_dates)-1)

st.sidebar.header("📆 Auto History Range")
auto_days = st.sidebar.slider("Auto History Days", 7, 100, 30)

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
    start_idx = max(0, pred_idx - auto_days + 1)
    start_date = unique_dates[start_idx]
    end_date = prediction_date

st.success(f"Selected prediction date: {prediction_date} | History range: {start_date} to {end_date}")

df_range = df[(df['DATE'].dt.date >= start_date) & (df['DATE'].dt.date <= end_date)].copy().reset_index(drop=True)
if len(df_range) < 2:
    st.error("Selected range में पर्याप्त data नहीं है.")
    st.stop()

st.sidebar.header("🎯 Display Controls")
show_chart = st.sidebar.checkbox("Show Frequency Chart", value=False)

def render_all_code():
    st.header("📊 All Code Analysis")
    success_history, backtest_rows = build_combined_history(df_range, available_shifts)
    if len(success_history) == 0:
        st.warning("Not enough data for combined analysis.")
        return

    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30, 60, 90], value=min(30, max(1, len(success_history))))
    recent_data = success_history[-window:] if window <= len(success_history) else success_history
    flat = [p for sub in recent_data for p in sub]
    freq_map = Counter(flat)
    top_3 = freq_map.most_common(3)

    c1, c2, c3 = st.columns(3)
    if len(top_3) > 0: c1.metric("🥇 Top Pattern", str(top_3[0][0]), f"{top_3[0][1]} Hits")
    if len(top_3) > 1: c2.metric("🥈 Second Best", str(top_3[1][0]), f"{top_3[1][1]} Hits")
    if len(top_3) > 2: c3.metric("🥉 Third Best", str(top_3[2][0]), f"{top_3[2][1]} Hits")

    if show_chart and freq_map:
        st.subheader("📈 Pattern Chart")
        chart_df = pd.DataFrame(freq_map.items(), columns=["Pattern", "Hits"]).sort_values("Hits", ascending=False)
        st.bar_chart(chart_df.set_index("Pattern"))

    st.divider()
    st.subheader("💎 Weekly vs Monthly")
    weekly_data = [p for sub in success_history[-7:] for p in sub]
    monthly_data = [p for sub in success_history[-30:] for p in sub]
    weekly_freq = Counter(weekly_data)
    monthly_freq = Counter(monthly_data)
    col1, col2 = st.columns(2)
    with col1:
        st.write("Weekly:", weekly_freq.most_common(5))
    with col2:
        st.write("Monthly:", monthly_freq.most_common(5))
    jackpot = list(set([p for p, _ in weekly_freq.most_common(10)]).intersection(set([p for p, _ in monthly_freq.most_common(10)])))
    st.warning(f"Jackpot Patterns: {jackpot}")

    st.divider()
    st.subheader("✅ Backtest History")
    backtest_df = pd.DataFrame(backtest_rows)
    st.dataframe(backtest_df, use_container_width=True, height=520)

    st.divider()
    st.subheader("🔮 Final Prediction")
    last_ps = success_history[-1] if success_history else []
    seq_counter = Counter()
    for i in range(len(recent_data) - 1):
        curr, nxt = recent_data[i], recent_data[i + 1]
        if len(curr) >= 1 and len(nxt) > 0:
            for combo in combinations(sorted(curr), 1):
                for n in nxt:
                    seq_counter[(combo, n)] += 1
    final_preds = [nxt for (prev, nxt), count in seq_counter.most_common(50) if set(prev).issubset(set(last_ps))]
    final_unique = list(dict.fromkeys(final_preds))[:10]
    pred_table = pd.DataFrame({"Date": [end_date] * len(final_unique), "Pattern": final_unique, "Generated Number": final_unique})
    st.dataframe(pred_table, use_container_width=True, height=260)
    st.success(f"Final predicted numbers: {final_unique}")

def render_shift_wise():
    st.header("📊 Shift Wise Analysis")
    selected_shift = st.selectbox("Select Shift", available_shifts, index=0)
    success_history, _ = build_shiftwise_history(df_range, selected_shift)

    if len(success_history) == 0:
        st.warning("Not enough data for this shift.")
        return

    window = st.sidebar.select_slider("Select Days", options=[1, 3, 7, 10, 15, 30, 60, 90], value=min(30, max(1, len(success_history))))
    recent_data = success_history[-window:] if window <= len(success_history) else success_history
    flat = [p for sub in recent_data for p in sub]
    freq_map = Counter(flat)
    top_3 = freq_map.most_common(3)

    c1, c2, c3 = st.columns(3)
    if len(top_3) > 0: c1.metric("🥇 Top Pattern", str(top_3[0][0]), f"{top_3[0][1]} Hits")
    if len(top_3) > 1: c2.metric("🥈 Second Best", str(top_3[1][0]), f"{top_3[1][1]} Hits")
    if len(top_3) > 2: c3.metric("🥉 Third Best", str(top_3[2][0]), f"{top_3[2][1]} Hits")

    if show_chart and freq_map:
        st.subheader("📈 Pattern Chart")
        chart_df = pd.DataFrame(freq_map.items(), columns=["Pattern", "Hits"]).sort_values("Hits", ascending=False)
        st.bar_chart(chart_df.set_index("Pattern"))

    st.divider()
    st.subheader(f"✅ Backtest History - {selected_shift}")
    shift_rows = []
    for i in range(len(df_range) - 1):
        cur = df_range.iloc[i]
        nxt = df_range.iloc[i + 1]
        cur_val_s = pd.to_numeric(pd.Series([cur[selected_shift]]), errors='coerce').dropna()
        nxt_vals = pd.to_numeric(nxt[available_shifts], errors='coerce').dropna().astype(int).tolist()
        if len(cur_val_s) == 0:
            continue
        val = int(cur_val_s.iloc[0])
        hit = detect_hit(val, set(nxt_vals))
        shift_rows.append({
            "DATE": cur["DATE"].date(),
            selected_shift: f"{val} ✅" if hit else f"{val} ❌",
            "PASS": 1 if hit else 0,
            "FAIL": 0 if hit else 1
        })
    st.dataframe(pd.DataFrame(shift_rows), use_container_width=True, height=520)

    st.divider()
    st.subheader(f"🔮 Final Prediction - {selected_shift}")
    last_vals = pd.to_numeric(df_range.iloc[-1][selected_shift:selected_shift+1], errors='coerce').dropna()
    if len(last_vals) == 0:
        st.warning("No valid latest value.")
        return
    last_val = int(last_vals.iloc[0])

    pred_nums = [(last_val + p) % 100 for p in MASTER_PATTERNS]
    pred_nums = list(dict.fromkeys(pred_nums))[:10]
    pred_table = pd.DataFrame({"Date": [end_date] * len(pred_nums), "Pattern": [selected_shift] * len(pred_nums), "Generated Number": pred_nums})
    st.dataframe(pred_table, use_container_width=True, height=260)
    st.success(f"Final predicted numbers: {pred_nums}")

if mode == "All Code":
    render_all_code()
else:
    render_shift_wise()
