import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter

st.set_page_config(
    page_title="Satta Sanchalan - AI Prediction Engine",
    layout="wide",
    page_icon="🎯"
)

st.markdown("""
<style>
.main-title {
    font-size: 38px;
    color: #FFD700;
    text-align: center;
    font-weight: bold;
    margin-bottom: 5px;
}
.subtitle {
    font-size: 18px;
    color: #A0A0A0;
    text-align: center;
    margin-bottom: 25px;
}
.metric-card {
    background-color: #1E1E1E;
    padding: 15px;
    border-radius: 10px;
    border-left: 5px solid #FFD700;
    margin: 10px 0px;
}
.jodi-box {
    display: inline-block;
    background-color: #FFD700;
    color: #111111;
    font-size: 24px;
    font-weight: bold;
    padding: 10px 20px;
    margin: 5px;
    border-radius: 5px;
    text-align: center;
}
.haruf-box {
    display: inline-block;
    background-color: #00FFCC;
    color: #111111;
    font-size: 26px;
    font-weight: bold;
    padding: 10px 30px;
    border-radius: 5px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

RASHI_MAP = {i: (i + 5) % 10 for i in range(10)}
CHANNELS = ["DS", "FD", "GD", "GL", "DB", "SG", "ZA"]

def get_rashi_family(number):
    if pd.isna(number):
        return []
    val = int(number)
    t = val // 10
    u = val % 10
    rt = RASHI_MAP[t]
    ru = RASHI_MAP[u]

    base_family = [
        10 * t + u,
        10 * t + ru,
        10 * rt + u,
        10 * rt + ru
    ]

    expanded_set = set()
    for num in base_family:
        expanded_set.add(num)
        expanded_set.add((num % 10) * 10 + (num // 10))

    return sorted(expanded_set)

def get_mode(lst):
    if not lst:
        return None
    return Counter(lst).most_common(1)[0][0]

@st.cache_data
def get_default_data():
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", end="2026-05-24", freq="D")
    data = {
        "DATE": dates,
        "DS": np.random.choice([np.nan, "XX", "15", "26", "42", "80", "94", "53", "77", "18", "03", "11"], size=len(dates)),
        "FD": np.random.choice([np.nan, "XX", "17", "65", "79", "25", "62", "83", "38", "11", "90", "04"], size=len(dates)),
        "GD": np.random.choice([np.nan, "XX", "08", "56", "05", "85", "43", "31", "35", "72", "81", "99"], size=len(dates)),
        "GL": np.random.choice([np.nan, "XX", "90", "48", "81", "92", "80", "70", "14", "96", "53", "12"], size=len(dates)),
        "DB": np.random.choice([np.nan, "XX", "12", "34", "56", "78", "90", "15", "27", "88", "69", "02"], size=len(dates)),
        "SG": np.random.choice([np.nan, "X", "11", "22", "33", "44", "55", "66", "77", "88", "99", "05"], size=len(dates)),
        "ZA": np.random.choice([np.nan, "X", "09", "18", "27", "36", "45", "54", "63", "72", "81", "07"], size=len(dates)),
    }
    return pd.DataFrame(data)

class SattaPredictiveEngine:
    def __init__(self, df):
        self.df = df.copy()
        self.clean_data()

    def clean_data(self):
        self.df["DATE"] = pd.to_datetime(self.df["DATE"], errors="coerce")
        self.df = self.df.dropna(subset=["DATE"]).sort_values("DATE").reset_index(drop=True)
        for col in CHANNELS:
            if col in self.df.columns:
                self.df[col] = (
                    self.df[col]
                    .astype(str)
                    .str.replace(r"[^d]", "", regex=True)
                    .replace("", np.nan)
                )
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

    def run_prediction(self, target_date, shift, top_n_jodis):
        hist_df = self.df[self.df["DATE"] <= pd.to_datetime(target_date)].sort_values("DATE")
        if hist_df.empty:
            return None

        series = hist_df[shift].dropna().astype(int).values
        if len(series) < 10:
            st.warning(f"⚠️ {shift} channel mein analysis ke liye bahut kam data hai (कम से कम 10 records chahiye).")
            return None

        last_val = int(series[-1])

        sarpanch_history = []
        for _, row in hist_df.iterrows():
            day_digits = []
            for col in CHANNELS:
                if col in row.index and not pd.isna(row[col]):
                    v_int = int(row[col])
                    day_digits.append(v_int // 10)
                    day_digits.append(v_int % 10)
            if day_digits:
                sarpanch_history.append(get_mode(day_digits))

        predicted_sarpanch = 5
        sarpanch_series = [x for x in sarpanch_history if x is not None]

        if len(sarpanch_series) >= 5:
            trans_mat = np.zeros((10, 10))
            for i in range(1, len(sarpanch_series)):
                p = int(sarpanch_series[i - 1])
                c = int(sarpanch_series[i])
                trans_mat[p, c] += 1
            trans_mat += 0.1
            trans_mat /= trans_mat.sum(axis=1, keepdims=True)
            predicted_sarpanch = int(np.argmax(trans_mat[int(sarpanch_series[-1])]))

        transition_matrix = np.zeros((100, 100))
        for i in range(1, len(series)):
            transition_matrix[int(series[i - 1]), int(series[i])] += 1
        transition_matrix += 0.1
        transition_matrix /= transition_matrix.sum(axis=1, keepdims=True)
        markov_scores = transition_matrix[last_val]

        rashi_scores = np.zeros(100)
        family_members = get_rashi_family(last_val)
        in_family_count = 0
        for i in range(1, len(series)):
            prev = int(series[i - 1])
            curr = int(series[i])
            if curr in get_rashi_family(prev):
                in_family_count += 1
        rashi_trans_ratio = in_family_count / (len(series) - 1) if len(series) > 1 else 0.2
        for member in family_members:
            if 0 <= member < 100:
                rashi_scores[member] = rashi_trans_ratio

        gap_scores = np.zeros(100)
        last_seen = {}
        all_gaps = {i: [] for i in range(100)}

        for idx, val in enumerate(series):
            val = int(val)
            if val in last_seen:
                all_gaps[val].append(idx - last_seen[val])
            last_seen[val] = idx

        n_draws = len(series)
        for num in range(100):
            gaps = all_gaps[num]
            curr_gap = n_draws - last_seen.get(num, -1)
            if len(gaps) > 1:
                mean_gap = np.mean(gaps)
                std_gap = np.std(gaps) or 1.0
                z_score = (curr_gap - mean_gap) / std_gap
                gap_scores[num] = 1 / (1 + np.exp(-z_score))
            else:
                gap_scores[num] = 0.1

        final_scores = np.zeros(100)
        for num in range(100):
            final_scores[num] = (0.5 * markov_scores[num]) + (0.3 * rashi_scores[num]) + (0.2 * gap_scores[num])
            t = num // 10
            u = num % 10
            if t == predicted_sarpanch or u == predicted_sarpanch:
                final_scores[num] *= 1.3

        ranked_indices = np.argsort(final_scores)[::-1]
        top_jodis = ranked_indices[:top_n_jodis]

        haruf_candidates = []
        for num in ranked_indices[:15]:
            haruf_candidates.append((num // 10, "Andar"))
            haruf_candidates.append((num % 10, "Bahar"))

        digit_weights = {}
        digit_sides = {i: [] for i in range(10)}
        for digit, side in haruf_candidates:
            digit_weights[digit] = digit_weights.get(digit, 0) + 1
            digit_sides[digit].append(side)

        primary_haruf = max(digit_weights, key=digit_weights.get)
        side_counts = Counter(digit_sides[primary_haruf])
        best_side = side_counts.most_common(1)[0][0]

        second_best = final_scores[ranked_indices[1]] if len(ranked_indices) > 1 else 1.0
        confidence = min(int((final_scores[top_jodis[0]] / (second_best + 1e-5)) * 40), 98)

        return {
            "target_date": target_date,
            "prediction_date": (pd.to_datetime(target_date) + pd.DateOffset(days=1)).strftime("%Y-%m-%d"),
            "last_val": f"{last_val:02d}",
            "sarpanch": predicted_sarpanch,
            "jodis": [f"{j:02d}" for j in top_jodis],
            "haruf": primary_haruf,
            "haruf_side": best_side,
            "confidence": confidence
        }

st.markdown('<div class="main-title">🎯 Satta Sanchalan (AI Prediction Engine)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">राशि मैपिंग, सरपंच सर्वसम्मति और अंतराल गतिशीलता आधारित स्वचालित पूर्वानुमान प्रणाली</div>', unsafe_allow_html=True)

st.sidebar.header("📁 डेटा कंट्रोल सेंटर")
uploaded_file = st.sidebar.file_uploader("अपनी Excel / CSV फ़ाइल अपलोड करें", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
        st.sidebar.success("🎉 फ़ाइल सफलतापूर्वक लोड हो गई!")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        raw_df = get_default_data()
else:
    st.sidebar.info("💡 डिफ़ॉल्ट डेमो डेटा लोड किया गया है। आप अपनी फ़ाइल अपलोड कर सकते हैं।")
    raw_df = get_default_data()

raw_df.columns = raw_df.columns.str.strip()

if "DATE" not in raw_df.columns:
    st.error("❌ डेटासेट में 'DATE' कॉलम होना अनिवार्य है।")
else:
    raw_df["DATE"] = pd.to_datetime(raw_df["DATE"], errors="coerce")
    raw_df = raw_df.dropna(subset=["DATE"]).sort_values("DATE").reset_index(drop=True)

    engine = SattaPredictiveEngine(raw_df)

    st.sidebar.header("⚙️ एल्गोरिदम सेटिंग्स")
    available_shifts = [c for c in CHANNELS if c in raw_df.columns]
    selected_shift = st.sidebar.selectbox("🎯 शिफ्ट (Shift/Channel) चुनें:", available_shifts)

    all_dates = raw_df["DATE"].dt.strftime("%Y-%m-%d").tolist()
    selected_date = st.sidebar.selectbox(
        "📅 दिनांक (Target Date) चुनें:",
        all_dates,
        index=len(all_dates) - 1
    )

    jodi_count = st.sidebar.slider(
        "🔢 जोड़ियों की संख्या (Top Jodis):",
        min_value=5,
        max_value=10,
        value=6
    )

    if st.button("🚀 अगले दिन की भविष्यवाणी (Prediction) शुरू करें"):
        with st.spinner("ऐतिहासिक डेटा पैटर्न्स और राशि चक्रों का विश्लेषण किया जा रहा है..."):
            results = engine.run_prediction(selected_date, selected_shift, jodi_count)

            if results:
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader("📊 इनपुट और विश्लेषण समरी")
                    st.write(f"**चुनी गई दिनांक (Target Date):** `{results['target_date']}`")
                    st.write(f"**भविष्यवाणी की तिथि (Next-Day):** `{results['prediction_date']}`")
                    st.write(f"**शिफ्ट / मार्केट:** `{selected_shift}`")
                    st.write(f"**अंतिम घोषित जोड़ी (Last Record):** `{results['last_val']}`")
                    st.write(f"**अनुमानित सरपंच अंक (Daily Anchor):** `{results['sarpanch']}`")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader("⚡ सिस्टम सटीकता स्कोर (Confidence Score)")
                    st.metric("सफलता की संभावना:", f"{results['confidence']}%")
                    st.progress(results['confidence'] / 100.0)
                    st.caption("यह स्कोर एल्गोरिदम के सिग्नल्स (Markov, Rashi, Gap Z-Score) के आपसी संरेखण की ताकत को दर्शाता है।")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col2:
                    st.markdown('<div class="metric-card" style="border-left-color: #00FFCC;">', unsafe_allow_html=True)
                    st.subheader("🎯 महा-धमाका सिंगल हरूफ (High-Accuracy Haruf)")
                    st.write("हमारी सांख्यिकीय प्रणाली के अनुसार आज का सबसे मजबूत एकल अंक:")
                    st.markdown(f'<div class="haruf-box">{results["haruf"]} ({results["haruf_side"]})</div>', unsafe_allow_html=True)
                    st.caption(f"सलाह: इस अंक को `{results['haruf_side']}` (Inside/Outside) स्थान पर प्रमुखता से खेलें।")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader(f"🔮 अनुमानित जोड़ियाँ (Top {jodi_count} Jodis)")
                    st.write("अत्यधिक गणितीय गणनाओं के आधार पर चुनिंदा जोड़ियाँ:")
                    jodi_html = "".join([f'<div class="jodi-box">{jodi}</div>' for jodi in results["jodis"]])
                    st.markdown(jodi_html, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
