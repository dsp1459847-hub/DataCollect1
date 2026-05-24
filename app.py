import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(
    page_title="Satta Sanchalan - AI Prediction Engine",
    layout="wide",
    page_icon="🎯"
)

# ------------------------------
# CUSTOM STYLE
# ------------------------------
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

# ------------------------------
# CONSTANTS
# ------------------------------
CHANNELS = ["DS", "FD", "GD", "GL", "DB", "SG", "ZA"]
RASHI_MAP = {i: (i + 5) % 10 for i in range(10)}

# ------------------------------
# HELPERS
# ------------------------------
def clean_jodi_series(series):
    s = series.astype(str).str.strip()
    s = s.replace({
        "": np.nan,
        "nan": np.nan,
        "NaN": np.nan,
        "None": np.nan,
        "XX": np.nan,
        "X": np.nan,
        "N/A": np.nan,
        "NA": np.nan
    })
    s = s.str.replace(r"[^d]", "", regex=True)
    s = s.str.zfill(2)
    s = s.where(s.str.len() == 2)
    return pd.to_numeric(s, errors="coerce")

def get_rashi_family(number):
    if pd.isna(number):
        return []
    val = int(number)
    t, u = val // 10, val % 10
    rt, ru = RASHI_MAP[t], RASHI_MAP[u]

    base_family = [
        10 * t + u,
        10 * t + ru,
        10 * rt + u,
        10 * rt + ru
    ]

    expanded = set()
    for num in base_family:
        expanded.add(num)
        expanded.add((num % 10) * 10 + (num // 10))
    return sorted(expanded)

def get_mode(lst):
    if not lst:
        return None
    return Counter(lst).most_common(1)[0][0]

# ------------------------------
# DEFAULT DATA
# ------------------------------
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

# ------------------------------
# ENGINE
# ------------------------------
class SattaPredictiveEngine:
    def __init__(self, df):
        self.df = df.copy()
        self.clean_data()

    def clean_data(self):
        self.df["DATE"] = pd.to_datetime(self.df["DATE"], errors="coerce")
        self.df = self.df.dropna(subset=["DATE"]).sort_values("DATE").reset_index(drop=True)

        for col in CHANNELS:
            if col in self.df.columns:
                self.df[col] = clean_jodi_series(self.df[col])

    def run_prediction(self, target_date, shift, top_n_jodis):
        hist_df = self.df[self.df["DATE"] <= pd.to_datetime(target_date)].copy()
        if hist_df.empty or shift not in hist_df.columns:
            return None

        series = hist_df[shift].dropna().astype(int).values
        valid_count = len(series)

        if valid_count < 3:
            st.warning(f"⚠️ {shift} channel mein valid records bahut kam hain: {valid_count}. कम से कम 3 chahiye.")
            return None

        last_val = int(series[-1])

        # Sarpanch
        sarpanch_history = []
        for _, row in hist_df.iterrows():
            digits = []
            for col in CHANNELS:
                if col in row.index and not pd.isna(row[col]):
                    v = int(row[col])
                    digits.append(v // 10)
                    digits.append(v % 10)
            mode = get_mode(digits)
            if mode is not None:
                sarpanch_history.append(mode)

        predicted_sarpanch = 5
        if len(sarpanch_history) >= 5:
            trans = np.zeros((10, 10))
            for i in range(1, len(sarpanch_history)):
                p = int(sarpanch_history[i - 1])
                c = int(sarpanch_history[i])
                trans[p, c] += 1
            trans += 0.1
            trans /= trans.sum(axis=1, keepdims=True)
            predicted_sarpanch = int(np.argmax(trans[int(sarpanch_history[-1])]))

        # Markov
        transition_matrix = np.zeros((100, 100))
        for i in range(1, len(series)):
            prev = int(series[i - 1])
            curr = int(series[i])
            if 0 <= prev < 100 and 0 <= curr < 100:
                transition_matrix[prev, curr] += 1
        transition_matrix += 0.1
        transition_matrix /= transition_matrix.sum(axis=1, keepdims=True)
        markov_scores = transition_matrix[last_val]

        # Rashi
        rashi_scores = np.zeros(100)
        family_members = get_rashi_family(last_val)
        in_family_count = 0
        for i in range(1, len(series)):
            prev = int(series[i - 1])
            curr = int(series[i])
            if curr in get_rashi_family(prev):
                in_family_count += 1
        rashi_ratio = in_family_count / (len(series) - 1) if len(series) > 1 else 0.2
        for member in family_members:
            if 0 <= member < 100:
                rashi_scores[member] = rashi_ratio

        # Gap
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

        # Ensemble
        final_scores = np.zeros(100)
        for num in range(100):
            final_scores[num] = 0.5 * markov_scores[num] + 0.3 * rashi_scores[num] + 0.2 * gap_scores[num]
            t, u = num // 10, num % 10
            if t == predicted_sarpanch or u == predicted_sarpanch:
                final_scores[num] *= 1.3

        ranked = np.argsort(final_scores)[::-1]
        top_jodis = ranked[:top_n_jodis]

        # Haruf
        haruf_candidates = []
        for num in ranked[:15]:
            haruf_candidates.append((num // 10, "Andar"))
            haruf_candidates.append((num % 10, "Bahar"))

        digit_weights = {}
        digit_sides = {i: [] for i in range(10)}
        for digit, side in haruf_candidates:
            digit_weights[digit] = digit_weights.get(digit, 0) + 1
            digit_sides[digit].append(side)

        primary_haruf = max(digit_weights, key=digit_weights.get)
        best_side = Counter(digit_sides[primary_haruf]).most_common(1)[0][0]
        second_best = final_scores[ranked[1]] if len(ranked) > 1 else 1.0

        confidence = min(int((final_scores[top_jodis[0]] / (second_best + 1e-5)) * 40), 98)
        confidence = int(confidence * min(valid_count / 10, 1.0))

        return {
            "target_date": target_date,
            "prediction_date": (pd.to_datetime(target_date) + pd.DateOffset(days=1)).strftime("%Y-%m-%d"),
            "last_val": f"{last_val:02d}",
            "sarpanch": predicted_sarpanch,
            "jodis": [f"{j:02d}" for j in top_jodis],
            "haruf": primary_haruf,
            "haruf_side": best_side,
            "confidence": confidence,
            "valid_count": valid_count
        }

# ------------------------------
# UI
# ------------------------------
st.markdown('<div class="main-title">🎯 Satta Sanchalan (AI Prediction Engine)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">राशि मैपिंग, सरपंच सर्वसम्मति और अंतराल गतिशीलता आधारित स्वचालित पूर्वानुमान प्रणाली</div>', unsafe_allow_html=True)

st.sidebar.header("📁 डेटा कंट्रोल सेंटर")
uploaded_file = st.sidebar.file_uploader("अपनी Excel / CSV फ़ाइल अपलोड करें", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        else:
            raw_df = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)
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

    if not available_shifts:
        st.error("❌ कोई valid channel column नहीं मिला. कृपया DS/FD/GD/GL/DB/SG/ZA में से कम से कम एक column रखें.")
        st.stop()

    selected_shift = st.sidebar.selectbox("🎯 शिफ्ट (Shift/Channel) चुनें:", available_shifts)
    all_dates = raw_df["DATE"].dt.strftime("%Y-%m-%d").tolist()
    selected_date = st.sidebar.selectbox("📅 दिनांक (Target Date) चुनें:", all_dates, index=len(all_dates) - 1)

    jodi_count = st.sidebar.slider("🔢 जोड़ियों की संख्या (Top Jodis):", min_value=5, max_value=10, value=6)

    valid_count = int(raw_df.loc[raw_df["DATE"] <= pd.to_datetime(selected_date), selected_shift].dropna().shape[0])
    st.sidebar.info(f"{selected_shift} channel में valid records: {valid_count}")

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
                    st.write(f"**Valid Records:** `{results['valid_count']}`")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader("⚡ सिस्टम सटीकता स्कोर (Confidence Score)")
                    st.metric("सफलता की संभावना:", f"{results['confidence']}%")
                    st.progress(results['confidence'] / 100.0)
                    st.caption("यह score model-agreement को दर्शाता है, guaranteed result नहीं.")
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
                    jodi_html = "".join([f'<div class="jodi-box">{j}</div>' for j in results["jodis"]])
                    st.markdown(jodi_html, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                with st.expander("🛠️ जानिए इस गणना के पीछे का गणित"):
                    st.write("यह prediction Markov, Rashi family, gap dynamics और Sarpanch digit blend से बनाई गई है.")
                    st.write("अगर data कम होगा, तो confidence भी automatically कम हो जाएगा.")
            else:
                st.error("Prediction नहीं बन सकी. कृपया दूसरे shift या अधिक data वाले file के साथ try करें.")
