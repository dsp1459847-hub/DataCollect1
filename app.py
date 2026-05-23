import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म और लॉन्ग-टर्म history के आधार पर pattern prediction.")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']
SHIFT_PRIORITY = ['DS', 'DB', 'SG', 'FD', 'GD', 'GL']

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []
if "last_prediction" not in st.session_state:
    st.session_state["last_prediction"] = None
if "locked_df_hash" not in st.session_state:
    st.session_state["locked_df_hash"] = None

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
        if not today_vals or not next_vals:
            rows.append({"Day": i, "Today Values": sorted(list(today_vals)), "Next Values": sorted(list(next_vals)), "Predicted": [], "Pass": "⚪"})
            continue
        predicted = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    predicted.append(p)
        predicted = sorted(list(set(predicted)))
        rows.append({"Day": i, "Today Values": sorted(list(today_vals)), "Next Values": sorted(list(next_vals)), "Predicted": predicted, "Pass": "✅" if predicted else "❌"})
    return pd.DataFrame(rows)

def predict_from_history(success_history, window=90):
    data = success_history[-window:] if len(success_history) >= window else success_history
    flat = [p for sub in data for p in sub]
    freq = Counter(flat)
    return freq

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

    backtest_window = st.sidebar.select_slider("Backtest Window", options=[30, 60, 90, 100, 180, 365, 500], value=90)
    pred_window = st.sidebar.select_slider("Prediction Window", options=[30, 60, 90, 100, 180, 365, 500], value=90)

    actual_result = st.sidebar.text_input("Enter actual result (comma separated)", value="")

    date_options = [d.date() for d in df[date_col].dropna().tolist()] if date_col else []
    selected_date = st.sidebar.date_input("Select Date", value=date_options[-1] if date_options else datetime.today().date()) if date_options else None

    success_history = build_success_history(df, active_shifts)
    recent_backtest = success_history[-backtest_window:] if len(success_history) >= backtest_window else success_history

    st.header(f"📊 Pattern Summary")
    freq_map = predict_from_history(success_history, pred_window)
    top_3 = freq_map.most_common(3)

    c1, c2, c3 = st.columns(3)
    if len(top_3) > 0:
        c1.metric("🥇 Top Pattern", f"{top_3[0][0]}", f"{top_3[0][1]} Hits")
    if len(top_3) > 1:
        c2.metric("🥈 Second Best", f"{top_3[1][0]}", f"{top_3[1][1]} Hits")
    if len(top_3) > 2:
        c3.metric("🥉 Third Best", f"{top_3[2][0]}", f"{top_3[2][1]} Hits")

    st.subheader("📈 Pattern Frequency")
    if freq_map:
        chart_df = pd.DataFrame(freq_map.items(), columns=["Pattern", "Hits"]).sort_values("Hits", ascending=False)
        st.bar_chart(chart_df.set_index("Pattern"))
    else:
        st.info("Pattern नहीं मिला।")

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
        else:
            st.warning("Selected date sheet में नहीं मिली।")

    st.divider()
    st.header("✅ Backtest")
    backtest_df = build_backtest(df, active_shifts)
    if not backtest_df.empty:
        st.dataframe(backtest_df, use_container_width=True)
        pass_rate = round((backtest_df["Pass"].eq("✅").mean() * 100), 2)
        st.success(f"Backtest Accuracy: {pass_rate}%")
    else:
        st.info("Backtest के लिए पर्याप्त data नहीं है।")

    st.divider()
    st.header("🔮 Prediction")
    final_preds = []
    if success_history:
        latest = success_history[-1]
        freq = predict_from_history(success_history, pred_window)
        seq_counter = Counter()
        seq_source = recent_backtest[-min(len(recent_backtest), 90):] if recent_backtest else []
        for i in range(len(seq_source) - 1):
            curr = seq_source[i]
            nxt = seq_source[i + 1]
            if curr and nxt:
                for combo in combinations(sorted(curr), 1):
                    for n in nxt:
                        seq_counter[(combo, n)] += 1
        for (prev, nxt), cnt in seq_counter.most_common(50):
            if set(prev).issubset(set(latest)):
                final_preds.append(nxt)
        if not final_preds:
            final_preds = [p for p, c in freq.most_common(10)]
        final_preds = sorted(list(set(final_preds)))
        st.write(f"**[PREDICTION NUMBERS]** {final_preds}")
        st.session_state["last_prediction"] = final_preds

        if actual_result.strip():
            actual_vals = [int(x.strip()) for x in actual_result.split(",") if x.strip().isdigit()]
            if actual_vals:
                matched = any(v in final_preds for v in actual_vals)
                if matched:
                    st.success(f"✅ PASS: Actual result {actual_vals} matches prediction {final_preds}")
                else:
                    st.error(f"❌ FAIL: Actual result {actual_vals} does not match prediction {final_preds}")
            else:
                st.warning("Valid numbers डालो.")
    else:
        st.warning("Prediction के लिए history नहीं मिली।")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
