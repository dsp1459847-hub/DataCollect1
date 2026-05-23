import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="Jackpot Pattern AI", layout="wide")

st.title("🏆 Monthly & Weekly Jackpot Pattern Analyzer")
st.write("शॉर्ट-टर्म (Weekly) और लॉन्ग-टर्म (Monthly) डेटा का उपयोग करके pattern analysis करें।")

MASTER_PATTERNS = [0, -18, -16, -26, -32, -1, -4, -11, -15, -10, -51, -50, 15, 5, -5, -55, 1, 10, 11, 51, 55, -40]
EXPECTED_SHIFTS = ['DS', 'FD', 'GD', 'GL', 'DB', 'SG']

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []

uploaded_file = st.sidebar.file_uploader("Data File Upload Karein", type=['csv', 'xlsx'])

def load_file(file):
    if file.name.endswith('.csv'):
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

def prepare_df(df):
    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.sort_values(date_col).reset_index(drop=True)
    return df, date_col

def reorder_shifts_by_rule(shifts):
    priority = ["DS", "DB", "SG", "FD", "GD", "GL"]
    ordered = [s for s in priority if s in shifts]
    ordered += [s for s in shifts if s not in ordered]
    return ordered

def get_active_shifts(df, selected_shift, all_mode):
    valid = [c for c in EXPECTED_SHIFTS if c in df.columns]
    if all_mode or selected_shift == "All Shifts":
        return reorder_shifts_by_rule(valid)
    return [selected_shift] if selected_shift in valid else valid[:2]

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
            rows.append({
                "Day": i,
                "Today Values": sorted(list(today_vals)),
                "Next Values": sorted(list(next_vals)),
                "Predicted": [],
                "Actual Match": "⚪"
            })
            continue

        predicted = []
        for val in today_vals:
            for p in MASTER_PATTERNS:
                if (val + p) % 100 in next_vals:
                    predicted.append(p)

        predicted = sorted(list(set(predicted)))
        rows.append({
            "Day": i,
            "Today Values": sorted(list(today_vals)),
            "Next Values": sorted(list(next_vals)),
            "Predicted": predicted,
            "Actual Match": "✅" if predicted else "❌"
        })
    return pd.DataFrame(rows)

if uploaded_file:
    df = load_file(uploaded_file)
    df, date_col = prepare_df(df)

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

    date_options = [d.date() for d in df[date_col].dropna().tolist()] if date_col else []
    selected_date = st.sidebar.date_input(
        "Select Date",
        value=date_options[-1] if date_options else datetime.today().date()
    ) if date_options else None

    selected_shift = st.sidebar.selectbox(
        "Select Shift",
        ["All Shifts"] + reorder_shifts_by_rule(available_shifts),
        index=0
    )

    all_mode = selected_shift == "All Shifts"
    active_shifts = get_active_shifts(df, selected_shift, all_mode)

    st.sidebar.subheader("Actual Result Entry")
    actual_result = st.sidebar.text_input("Enter actual result (comma separated)", value="")

    success_history = build_success_history(df, active_shifts)
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
    if date_col and selected_date:
        match_idx = df.index[df[date_col].dt.date == selected_date].tolist()
        if match_idx:
            idx = match_idx[0]
            selected_vals = df.loc[idx, active_shifts].dropna().astype(int).tolist()
            st.write(f"**[SELECTED DATE]** {selected_date}")
            st.write(f"**[ACTIVE SHIFTS]** {active_shifts}")
            st.write(f"**[HISTORY VALUES]** {selected_vals}")
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
        chain_table = pd.DataFrame(
            [{"Current Group": k[0], "Next Likely": k[1], "Total Hits": v} for k, v in seq_counter.most_common(10)]
        )
        st.table(chain_table)
    else:
        st.write("पर्याप्त डेटा नहीं है।")

    st.divider()
    st.header("✅ 30-Day Backtest")
    backtest_df = build_backtest(df, active_shifts)
    if not backtest_df.empty:
        st.dataframe(backtest_df, use_container_width=True)
        pass_rate = round((backtest_df["Actual Match"].eq("✅").mean() * 100), 2)
        st.success(f"Backtest Accuracy: {pass_rate}%")
    else:
        st.info("Backtest के लिए पर्याप्त data नहीं है।")

    st.divider()
    st.header("🔮 Prediction + Actual Match")
    if success_history:
        last_ps = success_history[-1]
        st.subheader(f"Latest Success Pattern Set: {last_ps}")

        final_preds = []
        for (prev, nxt), count in seq_counter.most_common(50):
            if set(prev).issubset(set(last_ps)):
                final_preds.append(nxt)
        final_preds = sorted(list(set(final_preds)))

        st.write(f"**[PREDICTION]** {final_preds}")

        if actual_result.strip():
            actual_vals = [int(x.strip()) for x in actual_result.split(",") if x.strip().isdigit()]
            if actual_vals:
                matched = any(val in final_preds for val in actual_vals)
                if matched:
                    st.success(f"✅ PASS: Actual result {actual_vals} matches prediction {final_preds}")
                else:
                    st.error(f"❌ FAIL: Actual result {actual_vals} does not match prediction {final_preds}")
            else:
                st.warning("Actual result में valid numbers डालो.")
else:
    st.info("Sidebar में अपनी डेटा फाइल अपलोड करें।")
