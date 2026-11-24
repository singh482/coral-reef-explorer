import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Coral Reef Explorer & Ocean Climate Lab", layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# CHANGE OR ADD YOUR DATA HERE
# ==============================================================================
# 1. To REPLACE a dataset: swap the filename inside the list below.
# 2. To ADD more data (e.g., new 2027 surveys): append your CSV filename to the list!
#    Example: GLOBAL_DATA_FILES = ["global_bleaching_environmental.csv", "my_new_2027_reefs.csv"]
GLOBAL_DATA_FILES = ["global_bleaching_environmental.csv", "coral.csv"]
REGIONAL_DATA_FILES = ["coral_bleaching.csv"]
CLIMATE_DATA_FILES = ["realistic_ocean_climate_dataset.csv"]

# Optional: If your new CSV uses slightly different column names, map them here:
# Format -> "your_csv_column_name": "standard_app_column_name"
COLUMN_ALIASES = {
    "year": "Date_Year",
    "month": "Date_Month",
    "bleaching": "Percent_Bleaching",
    "bleaching_percent": "Percent_Bleaching",
    "lat": "Latitude_Degrees",
    "lon": "Longitude_Degrees",
    "sst": "SST (°C)",
    "ph": "pH Level",
    "species": "Species Observed",
}
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent

def find_file(filename: str) -> Path | None:
    for folder in [BASE_DIR, Path("."), Path("Users/Ravi/Documents/Visualising Data/project"), Path.home() / "Documents/Visualising Data/project"]:
        candidate = folder / filename
        if candidate.exists():
            return candidate
    return None

@st.cache_data(show_spinner=False)
def load_and_merge_csvs(file_list: list[str], numeric_cols: list[str]) -> pd.DataFrame | None:
    frames = []
    for fname in file_list:
        path = find_file(fname)
        if path is not None:
            df = pd.read_csv(path, low_memory=False)
            df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns and v not in df.columns})
            frames.append(df)
            if fname == "global_bleaching_environmental.csv" and len(file_list) == 2 and file_list[1] == "coral.csv":
                break
    if not frames:
        return None
    merged = pd.concat(frames, ignore_index=True)
    for col in numeric_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
    return merged

@st.cache_data(show_spinner=False)
def load_all_datasets():
    df_global = load_and_merge_csvs(
        GLOBAL_DATA_FILES,
        ["Percent_Bleaching", "Depth_m", "SSTA", "SSTA_DHW", "Temperature_Mean", "Temperature_Maximum",
         "Turbidity", "Windspeed", "Distance_to_Shore", "Cyclone_Frequency", "Latitude_Degrees",
         "Longitude_Degrees", "Date_Year", "Date_Month"]
    )
    df_regional = load_and_merge_csvs(
        REGIONAL_DATA_FILES,
        ["Year", "Temperature_Celsius", "SSTA", "DHW_Stress", "Hotspot", "ONI_Index", "Chlorophyll_A_mg_m3",
         "Bleaching_Percent", "Salinity", "Dissolved_O2", "pH", "Nitrate", "Distance_to_Shore_km", "NDVI", "Turbidity_NTU"]
    )
    df_climate = load_and_merge_csvs(
        CLIMATE_DATA_FILES,
        ["SST (°C)", "pH Level", "Species Observed"]
    )
    if df_climate is not None:
        df_climate["Severity_Clean"] = df_climate["Bleaching Severity"].fillna("None")
        df_climate["Heatwave_Num"] = df_climate["Marine Heatwave"].astype(int)
    return df_global, df_regional, df_climate

@st.cache_data(show_spinner=False)
def get_global_timeline_data(df_in: pd.DataFrame | None) -> pd.DataFrame | None:
    if df_in is None:
        return None
    valid = df_in.dropna(subset=["Date_Year", "Percent_Bleaching"]).copy()
    valid["Year"] = valid["Date_Year"].astype(int)
    valid = valid[valid["Year"].between(1980, 2030)]
    yearly = valid.groupby("Year").agg(
        surveys=("Percent_Bleaching", "count"),
        mean_bleaching=("Percent_Bleaching", "mean"),
        pct_world_bleached=("Percent_Bleaching", lambda s: (s > 0).mean() * 100.0),
        pct_severe=("Percent_Bleaching", lambda s: (s >= 30).mean() * 100.0),
        mean_ssta=("SSTA", "mean"),
        mean_dhw=("SSTA_DHW", "mean"),
    ).reset_index()
    return yearly[yearly["surveys"] >= 15].reset_index(drop=True)

# ------------------------------------------------------------------------------
# STYLING — LOW-OPACITY SEA LIGHT, SWIMMING FISH & BUBBLES + HIGH-OPACITY CONTENT
# ------------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titan+One&family=Fredoka:wght@600;700&family=Baloo+2:wght@600;700;800&display=swap');
html { scroll-behavior: smooth; }
.stApp {
    background: linear-gradient(180deg, #023e68 0%, #012547 34%, #001329 70%, #000814 100%) !important;
    color: #e0f2fe !important;
}
[data-testid="stHeader"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    background: transparent !important;
}
[data-testid="stMainBlockContainer"],
.block-container {
    position: relative !important;
    z-index: 2 !important;
    background: transparent !important;
    font-family: 'Fredoka', 'Baloo 2', sans-serif !important;
    font-weight: 700;
    max-width: 98% !important;
    padding: 1.2rem 2rem 3.5rem 2rem !important;
}
/* Low-Opacity Ambient Background Layer: Shimmering Sea Light, Fish & Rising Bubbles */
.ocean-ambient-bg {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
    opacity: 0.26;
}
.ocean-ambient-bg svg {
    width: 100%;
    height: 100%;
    display: block;
}
@keyframes seaLightSway1 {
    0%, 100% { transform: translateX(-28px) skewX(-3deg); opacity: 0.55; }
    50% { transform: translateX(36px) skewX(3deg); opacity: 0.95; }
}
@keyframes seaLightSway2 {
    0%, 100% { transform: translateX(32px) skewX(2.5deg); opacity: 0.85; }
    50% { transform: translateX(-34px) skewX(-2.5deg); opacity: 0.45; }
}
@keyframes seaLightSway3 {
    0%, 100% { transform: translateX(-18px) skewX(-2deg); opacity: 0.45; }
    50% { transform: translateX(26px) skewX(2deg); opacity: 0.90; }
}
@keyframes bgBubbleRise1 {
    0% { transform: translate3d(0, 105vh, 0); opacity: 0; }
    12% { opacity: 0.85; }
    50% { transform: translate3d(18px, 48vh, 0); }
    88% { opacity: 0.75; }
    100% { transform: translate3d(-12px, -10vh, 0); opacity: 0; }
}
@keyframes bgBubbleRise2 {
    0% { transform: translate3d(0, 108vh, 0); opacity: 0; }
    15% { opacity: 0.80; }
    50% { transform: translate3d(-22px, 52vh, 0); }
    85% { opacity: 0.70; }
    100% { transform: translate3d(16px, -10vh, 0); opacity: 0; }
}
@keyframes bgFishRight1 {
    0% { transform: translate3d(-160px, 0px, 0); }
    50% { transform: translate3d(52vw, -22px, 0); }
    100% { transform: translate3d(112vw, 10px, 0); }
}
@keyframes bgFishLeft1 {
    0% { transform: translate3d(112vw, 0px, 0) scaleX(-1); }
    50% { transform: translate3d(48vw, 24px, 0) scaleX(-1); }
    100% { transform: translate3d(-160px, -12px, 0) scaleX(-1); }
}
@keyframes bgFishRight2 {
    0% { transform: translate3d(-140px, 0px, 0); }
    50% { transform: translate3d(50vw, 18px, 0); }
    100% { transform: translate3d(112vw, -14px, 0); }
}
@keyframes bgFishLeft2 {
    0% { transform: translate3d(112vw, 0px, 0) scaleX(-1); }
    50% { transform: translate3d(54vw, -18px, 0) scaleX(-1); }
    100% { transform: translate3d(-140px, 14px, 0) scaleX(-1); }
}
.bg-ray-1 { animation: seaLightSway1 9s ease-in-out infinite; }
.bg-ray-2 { animation: seaLightSway2 11s ease-in-out infinite; }
.bg-ray-3 { animation: seaLightSway3 8s ease-in-out infinite; }
.bg-bub-a { animation: bgBubbleRise1 11s ease-in infinite; }
.bg-bub-b { animation: bgBubbleRise2 14s ease-in infinite 2.5s; }
.bg-bub-c { animation: bgBubbleRise1 12.5s ease-in infinite 5.2s; }
.bg-bub-d { animation: bgBubbleRise2 10s ease-in infinite 1.4s; }
.bg-bub-e { animation: bgBubbleRise1 15s ease-in infinite 7.1s; }
.bg-bub-f { animation: bgBubbleRise2 11.8s ease-in infinite 3.9s; }
.bg-fish-1 { animation: bgFishRight1 28s linear infinite; will-change: transform; }
.bg-fish-2 { animation: bgFishLeft1 34s linear infinite 4s; will-change: transform; }
.bg-fish-3 { animation: bgFishRight2 24s linear infinite 10s; will-change: transform; }
.bg-fish-4 { animation: bgFishLeft2 31s linear infinite 14s; will-change: transform; }
h1, h2, h3, h4 {
    font-family: 'Titan One', 'Fredoka', cursive !important;
    color: #f0fdfa !important;
    letter-spacing: 0.03em;
    font-weight: 900 !important;
}
h1 {
    font-size: 3.05rem !important;
    line-height: 1.12 !important;
    margin-bottom: 0.4rem !important;
    background: linear-gradient(120deg, #ffffff 10%, #00f5d4 50%, #38bdf8 95%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 4px 16px rgba(0, 245, 212, 0.35));
}
h2 { font-size: 1.95rem !important; margin: 0.6rem 0 0.45rem 0 !important; color: #00f5d4 !important; text-shadow: 0 3px 14px rgba(0, 245, 212, 0.32); }
h3 { font-size: 1.42rem !important; color: #ffd166 !important; }
p, label, div, li, span { font-family: 'Fredoka', 'Baloo 2', sans-serif; line-height: 1.6; }
/* High-Opacity Content Containers & Strong Frame Borders */
.hero-banner {
    background: linear-gradient(135deg, rgba(3, 52, 86, 0.96) 0%, rgba(3, 22, 46, 0.97) 100%);
    border: 2.5px solid rgba(0, 245, 212, 0.72);
    border-radius: 24px;
    padding: 22px 28px;
    margin-bottom: 20px;
    box-shadow: 0 12px 32px rgba(0, 10, 24, 0.65);
}
.fun-pill {
    display: inline-block;
    background: rgba(0, 245, 212, 0.24);
    border: 2px solid #00f5d4;
    color: #00f5d4;
    font-family: 'Titan One', cursive;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 14px;
    border-radius: 999px;
    margin-bottom: 8px;
}
.nav-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(235px, 1fr));
    gap: 11px;
    margin: 16px 0 26px 0;
    padding: 16px;
    background: rgba(4, 24, 48, 0.96);
    border: 2.5px solid rgba(0, 245, 212, 0.65);
    border-radius: 20px;
    box-shadow: 0 10px 28px rgba(0, 10, 24, 0.58);
}
.nav-item {
    display: block;
    padding: 11px 14px;
    background: rgba(9, 44, 80, 0.98);
    border: 2px solid rgba(0, 245, 212, 0.48);
    border-radius: 14px;
    color: #f0f9ff !important;
    text-decoration: none !important;
    font-size: 0.95rem;
    font-weight: 700;
    transition: transform 0.16s ease, border-color 0.16s ease, background-color 0.16s ease;
}
.nav-item:hover { border-color: #00f5d4; background: rgba(0, 245, 212, 0.32); color: #ffffff !important; transform: translateY(-2px); }
.nav-num { color: #ffd166; font-family: 'Titan One', cursive; margin-right: 8px; }
.glossary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(275px, 1fr)); gap: 14px; margin: 14px 0 26px 0; }
.glossary-card {
    background: rgba(4, 24, 48, 0.96);
    border: 2px solid rgba(0, 245, 212, 0.58);
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 8px 22px rgba(0, 10, 24, 0.52);
}
.glossary-term { color: #38bdf8; font-size: 1.12rem; font-weight: 900; margin-bottom: 6px; font-family: 'Titan One', cursive; }
.glossary-def { color: #f1f5f9; font-size: 0.92rem; font-weight: 600; line-height: 1.55; margin: 0; }
.section-anchor { padding-top: 18px; margin-top: 30px; border-top: 2.5px solid rgba(0, 245, 212, 0.48); }
.section-tag { color: #ffd166; font-size: 0.92rem; font-weight: 900; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; font-family: 'Titan One', cursive; }
.narrative-box {
    background: rgba(4, 24, 48, 0.96);
    border: 2px solid rgba(0, 245, 212, 0.6);
    border-left: 6px solid #00f5d4;
    border-radius: 0 18px 18px 0;
    padding: 18px 22px;
    margin: 16px 0 12px 0;
    box-shadow: 0 8px 24px rgba(0, 10, 24, 0.55);
}
.narrative-box p { margin: 0 0 10px 0; font-size: 0.96rem; font-weight: 600; color: #f8fafc; }
.narrative-box p:last-child { margin-bottom: 0; }
.narrative-label { color: #38bdf8; font-weight: 900; font-family: 'Titan One', cursive; }
div[data-testid="stMetric"] {
    background: rgba(4, 24, 48, 0.96) !important;
    border: 2.5px solid rgba(0, 245, 212, 0.65) !important;
    border-radius: 18px !important;
    padding: 15px 18px !important;
    box-shadow: 0 8px 22px rgba(0, 10, 24, 0.55) !important;
}
div[data-testid="stMetricValue"] { color: #00f5d4 !important; font-size: 2.05rem !important; font-weight: 900 !important; font-family: 'Titan One', cursive !important; }
div[data-testid="stMetricLabel"] { color: #7dd3fc !important; font-size: 0.88rem !important; font-weight: 800 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
div[data-testid="stPlotlyChart"] {
    border-radius: 18px !important;
    overflow: hidden !important;
    border: 2px solid rgba(0, 245, 212, 0.45) !important;
    box-shadow: 0 8px 24px rgba(0, 10, 24, 0.55) !important;
}
.stButton > button {
    border-radius: 22px !important;
    font-family: 'Titan One', cursive !important;
    font-size: 1.02rem !important;
    letter-spacing: 0.03em !important;
    border: 2.5px solid #00f5d4 !important;
    background: linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%) !important;
    color: #021426 !important;
    box-shadow: 0 5px 18px rgba(0, 245, 212, 0.42) !important;
    transition: transform 0.16s ease !important;
}
.stButton > button:hover { transform: translateY(-2px) scale(1.02) !important; }
.badge-safe, .badge-warn, .badge-danger {
    border-radius: 10px;
    padding: 5px 11px;
    font-size: 0.84rem;
    font-weight: 700;
    display: inline-block;
    margin: 2px 0 8px 0;
}
.badge-safe { background: rgba(0, 245, 212, 0.24); border: 1.5px solid #00f5d4; color: #00f5d4; }
.badge-warn { background: rgba(255, 209, 102, 0.24); border: 1.5px solid #ffd166; color: #ffd166; }
.badge-danger { background: rgba(255, 107, 139, 0.26); border: 1.5px solid #ff6b8b; color: #ff6b8b; }
</style>
<div class="ocean-ambient-bg" aria-hidden="true">
  <svg viewBox="0 0 1440 900" preserveAspectRatio="none">
    <defs>
      <linearGradient id="bgSeaLight" x1="0" y1="0" x2="0.3" y2="1">
        <stop offset="0%" stop-color="#a5f3fc" stop-opacity="0.75"/>
        <stop offset="55%" stop-color="#38bdf8" stop-opacity="0.22"/>
        <stop offset="100%" stop-color="#023e8a" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <!-- Shimmering & Swaying Sea Light Rays -->
    <polygon class="bg-ray-1" points="120,0 320,0 480,900 190,900" fill="url(#bgSeaLight)"/>
    <polygon class="bg-ray-2" points="540,0 760,0 940,900 630,900" fill="url(#bgSeaLight)"/>
    <polygon class="bg-ray-3" points="980,0 1180,0 1360,900 1080,900" fill="url(#bgSeaLight)"/>
    <polygon class="bg-ray-1" points="360,0 440,0 560,900 410,900" fill="url(#bgSeaLight)" style="animation-delay:2.2s;"/>
    <polygon class="bg-ray-2" points="820,0 910,0 1050,900 880,900" fill="url(#bgSeaLight)" style="animation-delay:3.4s;"/>
    <!-- Swimming Fish -->
    <g class="bg-fish-1">
      <g transform="translate(0, 175)">
        <ellipse cx="34" cy="0" rx="28" ry="14" fill="#38bdf8"/>
        <polygon points="8,0 -10,-12 -6,0 -10,12" fill="#00f5d4"/>
        <path d="M 24 -12 Q 36 -20 46 -10 Z" fill="#00f5d4"/>
        <circle cx="50" cy="-3" r="2.5" fill="#e0f2fe"/>
      </g>
    </g>
    <g class="bg-fish-2">
      <g transform="translate(0, 390)">
        <ellipse cx="38" cy="0" rx="32" ry="16" fill="#00f5d4"/>
        <polygon points="8,0 -12,-14 -7,0 -12,14" fill="#ffd166"/>
        <circle cx="55" cy="-4" r="2.8" fill="#e0f2fe"/>
      </g>
    </g>
    <g class="bg-fish-3">
      <g transform="translate(0, 610)">
        <polygon points="10,0 34,-18 48,0 34,18" fill="#ffd166"/>
        <polygon points="10,0 -6,-9 -3,0 -6,9" fill="#38bdf8"/>
        <circle cx="40" cy="-3" r="2.2" fill="#e0f2fe"/>
      </g>
    </g>
    <g class="bg-fish-4">
      <g transform="translate(0, 770)">
        <ellipse cx="28" cy="0" rx="22" ry="11" fill="#7dd3fc"/>
        <polygon points="7,0 -8,-10 -5,0 -8,10" fill="#00f5d4"/>
        <circle cx="41" cy="-2.5" r="2" fill="#e0f2fe"/>
      </g>
    </g>
    <!-- Rising Air Bubbles -->
    <g fill="none" stroke="#bae6fd" stroke-width="1.6">
      <circle cx="140" cy="0" r="6" class="bg-bub-a"/>
      <circle cx="310" cy="0" r="9" class="bg-bub-b"/>
      <circle cx="520" cy="0" r="5" class="bg-bub-c"/>
      <circle cx="760" cy="0" r="8" class="bg-bub-d"/>
      <circle cx="1010" cy="0" r="6.5" class="bg-bub-e"/>
      <circle cx="1280" cy="0" r="7.5" class="bg-bub-f"/>
      <circle cx="220" cy="0" r="4.5" class="bg-bub-e"/>
      <circle cx="910" cy="0" r="5.5" class="bg-bub-a"/>
      <circle cx="1160" cy="0" r="8.5" class="bg-bub-c"/>
    </g>
  </svg>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# SHARED CHART & ANIMATED TANK HELPERS
# ------------------------------------------------------------------------------
PALETTE = {"healthy": "#00f5d4", "watch": "#ffd166", "bleached": "#ff6b8b", "dead": "#7f4f48", "cool": "#38bdf8", "neutral": "#64748b"}
AXIS_STYLE = dict(gridcolor="rgba(0, 229, 255, 0.12)", zerolinecolor="rgba(0, 229, 255, 0.20)", linecolor="rgba(0, 229, 255, 0.28)")

def make_layout(**overrides):
    base = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(4, 24, 48, 0.96)",
        plot_bgcolor="rgba(5, 22, 44, 0.97)",
        font=dict(family="Fredoka, Baloo 2, sans-serif", color="#e0f2fe", size=12),
        margin=dict(l=55, r=35, t=88, b=55),
    )
    base.update(overrides)
    return base

def section_header(anchor: str, tag: str, title: str):
    st.markdown(f'<div id="{anchor}" class="section-anchor"></div><div class="section-tag">{tag}</div><h2>{title}</h2>', unsafe_allow_html=True)

def render_explanation(context: str, description: str, conclusion: str):
    st.markdown(f'<div class="narrative-box"><p><span class="narrative-label">1. Reef Context &amp; Data:</span> {context}</p><p><span class="narrative-label">2. How to Read It:</span> {description}</p><p><span class="narrative-label">3. Key Ocean Takeaway:</span> {conclusion}</p></div>', unsafe_allow_html=True)

def add_linear_trend(fig, x_vals, y_vals, color="#ffd166", name="Linear Trend"):
    x, y = np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() >= 5:
        slope, intercept = np.polyfit(x[valid], y[valid], 1)
        x_line = np.linspace(np.nanmin(x[valid]), np.nanmax(x[valid]), 100)
        fig.add_trace(go.Scatter(x=x_line, y=slope * x_line + intercept, mode="lines", line=dict(color=color, width=2.2, dash="dash"), name=name, hoverinfo="skip"))

def simulate_reef(temp_c, ph_val, enso_freq, lanina_freq, turbidity, do_val, years=10):
    coral_cover = 65.0
    records = []
    for yr in range(1, years + 1):
        is_el_nino = (yr % enso_freq == 0)
        is_la_nina = (yr % lanina_freq == 0) and not is_el_nino
        effective_temp = temp_c + (1.35 if is_el_nino else (-0.85 if is_la_nina else 0.0))
        dhw = max(0.0, effective_temp - 28.2) * 4.6
        ph_stress = max(0.0, (8.05 - ph_val) * 65.0)
        turb_stress = max(0.0, (turbidity - 2.5) * 3.8)
        o2_stress = max(0.0, (6.0 - do_val) * 8.5)
        bleach_pct = min(100.0, max(0.0, (dhw * 8.2) + (ph_stress * 0.42) + (turb_stress * 0.35) + o2_stress))

        if bleach_pct >= 30.0:
            coral_cover = max(2.0, coral_cover - (bleach_pct - 22.0) * 0.48)
        else:
            boost = 1.6 if is_la_nina else 1.0
            if ph_val >= 8.05 and turbidity <= 2.5 and bleach_pct < 12.0:
                coral_cover = min(90.0, coral_cover + 4.2 * boost)
            elif bleach_pct < 22.0:
                coral_cover = min(90.0, coral_cover + 1.8 * boost)

        fish_idx = min(100.0, max(5.0, (coral_cover * 0.95) + (do_val * 4.2) - (turb_stress * 2.2) - (bleach_pct * 0.15)))
        event_label = "El Nino Heatwave" if is_el_nino else ("La Nina Cool Relief" if is_la_nina else "Baseline Ocean")
        records.append({"year": yr, "temp": round(effective_temp, 1), "bleaching": round(bleach_pct, 1), "cover": round(coral_cover, 1), "fish": round(fish_idx, 0), "event": event_label})
    return records

def render_reef_tank(
    height_px: int,
    tank_height_px: int,
    init_title: str,
    init_sub: str,
    init_status: str,
    init_gauge_pct: float,
    play_label: str,
    slider_max: int,
    slider_step: int,
    slider_val: int,
    disp_text: str,
    quick_label: str,
    quick_buttons: list[tuple[str, str]],
    kpi_cards: list[tuple[str, str, str]],
    custom_js_logic: str,
):
    quick_html = f'<div class="quick-row"><span class="quick-label">{quick_label}</span>' + "".join(
        f'<button class="quick-btn" onclick="{fn}">{lbl}</button>' for lbl, fn in quick_buttons
    ) + "</div>" if quick_buttons else ""

    kpi_html = '<div class="live-kpi-grid">' + "".join(
        f'<div class="live-kpi"><div class="live-kpi-lbl">{lbl}</div><div id="{kid}" class="live-kpi-val">{val}</div></div>'
        for kid, lbl, val in kpi_cards
    ) + "</div>" if kpi_cards else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  @import url("https://fonts.googleapis.com/css2?family=Titan+One&family=Fredoka:wght@600;700&display=swap");
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: "Fredoka", sans-serif; color: #e0f2fe; overflow: hidden; }}
  .ocean-wrapper {{ width: 100%; border-radius: 22px; overflow: hidden; box-shadow: 0 14px 40px rgba(0, 180, 216, 0.42); border: 3px solid rgba(0, 245, 212, 0.75); background: #020c1b; }}
  .ocean-card {{ width: 100%; height: {tank_height_px}px; position: relative; overflow: hidden; }}
  svg {{ display: block; width: 100%; height: 100%; }}
  @keyframes swayTentacles {{ 0%, 100% {{ transform: rotate(0deg); }} 50% {{ transform: rotate(4.5deg); }} }}
  @keyframes riseBubble {{ 0% {{ transform: translate3d(0, 0, 0); opacity: 0; }} 15% {{ opacity: 0.95; }} 85% {{ opacity: 0.85; }} 100% {{ transform: translate3d(18px, -430px, 0); opacity: 0; }} }}
  @keyframes riseBubble2 {{ 0% {{ transform: translate3d(0, 0, 0); opacity: 0; }} 20% {{ opacity: 0.98; }} 80% {{ opacity: 0.78; }} 100% {{ transform: translate3d(-20px, -430px, 0); opacity: 0; }} }}
  @keyframes swimClownfish {{ 0% {{ transform: translate3d(-90px, 0, 0); }} 50% {{ transform: translate3d(520px, -18px, 0); }} 100% {{ transform: translate3d(1100px, 8px, 0); }} }}
  @keyframes swimBlueTang {{ 0% {{ transform: translate3d(1100px, 0, 0) scaleX(-1); }} 50% {{ transform: translate3d(550px, 16px, 0) scaleX(-1); }} 100% {{ transform: translate3d(-90px, -10px, 0) scaleX(-1); }} }}
  @keyframes swimYellowFish {{ 0% {{ transform: translate3d(-60px, 0, 0); }} 50% {{ transform: translate3d(480px, 12px, 0); }} 100% {{ transform: translate3d(1080px, -6px, 0); }} }}
  @keyframes shimmer {{ 0%, 100% {{ opacity: 0.24; }} 50% {{ opacity: 0.44; }} }}
  .anemone-1 {{ transform-origin: 640px 430px; animation: swayTentacles 3.8s ease-in-out infinite; }}
  .b1 {{ animation: riseBubble 4.2s ease-in infinite; }}
  .b2 {{ animation: riseBubble2 5.3s ease-in infinite 1.2s; }}
  .b3 {{ animation: riseBubble 3.9s ease-in infinite 2.5s; }}
  .b4 {{ animation: riseBubble2 4.8s ease-in infinite 0.6s; }}
  .fish-1 {{ animation: swimClownfish 16s linear infinite; will-change: transform; }}
  .fish-2 {{ animation: swimBlueTang 20s linear infinite 4s; will-change: transform; }}
  .fish-3 {{ animation: swimYellowFish 14s linear infinite 8s; will-change: transform; }}
  .caustic {{ animation: shimmer 4s ease-in-out infinite; }}
  .coral-part {{ transition: fill 1.15s ease, stroke 1.15s ease; }}
  .hud {{ position: absolute; top: 16px; left: 18px; background: rgba(3, 20, 42, 0.97); border: 2.5px solid rgba(0, 245, 212, 0.78); border-radius: 16px; padding: 12px 18px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6); min-width: 340px; }}
  .hud-title {{ font-family: "Titan One", cursive; font-size: 1.3rem; color: #00f5d4; letter-spacing: 0.4px; }}
  .hud-sub {{ font-size: 0.94rem; font-weight: 700; color: #ffffff; margin-top: 2px; }}
  .hud-gauge-bar {{ width: 100%; height: 10px; background: rgba(255, 255, 255, 0.22); border-radius: 10px; margin-top: 8px; overflow: hidden; }}
  .hud-gauge-fill {{ height: 100%; background: #00f5d4; border-radius: 10px; transition: width 0.8s ease, background 0.8s ease; }}
  .hud-status {{ font-size: 0.84rem; font-weight: 700; color: #a5f3fc; margin-top: 5px; display: inline-block; }}
  .controls-bar {{ background: rgba(4, 26, 50, 0.99); padding: 14px 20px; border-top: 2.5px solid rgba(0, 245, 212, 0.58); display: flex; flex-direction: column; gap: 10px; }}
  .slider-row {{ display: flex; align-items: center; gap: 16px; }}
  .play-btn {{ background: linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%); color: #031527; font-family: "Titan One", cursive; font-size: 0.96rem; padding: 8px 20px; border-radius: 20px; border: none; cursor: pointer; box-shadow: 0 4px 14px rgba(0, 245, 212, 0.45); transition: transform 0.15s ease, background 0.2s ease; flex-shrink: 0; min-width: 175px; }}
  .play-btn:hover {{ transform: scale(1.04); }}
  .timeline-slider {{ flex-grow: 1; -webkit-appearance: none; height: 12px; border-radius: 8px; background: rgba(255, 255, 255, 0.28); outline: none; cursor: pointer; }}
  .timeline-slider::-webkit-slider-thumb {{ -webkit-appearance: none; width: 26px; height: 26px; border-radius: 50%; background: #00f5d4; border: 3px solid #ffffff; cursor: pointer; box-shadow: 0 0 12px rgba(0, 245, 212, 0.85); }}
  .year-display {{ font-family: "Titan One", cursive; font-size: 1.38rem; color: #ffd166; min-width: 72px; text-align: right; }}
  .quick-row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
  .quick-label {{ font-size: 0.86rem; font-weight: 700; color: #7dd3fc; margin-right: 4px; }}
  .quick-btn {{ background: rgba(8, 42, 78, 0.98); border: 1.5px solid rgba(0, 245, 212, 0.55); color: #e0f2fe; font-family: "Fredoka", sans-serif; font-size: 0.84rem; font-weight: 700; padding: 4px 12px; border-radius: 12px; cursor: pointer; transition: all 0.15s ease; }}
  .quick-btn:hover {{ background: rgba(0, 245, 212, 0.34); border-color: #00f5d4; color: #ffffff; transform: translateY(-1px); }}
  .live-kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 2px; }}
  .live-kpi {{ background: rgba(8, 42, 78, 0.98); border: 1.5px solid rgba(0, 245, 212, 0.52); border-radius: 12px; padding: 8px 12px; }}
  .live-kpi-lbl {{ font-size: 0.74rem; text-transform: uppercase; color: #7dd3fc; font-weight: 700; }}
  .live-kpi-val {{ font-family: "Titan One", cursive; font-size: 1.24rem; color: #00f5d4; margin-top: 2px; }}
</style></head>
<body>
<div class="ocean-wrapper">
  <div class="ocean-card">
    <svg viewBox="0 0 1000 450" preserveAspectRatio="none">
      <defs>
        <linearGradient id="oceanGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00b4d8"/><stop offset="60%" stop-color="#023e8a"/><stop offset="100%" stop-color="#010814"/></linearGradient>
        <linearGradient id="sunbeamGrad" x1="0" y1="0" x2="0.6" y2="1"><stop offset="0%" stop-color="#ffffff" stop-opacity="0.34"/><stop offset="50%" stop-color="#e0f2fe" stop-opacity="0.12"/><stop offset="100%" stop-color="#023e8a" stop-opacity="0"/></linearGradient>
        <linearGradient id="floorGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#143454"/><stop offset="100%" stop-color="#071728"/></linearGradient>
      </defs>
      <rect width="1000" height="450" fill="url(#oceanGrad)" />
      <polygon class="caustic" points="140,0 280,0 380,450 180,450" fill="url(#sunbeamGrad)" />
      <polygon class="caustic" points="420,0 560,0 700,450 500,450" fill="url(#sunbeamGrad)" style="animation-delay:1.5s;" />
      <polygon class="caustic" points="720,0 840,0 960,450 800,450" fill="url(#sunbeamGrad)" style="animation-delay:2.8s;" />
      <path d="M 0 370 Q 250 320 500 355 T 1000 345 L 1000 450 L 0 450 Z" fill="#061c33" opacity="0.98" />
      <path d="M 0 392 Q 230 362 470 387 T 1000 377 L 1000 450 L 0 450 Z" fill="url(#floorGrad)" />
      <ellipse cx="300" cy="412" rx="45" ry="15" fill="#082038" /><ellipse cx="580" cy="420" rx="70" ry="19" fill="#06182c" /><ellipse cx="850" cy="414" rx="60" ry="17" fill="#071b30" />
      <g transform="translate(290, 405) scale(0.72)"><polygon points="0,-18 5,-5 18,-4 8,5 11,18 0,10 -11,18 -8,5 -18,-4 -5,-5" fill="#ff7b00" stroke="#ffd166" stroke-width="1.5" /></g>
      <g id="staghorn">
        <path id="c-staghorn" class="coral-part" d="M 130 412 Q 135 332 120 272 Q 115 222 95 172 Q 90 152 85 142 Q 96 147 106 167 Q 128 217 135 267 Q 150 217 168 162 Q 178 122 185 102 Q 195 107 195 130 Q 190 167 174 227 Q 196 207 224 177 Q 244 157 255 147 Q 257 157 250 172 Q 228 212 196 257 Q 185 327 180 412 Z" fill="#ff1493" />
        <path id="c-staghorn-b1" class="coral-part" d="M 138 282 Q 85 247 65 212 Q 60 202 70 204 Q 85 220 132 252 Z" fill="#ff1493" />
        <path id="c-staghorn-b2" class="coral-part" d="M 174 262 Q 222 237 250 217 Q 257 212 255 220 Q 238 242 180 282 Z" fill="#ff1493" />
        <circle id="c-stip-1" class="coral-part" cx="85" cy="142" r="5" fill="#ffe600" /><circle id="c-stip-2" class="coral-part" cx="185" cy="102" r="5.5" fill="#ffe600" /><circle id="c-stip-3" class="coral-part" cx="255" cy="147" r="5" fill="#ffe600" /><circle id="c-stip-4" class="coral-part" cx="65" cy="207" r="4.5" fill="#ffe600" />
      </g>
      <g id="brain">
        <path id="c-brain" class="coral-part" d="M 280 412 C 275 352, 305 292, 365 292 C 425 292, 455 352, 450 412 Z" fill="#ffb703" />
        <path id="c-bridge-1" class="coral-part" d="M 320 397 Q 308 357 336 340 Q 364 324 352 364 Q 346 386 362 397" stroke="#fb8500" stroke-width="5" fill="none" stroke-linecap="round" />
        <path id="c-bridge-2" class="coral-part" d="M 364 397 Q 376 352 392 330 Q 414 314 404 354 Q 398 382 420 397" stroke="#fb8500" stroke-width="5" fill="none" stroke-linecap="round" />
        <path id="c-bridge-3" class="coral-part" d="M 336 324 Q 365 304 392 317" stroke="#fb8500" stroke-width="4.5" fill="none" stroke-linecap="round" />
        <path id="c-bridge-4" class="coral-part" d="M 296 392 Q 290 370 308 352" stroke="#fb8500" stroke-width="4.5" fill="none" stroke-linecap="round" />
      </g>
      <g id="tubes">
        <path id="c-tube-1" class="coral-part" d="M 470 422 L 476 347 Q 487 341 498 347 L 504 422 Z" fill="#f72585" />
        <ellipse id="c-ttip-1" class="coral-part" cx="487" cy="347" rx="11" ry="4.5" fill="#ffe600" /><ellipse cx="487" cy="347" rx="6.5" ry="2.8" fill="#030b14" />
        <path id="c-tube-2" class="coral-part" d="M 498 422 L 506 362 Q 517 357 528 362 L 535 422 Z" fill="#f72585" opacity="0.98" />
        <ellipse id="c-ttip-2" class="coral-part" cx="517" cy="362" rx="10" ry="4" fill="#ffe600" /><ellipse cx="517" cy="362" rx="6" ry="2.2" fill="#030b14" />
      </g>
      <g class="anemone-1">
        <path id="c-ane-1" class="coral-part" d="M 610 422 Q 598 362 580 307 Q 568 268 562 242 Q 571 248 580 274 Q 604 330 622 422 Z" fill="#00f5d4" />
        <path id="c-ane-2" class="coral-part" d="M 622 422 Q 628 352 634 284 Q 640 234 646 202 Q 653 212 652 244 Q 646 317 640 422 Z" fill="#00f5d4" />
        <path id="c-ane-3" class="coral-part" d="M 634 422 Q 656 357 678 302 Q 700 252 716 224 Q 719 238 700 274 Q 672 340 650 422 Z" fill="#00f5d4" />
        <path id="c-ane-4" class="coral-part" d="M 616 422 Q 588 372 554 328 Q 538 306 526 294 Q 540 300 560 322 Q 594 367 628 422 Z" fill="#00f5d4" opacity="0.95" />
        <circle id="c-ane-tip-1" class="coral-part" cx="562" cy="242" r="5.5" fill="#70e000" /><circle id="c-ane-tip-2" class="coral-part" cx="646" cy="202" r="6" fill="#70e000" /><circle id="c-ane-tip-3" class="coral-part" cx="716" cy="224" r="5.5" fill="#70e000" /><circle id="c-ane-tip-4" class="coral-part" cx="526" cy="294" r="5" fill="#70e000" />
      </g>
      <g id="plate">
        <ellipse id="c-plate-1" class="coral-part" cx="850" cy="397" rx="95" ry="20" fill="#9d4edd" /><ellipse id="c-plate-rim-1" class="coral-part" cx="850" cy="393" rx="88" ry="15" fill="#00f5d4" opacity="0.82" />
        <path d="M 830 397 L 845 342 L 868 342 L 858 397 Z" fill="#081d33" />
        <ellipse id="c-plate-2" class="coral-part" cx="840" cy="342" rx="80" ry="18" fill="#9d4edd" /><ellipse id="c-plate-rim-2" class="coral-part" cx="840" cy="338" rx="72" ry="13" fill="#00f5d4" opacity="0.88" />
        <path d="M 840 342 L 856 287 L 874 287 L 858 342 Z" fill="#081d33" />
        <ellipse id="c-plate-3" class="coral-part" cx="862" cy="287" rx="62" ry="15" fill="#9d4edd" /><ellipse id="c-plate-rim-3" class="coral-part" cx="862" cy="283" rx="54" ry="11" fill="#00f5d4" opacity="0.94" />
      </g>
      <g id="fish-group" opacity="1.0" style="transition: opacity 1.1s ease;">
        <g class="fish-1"><g transform="translate(0, 145)"><ellipse cx="32" cy="0" rx="28" ry="16" fill="#ff7700" /><path d="M 23 -15 C 21 -4 21 4 23 15 L 28 14 C 26 3 26 -3 28 -14 Z" fill="#ffffff" /><path d="M 38 -13 C 36 -3 36 3 38 13 L 42 11 C 40 2 40 -2 42 -11 Z" fill="#ffffff" /><polygon points="6,0 -10,-12 -8,0 -10,12" fill="#ff7700" /><circle cx="49" cy="-4" r="3.2" fill="#ffffff" /><circle cx="50" cy="-4" r="1.6" fill="#000000" /></g></g>
        <g class="fish-2"><g transform="translate(0, 205)"><ellipse cx="34" cy="0" rx="30" ry="18" fill="#0077b6" /><polygon points="6,0 -12,-14 -9,0 -12,14" fill="#ffd166" /><path d="M 22 -7 Q 33 -16 44 -9 Z" fill="#ffd166" /><circle cx="51" cy="-4" r="3.2" fill="#ffffff" /><circle cx="52" cy="-4" r="1.6" fill="#000000" /></g></g>
        <g class="fish-3"><g transform="translate(0, 82)"><polygon points="12,0 36,-22 48,0 36,22" fill="#ffe600" /><polygon points="12,0 -4,-10 -2,0 -4,10" fill="#ffb703" /><line x1="42" y1="-18" x2="42" y2="18" stroke="#000814" stroke-width="3" /><circle cx="45" cy="-4" r="2.8" fill="#ffffff" /><circle cx="46" cy="-4" r="1.4" fill="#000000" /></g></g>
      </g>
      <g fill="#caf0f8" opacity="0.94">
        <circle cx="170" cy="395" r="4.5" class="b1" /><circle cx="360" cy="375" r="5.5" class="b2" /><circle cx="500" cy="390" r="4" class="b3" /><circle cx="660" cy="398" r="5" class="b4" /><circle cx="860" cy="370" r="4" class="b2" />
      </g>
    </svg>
    <div class="hud">
      <div id="hud-title" class="hud-title">{init_title}</div>
      <div id="hud-sub" class="hud-sub">{init_sub}</div>
      <div class="hud-gauge-bar"><div id="hud-gauge-fill" class="hud-gauge-fill" style="width:{init_gauge_pct}%;"></div></div>
      <div id="hud-status" class="hud-status">{init_status}</div>
    </div>
  </div>
  <div class="controls-bar">
    <div class="slider-row">
      <button id="btn-play" class="play-btn" onclick="togglePlay()">{play_label}</button>
      <input id="tank-slider" type="range" class="timeline-slider" min="0" max="{slider_max}" step="{slider_step}" value="{slider_val}" oninput="onSliderDrag(this.value)">
      <div id="tank-disp" class="year-display">{disp_text}</div>
    </div>
    {quick_html}
    {kpi_html}
  </div>
</div>
<script>
  function hexToRgb(hex) {{ const h = hex.replace("#", ""); return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]; }}
  function rgbToHex(r, g, b) {{ const f = c => Math.round(c).toString(16).padStart(2, "0"); return "#" + f(r) + f(g) + f(b); }}
  function interpColor(v, hH, hB, hD) {{
    const val = Math.max(0, Math.min(100, v)), rH = hexToRgb(hH), rB = hexToRgb(hB), rD = hexToRgb(hD);
    const [a, b, t] = val <= 50 ? [rH, rB, val / 50] : [rB, rD, (val - 50) / 50];
    return rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
  }}
  function paintReefColors(v) {{
    const setFill = (ids, col) => ids.forEach(id => document.getElementById(id).setAttribute("fill", col));
    setFill(["c-staghorn", "c-staghorn-b1", "c-staghorn-b2"], interpColor(v, "#ff1493", "#f8fafc", "#443932"));
    setFill(["c-stip-1", "c-stip-2", "c-stip-3", "c-stip-4", "c-ttip-1", "c-ttip-2"], interpColor(v, "#ffe600", "#ffffff", "#2b2a26"));
    setFill(["c-brain"], interpColor(v, "#ffb703", "#f1f5f9", "#3b3a2e"));
    ["c-bridge-1", "c-bridge-2", "c-bridge-3", "c-bridge-4"].forEach(id => document.getElementById(id).setAttribute("stroke", interpColor(v, "#fb8500", "#e2e8f0", "#24251e")));
    setFill(["c-tube-1", "c-tube-2"], interpColor(v, "#f72585", "#fdfbf7", "#2a2a2a"));
    setFill(["c-ane-1", "c-ane-2", "c-ane-3", "c-ane-4"], interpColor(v, "#00f5d4", "#e2e8f0", "#2b382a"));
    setFill(["c-ane-tip-1", "c-ane-tip-2", "c-ane-tip-3", "c-ane-tip-4"], interpColor(v, "#70e000", "#ffffff", "#1e291d"));
    setFill(["c-plate-1", "c-plate-2", "c-plate-3"], interpColor(v, "#9d4edd", "#ffffff", "#323538"));
    setFill(["c-plate-rim-1", "c-plate-rim-2", "c-plate-rim-3"], interpColor(v, "#00f5d4", "#e2e8f0", "#252729"));
    document.getElementById("fish-group").style.opacity = Math.max(0.14, 1 - (v / 85));
  }}
  {custom_js_logic}
</script>
</body></html>"""
    components.html(html, height=height_px)

# ------------------------------------------------------------------------------
# LOAD DATA & HERO HEADER
# ------------------------------------------------------------------------------
df_global, df_regional, df_climate = load_all_datasets()

st.markdown("""
<div class="hero-banner">
    <div class="fun-pill">Interactive Ocean &amp; Reef Expedition (1980–2026)</div>
    <h1>Global &amp; Regional Coral Reef Bleaching Explorer</h1>
    <p style="color:#bae6fd;font-size:1.12rem;margin:4px 0 0 0;font-weight:700;">
        Dive beneath the waves to explore how ocean heatwaves, El Niño &amp; La Niña cycles, and seawater chemistry shape coral reefs—then take the controls in our live Reef Simulator!
    </p>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Global Reef Surveys", f"{len(df_global):,}" if df_global is not None else "Missing", "1980–2020 Global Archive")
m2.metric("Regional Sensor Records", f"{len(df_regional):,}" if df_regional is not None else "Missing", "2000–2026 High-Res Sensors")
m3.metric("Ocean Climate Logs", f"{len(df_climate):,}" if df_climate is not None else "Missing", "2015–2023 SST & pH Logs")
m4.metric("Countries Monitored", f"{df_global['Country_Name'].nunique()}" if df_global is not None else "Missing", "Across 5 Tropical Basins")

nav_items = [
    ("#glossary", "00", "Reef Decoder & Key Metrics"),
    ("#sec-1", "01", "Yearly Decline & El Niño Pulses"),
    ("#sec-2", "02", "Heat Dose: DHW & Hotspots"),
    ("#sec-3", "03", "SST vs. Ocean pH Density"),
    ("#sec-4", "04", "Global Hotspot Circular Globe"),
    ("#sec-5", "05", "Depth, Waves & Peak Months"),
    ("#sec-6", "06", "Top Bleaching Stressors"),
    ("#sec-7", "07", "Heatwave Ecosystem Pathways"),
    ("#sec-8", "08", "Animated Underwater Reef"),
    ("#sec-9", "09", "Play with the Coral Reef!"),
]
st.markdown('<div class="nav-bar">' + "".join(f'<a class="nav-item" href="{h}"><span class="nav-num">{n}</span>{t}</a>' for h, n, t in nav_items) + '</div>', unsafe_allow_html=True)

# 00. GLOSSARY
section_header("glossary", "Reef Field Guide", "00. Key Scientific Terms and Metrics")
st.markdown("<p style='color:#bae6fd;font-size:0.95rem;'>Quick decoder for the oceanographic vitals tracked across our reef charts and simulator.</p>", unsafe_allow_html=True)
glossary_items = [
    ("SST / SSC (Sea Surface Temperature)", "Surface ocean warmth in °C. Tropical corals thrive around 23–28.5 °C; just 1–2 °C above summer highs triggers thermal alarm."),
    ("SSTA (Temperature Anomaly)", "How many degrees (°C) warmer or cooler the water is compared to its historical long-term average for that exact spot and month."),
    ("Hotspot (Bleaching Hotspot)", "Extra heat (°C) stacked above a reef's hottest normal summer month. Anything above +1.0 °C puts corals in immediate danger."),
    ("DHW (Degree Heating Weeks)", "Accumulated heat stress over 12 weeks (°C-weeks). At 4 °C-weeks corals bleach; above 8 °C-weeks widespread mortality begins."),
    ("ENSO: El Niño & La Niña (ONI)", "Pacific climate swings tracked by ONI. <b>El Niño</b> (ONI &gt; +0.5 °C) fuels mass bleaching; <b>La Niña</b> (ONI &lt; -0.5 °C) brings cooling relief."),
    ("Ocean pH, Dissolved O2 & Turbidity", "<b>pH</b> tracks acidity (lower pH weakens skeletons); <b>Dissolved O2</b> fuels respiration; <b>Turbidity (NTU)</b> measures cloudy runoff blocking sunlight."),
]
st.markdown('<div class="glossary-grid">' + "".join(f'<div class="glossary-card"><div class="glossary-term">{t}</div><p class="glossary-def">{d}</p></div>' for t, d in glossary_items) + '</div>', unsafe_allow_html=True)

# 01. YEARLY DECLINE & EL NINO
section_header("sec-1", "Chart 01 — Ocean Fever Timeline", "01. Years of Severe Coral Reef Degradation and the El Niño Connection")
view_choice = st.radio("Select timeline source:", ["Global Reef Record (1980–2020, n = 34,515)", "Regional Sensor Record with Explicit ONI & ENSO Labels (2000–2026, n = 2,000)"], horizontal=True, key="sec1_source")

if view_choice.startswith("Global") and df_global is not None:
    yearly = df_global.dropna(subset=["Date_Year", "Percent_Bleaching"]).groupby("Date_Year").agg(
        mean_bleach=("Percent_Bleaching", "mean"), severe_share=("Percent_Bleaching", lambda s: (s >= 30).mean() * 100),
        mean_ssta=("SSTA", "mean"), records=("Percent_Bleaching", "size")
    ).reset_index()
    yearly = yearly[(yearly["Date_Year"].between(1980, 2030)) & (yearly["records"] >= 15)].copy()
    yearly["ENSO_State"] = yearly["mean_ssta"].apply(lambda v: "El Niño Warming" if pd.notna(v) and v >= 0.45 else ("La Niña Cooling" if pd.notna(v) and v <= -0.35 else "Neutral"))
    enso_bg = {"El Niño Warming": PALETTE["bleached"], "La Niña Cooling": PALETTE["cool"], "Neutral": PALETTE["neutral"]}

    fig1 = go.Figure()
    for _, row in yearly.iterrows():
        fig1.add_vrect(x0=row["Date_Year"] - 0.5, x1=row["Date_Year"] + 0.5, fillcolor=enso_bg[row["ENSO_State"]], opacity=0.14, line_width=0, layer="below")
    fig1.add_trace(go.Bar(x=yearly["Date_Year"], y=yearly["severe_share"], name="Severe Reefs (≥30%)", marker_color="rgba(255, 107, 139, 0.36)", hovertemplate="<b>%{x}</b><br>Severely bleached sites: %{y:.1f}%<extra></extra>"))
    fig1.add_trace(go.Scatter(x=yearly["Date_Year"], y=yearly["mean_bleach"], mode="lines+markers", name="Mean Bleaching (%)", line=dict(color="#f0fdfa", width=2.6), marker=dict(size=7, color=[enso_bg[e] for e in yearly["ENSO_State"]], line=dict(color="#020c1b", width=1)), customdata=np.stack([yearly["records"], yearly["ENSO_State"]], axis=-1), hovertemplate="<b>Year %{x}</b><br>Mean Bleaching: %{y:.1f}%<br>Regime: %{customdata[1]}<br>Surveys: %{customdata[0]}<extra></extra>"))
    fig1.add_trace(go.Scatter(x=yearly["Date_Year"], y=yearly["mean_ssta"], mode="lines", name="Mean SSTA (°C)", line=dict(color="#ffd166", width=2, dash="dot"), yaxis="y2", hovertemplate="<b>Year %{x}</b><br>Mean SSTA: %{y:+.2f} °C<extra></extra>"))
    for label, color in enso_bg.items():
        fig1.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=color, symbol="square"), name=label))
    for _, row in yearly[yearly["Date_Year"].isin([1998, 2002, 2005, 2010, 2016])].iterrows():
        fig1.add_annotation(x=row["Date_Year"], y=row["mean_bleach"], text=f"{int(row['Date_Year'])} ({row['mean_bleach']:.1f}%)", showarrow=True, arrowhead=0, arrowcolor="#ffd166", ay=-24, font=dict(color="#f0fdfa", size=11))

    fig1.update_layout(**make_layout(height=490, margin=dict(l=55, r=55, t=95, b=50), xaxis=dict(title="Survey Year", dtick=4, **AXIS_STYLE), yaxis=dict(title="Bleaching & Severe Share (%)", range=[0, 80], **AXIS_STYLE), yaxis2=dict(title="Mean SSTA (°C)", overlaying="y", side="right", showgrid=False, color="#ffd166", range=[-0.6, 1.3]), legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0.5, xanchor="center", font=dict(size=11))))
    st.plotly_chart(fig1, use_container_width=True)

    top_years = yearly.nlargest(6, "mean_bleach")[["Date_Year", "mean_bleach", "severe_share", "mean_ssta", "ENSO_State", "records"]].round({"mean_bleach": 1, "severe_share": 1, "mean_ssta": 2})
    top_years.columns = ["Year", "Mean Bleaching (%)", "Severely Bleached Sites (%)", "Mean SSTA (°C)", "ENSO Regime", "Survey Count"]
    top_years["Year"] = top_years["Year"].astype(int)
    st.dataframe(top_years, use_container_width=True, hide_index=True)

    render_explanation(
        context="Coral reefs suffer acute bleaching pulses during global ocean heatwaves rather than steady annual decline, tracked here across dated surveys.",
        description="The white curve tracks annual mean bleaching severity (%), pink bars show severely bleached reefs (≥30%), the dashed gold line plots temperature anomalies (SSTA), and background bands highlight El Niño vs. La Niña years.",
        conclusion=f"Temperature anomalies correlate strongly with bleaching spikes (r = {yearly['mean_bleach'].corr(yearly['mean_ssta']):.2f}), led by the 1998 Super El Niño (43.1% mean bleaching), 2005 (25.3%), 2002 (17.2%), and 2016 (15.2%)."
    )
elif df_regional is not None:
    reg_yearly = df_regional.groupby("Year").agg(mean_bleach=("Bleaching_Percent", "mean"), mean_oni=("ONI_Index", "mean"), dominant_enso=("ENSO_Phase", lambda s: s.mode().iat[0])).reset_index()
    enso_colors = {"El Nino": PALETTE["bleached"], "La Nina": PALETTE["cool"], "Neutral": PALETTE["neutral"]}
    fig1_reg = go.Figure()
    for _, row in reg_yearly.iterrows():
        fig1_reg.add_vrect(x0=row["Year"] - 0.5, x1=row["Year"] + 0.5, fillcolor=enso_colors.get(row["dominant_enso"], PALETTE["neutral"]), opacity=0.15, line_width=0, layer="below")
    fig1_reg.add_trace(go.Scatter(x=reg_yearly["Year"], y=reg_yearly["mean_bleach"], mode="lines+markers", name="Mean Bleaching (%)", line=dict(color="#f0fdfa", width=2.6), marker=dict(size=8, color=[enso_colors.get(e, PALETTE["neutral"]) for e in reg_yearly["dominant_enso"]])))
    fig1_reg.add_trace(go.Scatter(x=reg_yearly["Year"], y=reg_yearly["mean_oni"], mode="lines", name="Oceanic Niño Index (ONI)", line=dict(color="#ffd166", width=2, dash="dot"), yaxis="y2"))
    fig1_reg.update_layout(**make_layout(height=460, margin=dict(l=55, r=55, t=88, b=50), xaxis=dict(title="Year", dtick=2, **AXIS_STYLE), yaxis=dict(title="Mean Bleaching (%)", **AXIS_STYLE), yaxis2=dict(title="ONI Index (°C)", overlaying="y", side="right", showgrid=False, color="#ffd166"), legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0.5, xanchor="center")))
    st.plotly_chart(fig1_reg, use_container_width=True)
    render_explanation(
        context="Regional Indian Ocean sensor records with explicit ONI and ENSO phase labels.",
        description="Annual mean bleaching (%) is plotted alongside the Oceanic Niño Index (dashed gold) with ENSO background shading.",
        conclusion=f"Regional bleaching closely follows ONI cycles (r = {reg_yearly['mean_bleach'].corr(reg_yearly['mean_oni']):.2f}), surging during the 2016 El Niño (52.7% mean bleaching) before cooling in La Niña periods."
    )

# 02. THERMAL DOSE-RESPONSE
section_header("sec-2", "Chart 02 — Thermal Dose-Response", "02. Cumulative Heat Stress (DHW) and Hotspot Thresholds")
if df_regional is not None:
    col2a, col2b = st.columns([1.45, 1])
    state_labels = {"healthy": "Healthy", "watch": "Thermal Watch", "bleached": "Bleached", "severe_bleach": "Severe Bleaching"}
    state_colors = {"Healthy": PALETTE["healthy"], "Thermal Watch": PALETTE["watch"], "Bleached": PALETTE["bleached"], "Severe Bleaching": PALETTE["dead"]}
    sub_reg = df_regional.dropna(subset=["DHW_Stress", "Bleaching_Percent", "Damage_State"]).copy()
    sub_reg["State_Label"] = sub_reg["Damage_State"].map(state_labels).fillna(sub_reg["Damage_State"])

    with col2a:
        fig2_scatter = px.scatter(sub_reg, x="DHW_Stress", y="Bleaching_Percent", color="State_Label", color_discrete_map=state_colors, hover_data={"Site_Name": True, "Hotspot": ":.2f", "Temperature_Celsius": ":.1f", "ENSO_Phase": True}, opacity=0.8)
        add_linear_trend(fig2_scatter, sub_reg["DHW_Stress"], sub_reg["Bleaching_Percent"], color="#f0fdfa")
        fig2_scatter.add_vline(x=4.0, line_dash="dot", line_color="#ffd166", annotation_text="4 °C-wks: Warning", annotation_position="top left", annotation_font=dict(color="#ffd166", size=11))
        fig2_scatter.add_vline(x=8.0, line_dash="dot", line_color="#ff6b8b", annotation_text="8 °C-wks: Mortality", annotation_position="top right", annotation_font=dict(color="#ff6b8b", size=11))
        fig2_scatter.update_layout(**make_layout(height=450, margin=dict(l=55, r=25, t=95, b=50), xaxis=dict(title="Degree Heating Weeks (DHW, °C-weeks)", **AXIS_STYLE), yaxis=dict(title="Coral Bleaching (%)", range=[-4, 108], **AXIS_STYLE), legend=dict(title=None, orientation="h", y=1.03, yanchor="bottom", x=0.5, xanchor="center", font=dict(size=11))))
        st.plotly_chart(fig2_scatter, use_container_width=True)

    with col2b:
        agg_state = sub_reg.groupby("Damage_State").agg(mean_bleach=("Bleaching_Percent", "mean"), mean_dhw=("DHW_Stress", "mean"), mean_hotspot=("Hotspot", "mean"), count=("Bleaching_Percent", "size")).reindex(["healthy", "watch", "bleached", "severe_bleach"]).reset_index()
        agg_state["Label"] = agg_state["Damage_State"].map(state_labels)
        fig2_bar = go.Figure(go.Bar(x=agg_state["Label"], y=agg_state["mean_bleach"], marker_color=[state_colors[l] for l in agg_state["Label"]], text=agg_state["mean_bleach"].round(1).astype(str) + "%", textposition="outside", customdata=np.stack([agg_state["mean_dhw"], agg_state["mean_hotspot"], agg_state["count"]], axis=-1), hovertemplate="<b>%{x}</b><br>Mean Bleaching: %{y:.1f}%<br>Mean DHW: %{customdata[0]:.2f} °C-wks<br>Mean Hotspot: %{customdata[1]:+.2f} °C<br>Observations: %{customdata[2]}<extra></extra>"))
        fig2_bar.update_layout(**make_layout(height=450, margin=dict(l=50, r=25, t=95, b=50), title=dict(text="Average Severity by Damage State", y=0.95, font=dict(size=14)), xaxis=dict(title="Reef Damage State", **AXIS_STYLE), yaxis=dict(title="Mean Bleaching (%)", range=[0, 105], **AXIS_STYLE), showlegend=False))
        st.plotly_chart(fig2_bar, use_container_width=True)

    render_explanation(
        context="NOAA Coral Reef Watch uses Degree Heating Weeks (DHW) to track accumulated heat: 4 °C-weeks triggers bleaching warnings and 8 °C-weeks triggers mass mortality.",
        description="Left: Cumulative DHW vs. Bleaching % across sensor observations with NOAA warning thresholds. Right: Mean bleaching percentage for each field damage state.",
        conclusion=f"Cumulative DHW is the #1 driver of bleaching intensity (r = {sub_reg['DHW_Stress'].corr(sub_reg['Bleaching_Percent']):.2f}): Healthy reefs average 0.51 °C-weeks (3.0% bleaching), while Severe Bleaching sites average 4.66 °C-weeks (84.4% bleaching)."
    )

# 03. SST VS PH DENSITY
section_header("sec-3", "Chart 03 — Heat + Acidification Double Trouble", "03. Sea Surface Temperature (SST) vs. Seawater pH Density Distribution")
if df_climate is not None:
    fig3_contour = go.Figure()
    fig3_contour.add_trace(go.Histogram2dContour(
        x=df_climate["SST (°C)"], y=df_climate["pH Level"], ncontours=15,
        colorscale=[[0.0, "#051930"], [0.18, "#0b3154"], [0.40, "#155585"], [0.65, "#2880b8"], [0.85, "#59b5e8"], [1.0, "#a8e6ff"]],
        contours=dict(coloring="fill", showlines=True), line=dict(color="rgba(168, 230, 255, 0.35)", width=1),
        colorbar=dict(title="Density", thickness=12), hovertemplate="SST: %{x:.1f} °C<br>Seawater pH: %{y:.3f}<br>Density Count: %{z}<extra></extra>"
    ))
    for subset, name, marker_cfg, tag in [
        (df_climate[~df_climate["Marine Heatwave"]], f"Normal Conditions (n = {(~df_climate['Marine Heatwave']).sum()})", dict(size=5, color="rgba(240, 253, 250, 0.45)"), "Normal"),
        (df_climate[df_climate["Marine Heatwave"]], f"Marine Heatwave (n = {df_climate['Marine Heatwave'].sum()})", dict(size=7.5, color="#ff6b8b", line=dict(color="#020c1b", width=0.8)), "Marine Heatwave"),
    ]:
        fig3_contour.add_trace(go.Scatter(x=subset["SST (°C)"], y=subset["pH Level"], mode="markers", name=name, marker=marker_cfg, customdata=np.stack([subset["Location"], subset["Severity_Clean"], subset["Species Observed"]], axis=-1), hovertemplate=f"<b>%{{customdata[0]}}</b> ({tag})<br>SST: %{{x:.2f}} °C | pH: %{{y:.3f}}<br>Bleaching: %{{customdata[1]}} | Species: %{{customdata[2]}}<extra></extra>"))

    add_linear_trend(fig3_contour, df_climate["SST (°C)"], df_climate["pH Level"], color="#ffd166", name="Thermal-pH Trend")
    fig3_contour.update_layout(**make_layout(height=480, margin=dict(l=55, r=35, t=88, b=50), xaxis=dict(title="Sea Surface Temperature — SST (°C)", range=[23.0, 34.0], dtick=1, **AXIS_STYLE), yaxis=dict(title="Seawater pH Level", range=[7.85, 8.20], dtick=0.05, **AXIS_STYLE), legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0.5, xanchor="center", font=dict(size=11))))
    st.plotly_chart(fig3_contour, use_container_width=True)

    render_explanation(
        context="Warming oceans both overheat corals and absorb excess CO2, lowering seawater pH across reef climate observations.",
        description="2D density contours map Sea Surface Temperature against seawater pH, overlaid with individual reef surveys (pink points = Marine Heatwaves).",
        conclusion=f"SST and seawater pH move inversely (r = {df_climate['SST (°C)'].corr(df_climate['pH Level']):.2f}): Marine Heatwave events cluster in the hot, acidic lower-right zone (SST ≥ 30 °C, pH ~7.95–8.02)."
    )

# 04. GLOBAL HOTSPOT CIRCULAR GLOBE
section_header("sec-4", "Chart 04 — Global Hotspot Circular Globe", "04. Global Geography of Coral Bleaching Hotspots")
if df_global is not None:
    ctrl4_1, ctrl4_2 = st.columns([1.2, 1])
    with ctrl4_1:
        geo_level = st.radio("Map and ranking aggregation level:", ["Marine Ecoregion (n >= 10 surveys)", "Ocean Basin", "Individual Reef Sites (n >= 5 surveys)"], horizontal=True, key="sec4_geo")
    with ctrl4_2:
        globe_view = st.selectbox("Rotate Globe Focus (or drag globe directly):", [
            "Coral Triangle & Indo-Pacific (125°E)",
            "Indian Ocean & East Africa (65°E)",
            "Caribbean & Western Atlantic (75°W)",
            "Central & Eastern Pacific (145°W)",
        ], key="sec4_globe_rot")

    rot_coords = {
        "Coral Triangle & Indo-Pacific (125°E)": dict(lon=125, lat=-5),
        "Indian Ocean & East Africa (65°E)": dict(lon=65, lat=-8),
        "Caribbean & Western Atlantic (75°W)": dict(lon=-75, lat=12),
        "Central & Eastern Pacific (145°W)": dict(lon=-145, lat=-5),
    }[globe_view]

    group_col, min_n, bar_chart_title = {
        "Marine Ecoregion (n >= 10 surveys)": ("Ecoregion_Name", 10, "Top 10 Marine Ecoregions (n ≥ 10)"),
        "Ocean Basin": ("Ocean_Name", 1, "Mean Bleaching by Ocean Basin"),
        "Individual Reef Sites (n >= 5 surveys)": ("Site_Name", 5, "Top 10 Individual Reef Sites (n ≥ 5)"),
    }[geo_level]

    geo_df = df_global.dropna(subset=["Latitude_Degrees", "Longitude_Degrees", "Percent_Bleaching", group_col]).loc[lambda d: d[group_col].astype(str).str.lower() != "nd"].groupby(group_col).agg(
        lat=("Latitude_Degrees", "mean"), lon=("Longitude_Degrees", "mean"), mean_bleach=("Percent_Bleaching", "mean"),
        surveys=("Percent_Bleaching", "size"), country=("Country_Name", lambda s: s.mode().iat[0] if len(s.mode()) else "")
    ).reset_index()
    geo_df = geo_df[geo_df["surveys"] >= min_n].copy()

    col4a, col4b = st.columns([1.75, 1])
    with col4a:
        fig4_map = px.scatter_geo(
            geo_df,
            lat="lat",
            lon="lon",
            size="surveys",
            color="mean_bleach",
            color_continuous_scale=[
                [0.0, "#00f5d4"],
                [0.28, "#38bdf8"],
                [0.52, "#ffd166"],
                [0.76, "#ff7b00"],
                [1.0, "#ff3b6b"],
            ],
            hover_name=group_col,
            hover_data={"country": True, "mean_bleach": ":.1f", "surveys": True, "lat": False, "lon": False},
            size_max=34,
        )
        fig4_map.update_traces(marker=dict(line=dict(color="rgba(255,255,255,0.8)", width=1.1), opacity=0.95))
        fig4_map.update_geos(
            projection_type="orthographic",
            projection_rotation=rot_coords,
            showocean=True,
            oceancolor="#0b5588",
            showland=True,
            landcolor="#187a66",
            showcountries=True,
            countrycolor="rgba(167, 243, 208, 0.42)",
            coastlinecolor="#7dd3fc",
            coastlinewidth=1.2,
            lataxis=dict(showgrid=True, gridcolor="rgba(125, 211, 252, 0.18)"),
            lonaxis=dict(showgrid=True, gridcolor="rgba(125, 211, 252, 0.18)"),
            showframe=True,
            framecolor="#00f5d4",
            framewidth=2.5,
            bgcolor="rgba(0, 0, 0, 0)",
        )
        fig4_map.update_layout(**make_layout(
            height=620,
            margin=dict(l=15, r=15, t=60, b=20),
            title=dict(text="Interactive 3D Circular Reef Globe (Drag to Spin!)", y=0.97, font=dict(size=16, color="#00f5d4")),
            coloraxis_colorbar=dict(title="Bleach %", thickness=14, len=0.72),
            hoverlabel=dict(bgcolor="rgba(3, 20, 42, 0.98)", bordercolor="#00f5d4", font=dict(size=12, color="#f0fdfa")),
        ))
        st.plotly_chart(fig4_map, use_container_width=True)

    with col4b:
        top_ranked = geo_df.nlargest(10, "mean_bleach").sort_values("mean_bleach", ascending=True).copy()
        top_ranked["Short_Name"] = top_ranked[group_col].astype(str).str.slice(0, 26)
        max_x = float(top_ranked["mean_bleach"].max()) * 1.25 if len(top_ranked) > 0 else 80.0
        fig4_bar = go.Figure(go.Bar(x=top_ranked["mean_bleach"], y=top_ranked["Short_Name"], orientation="h", marker=dict(color=top_ranked["mean_bleach"], colorscale=[[0, PALETTE["watch"]], [1, PALETTE["bleached"]]]), text=top_ranked["mean_bleach"].round(1).astype(str) + "%", textposition="outside", cliponaxis=False, customdata=np.stack([top_ranked[group_col], top_ranked["surveys"]], axis=-1), hovertemplate="<b>%{customdata[0]}</b><br>Mean Bleaching: %{x:.1f}%<br>Surveys: %{customdata[1]:,}<extra></extra>"))
        fig4_bar.update_layout(**make_layout(height=620, margin=dict(l=10, r=35, t=60, b=50), title=dict(text=bar_chart_title, y=0.97, font=dict(size=15)), xaxis=dict(title="Mean Bleaching (%)", range=[0, max_x], **AXIS_STYLE), yaxis=dict(title="", automargin=True, **AXIS_STYLE)))
        st.plotly_chart(fig4_bar, use_container_width=True)

    top_entity_name = top_ranked.iloc[-1][group_col] if len(top_ranked) > 0 else "N/A"
    top_entity_val = top_ranked.iloc[-1]["mean_bleach"] if len(top_ranked) > 0 else 0.0
    render_explanation(
        context="Tropical reefs span 30°N to 30°S, but local currents and basin shapes create dramatic differences in bleaching severity.",
        description="Left: Full uncropped circular 3D globe sized by survey count and colored from mint (healthy) to gold and coral-pink (severe bleaching)—drag anywhere on the sphere to rotate it! Right: Top-10 leaderboard.",
        conclusion=f"In the selected view ({geo_level}), {top_entity_name} leads with {top_entity_val:.1f}% mean bleaching."
    )

# 05. DEPTH, WAVES & SEASONALITY
section_header("sec-5", "Chart 05 — Reef Shelter & Seasonality", "05. How Water Depth, Wave Exposure, and Season Shape Bleaching Risk")
if df_global is not None:
    col5a, col5b, col5c = st.columns(3)

    with col5a:
        dep_df = df_global.dropna(subset=["Depth_m", "Percent_Bleaching"]).query("0 < Depth_m <= 35").copy()
        dep_df["Depth_Band"] = pd.cut(dep_df["Depth_m"], bins=[0, 3, 6, 10, 15, 25, 35], labels=["0–3m", "3–6m", "6–10m", "10–15m", "15–25m", "25–35m"])
        dep_agg = dep_df.groupby("Depth_Band", observed=False).agg(mean_bleach=("Percent_Bleaching", "mean"), n=("Percent_Bleaching", "size")).reset_index()
        fig5_dep = go.Figure(go.Bar(x=dep_agg["Depth_Band"].astype(str), y=dep_agg["mean_bleach"], marker_color=PALETTE["cool"], text=dep_agg["mean_bleach"].round(1).astype(str) + "%", textposition="outside", customdata=dep_agg["n"], hovertemplate="<b>Depth %{x}</b><br>Mean Bleaching: %{y:.1f}%<br>Surveys: %{customdata:,}<extra></extra>"))
        fig5_dep.update_layout(**make_layout(height=380, margin=dict(l=45, r=15, t=55, b=50), title=dict(text="Bleaching by Water Depth", y=0.95, font=dict(size=13)), xaxis=dict(title="Depth Band (m)", **AXIS_STYLE), yaxis=dict(title="Mean Bleaching (%)", range=[0, 20], **AXIS_STYLE)))
        st.plotly_chart(fig5_dep, use_container_width=True)

    with col5b:
        exp_agg = df_global[df_global["Exposure"].isin(["Exposed", "Sheltered", "Sometimes"])].dropna(subset=["Percent_Bleaching"]).groupby("Exposure").agg(mean_bleach=("Percent_Bleaching", "mean"), n=("Percent_Bleaching", "size")).reindex(["Exposed", "Sometimes", "Sheltered"]).reset_index()
        fig5_exp = go.Figure(go.Bar(x=exp_agg["Exposure"], y=exp_agg["mean_bleach"], marker_color=[PALETTE["bleached"], PALETTE["watch"], PALETTE["healthy"]], text=exp_agg["mean_bleach"].round(1).astype(str) + "%", textposition="outside", customdata=exp_agg["n"], hovertemplate="<b>%{x} Reefs</b><br>Mean Bleaching: %{y:.1f}%<br>Surveys: %{customdata:,}<extra></extra>"))
        fig5_exp.update_layout(**make_layout(height=380, margin=dict(l=45, r=15, t=55, b=50), title=dict(text="Bleaching by Wave Exposure", y=0.95, font=dict(size=13)), xaxis=dict(title="Exposure Level", **AXIS_STYLE), yaxis=dict(title="Mean Bleaching (%)", range=[0, 16], **AXIS_STYLE)))
        st.plotly_chart(fig5_exp, use_container_width=True)

    with col5c:
        mo_agg = df_global.dropna(subset=["Date_Month", "Percent_Bleaching"]).query("1 <= Date_Month <= 12").groupby("Date_Month").agg(mean_bleach=("Percent_Bleaching", "mean"), n=("Percent_Bleaching", "size")).reset_index()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        mo_agg["Month"] = mo_agg["Date_Month"].astype(int).apply(lambda m: month_names[m - 1])
        fig5_mo = go.Figure(go.Scatter(x=mo_agg["Month"], y=mo_agg["mean_bleach"], mode="lines+markers", line=dict(color=PALETTE["watch"], width=2.5), marker=dict(size=7, color=PALETTE["bleached"]), customdata=mo_agg["n"], hovertemplate="<b>%{x}</b><br>Mean Bleaching: %{y:.1f}%<br>Surveys: %{customdata:,}<extra></extra>"))
        fig5_mo.update_layout(**make_layout(height=380, margin=dict(l=45, r=15, t=55, b=50), title=dict(text="Seasonal Cycle by Month", y=0.95, font=dict(size=13)), xaxis=dict(title="Month", **AXIS_STYLE), yaxis=dict(title="Mean Bleaching (%)", range=[0, float(mo_agg["mean_bleach"].max()) * 1.25], **AXIS_STYLE)))
        st.plotly_chart(fig5_mo, use_container_width=True)

    render_explanation(
        context="Micro-habitat structure—depth, wave exposure, and seasonal sunlight—determines why neighboring reefs survive or bleach differently.",
        description="Mean bleaching across six water depth bands (left), wave/sun exposure categories (center), and calendar months (right).",
        conclusion="Shallow reefs (0–3 m) bleach worst (14.4% mean) while deeper reefs (15–35 m) act as cool refugia; exposed reefs bleach more than sheltered ones (11.5% vs. 9.0%)."
    )

# 06. STRESSOR CORRELATIONS
section_header("sec-6", "Chart 06 — Stressor Rankings", "06. Which Environmental Factors Correlate Most Strongly with Bleaching?")
if df_regional is not None and df_global is not None:
    col6a, col6b = st.columns(2)
    reg_features = {"DHW_Stress": "Cumulative Heat (DHW)", "ONI_Index": "El Niño Index (ONI)", "Temperature_Celsius": "Water Temp (°C)", "NDVI": "Algal Index (NDVI)", "Salinity": "Salinity (PSU)", "Nitrate": "Nitrate Level", "Chlorophyll_A_mg_m3": "Chlorophyll-a", "Turbidity_NTU": "Turbidity (NTU)", "pH": "Seawater pH", "Distance_to_Shore_km": "Shore Distance (km)", "Dissolved_O2": "Dissolved O2 (mg/L)"}
    glob_features = {"SSTA_DHW": "Cumulative Heat (DHW)", "Temperature_Maximum": "Max Temp (K)", "SSTA": "Temp Anomaly (SSTA)", "Temperature_Mean": "Mean Temp (K)", "Turbidity": "Water Turbidity", "Distance_to_Shore": "Shore Distance (m)", "Cyclone_Frequency": "Cyclone Frequency", "Windspeed": "Wind Speed (m/s)", "Depth_m": "Reef Depth (m)"}

    for col_box, src_df, target_col, feat_map, title_txt, x_rng in [
        (col6a, df_regional, "Bleaching_Percent", reg_features, "Regional Sensor Drivers", [-0.22, 0.44]),
        (col6b, df_global, "Percent_Bleaching", glob_features, "Global Physical Drivers", [-0.22, 0.36]),
    ]:
        with col_box:
            corr_df = pd.DataFrame([{"Variable": lbl, "Correlation (r)": src_df[target_col].corr(src_df[c])} for c, lbl in feat_map.items() if c in src_df.columns]).dropna().sort_values("Correlation (r)", ascending=True)
            fig6 = go.Figure(go.Bar(x=corr_df["Correlation (r)"], y=corr_df["Variable"], orientation="h", marker_color=[PALETTE["bleached"] if v > 0 else PALETTE["cool"] for v in corr_df["Correlation (r)"]], text=corr_df["Correlation (r)"].apply(lambda v: f"{v:+.2f}"), textposition="outside", cliponaxis=False, hovertemplate="<b>%{y}</b><br>Pearson r: %{x:+.3f}<extra></extra>"))
            fig6.add_vline(x=0, line_color="rgba(255,255,255,0.28)", line_width=1)
            fig6.update_layout(**make_layout(height=430, margin=dict(l=10, r=35, t=55, b=50), title=dict(text=title_txt, y=0.96, font=dict(size=14)), xaxis=dict(title="Correlation (r) with Bleaching %", range=x_rng, **AXIS_STYLE), yaxis=dict(title="", automargin=True, **AXIS_STYLE)))
            st.plotly_chart(fig6, use_container_width=True)

    render_explanation(
        context="Direct Pearson correlation rankings compare every chemical and physical driver against bleaching severity across both regional and global datasets.",
        description="Pink bars increase bleaching risk; sky-blue bars act as protective buffers.",
        conclusion="Cumulative heat stress (DHW) ranks #1 in both datasets (r = +0.33 regionally; r = +0.25 globally), while higher Dissolved Oxygen, higher pH, and deeper water protect corals."
    )

# 07. PARALLEL COORDINATES
section_header("sec-7", "Chart 07 — Ecosystem Domino Effect", "07. Parallel Coordinates: How Marine Heatwaves Reduce pH and Reef Biodiversity")
if df_climate is not None:
    st.markdown("<p style='color:#bae6fd;font-size:0.94rem;margin-bottom:8px;'>Each line traces one reef survey. <b>Blue lines</b> = normal ocean; <b>pink-orange lines</b> = Marine Heatwave events. Drag vertically on any axis to filter!</p>", unsafe_allow_html=True)
    fig7_par = go.Figure(data=go.Parcoords(
        line=dict(color=df_climate["Heatwave_Num"], colorscale=[[0.0, "#38bdf8"], [1.0, "#ff6b8b"]], showscale=True, cmin=0, cmax=1, colorbar=dict(title="Regime", tickvals=[0, 1], ticktext=["Normal", "Heatwave"], thickness=14)),
        dimensions=[
            dict(range=[175, 50], label="Species Observed", values=df_climate["Species Observed"]),
            dict(range=[33.5, 23.5], label="SST (°C)", values=df_climate["SST (°C)"]),
            dict(range=[8.20, 7.86], label="pH Level", values=df_climate["pH Level"]),
        ],
        labelfont=dict(color="#f0fdfa", size=13, family="Titan One, cursive"), tickfont=dict(color="#cbd5e1", size=11, family="Fredoka, sans-serif"), rangefont=dict(color="#00f5d4", size=11, family="Fredoka, sans-serif"),
    ))
    fig7_par.update_layout(**make_layout(height=460, margin=dict(l=75, r=95, t=78, b=35)))
    st.plotly_chart(fig7_par, use_container_width=True)

    hw_summary = df_climate.groupby("Marine Heatwave")[["SST (°C)", "pH Level", "Species Observed"]].mean()
    c7_1, c7_2, c7_3 = st.columns(3)
    c7_1.metric("Mean SST: Heatwave vs. Normal", f"{hw_summary.loc[True, 'SST (°C)']:.2f} °C", f"+{hw_summary.loc[True, 'SST (°C)'] - hw_summary.loc[False, 'SST (°C)']:.2f} °C hotter", delta_color="inverse")
    c7_2.metric("Mean Seawater pH: Heatwave vs. Normal", f"{hw_summary.loc[True, 'pH Level']:.3f}", f"{hw_summary.loc[True, 'pH Level'] - hw_summary.loc[False, 'pH Level']:+.3f} more acidic", delta_color="normal")
    c7_3.metric("Mean Species Observed: Heatwave vs. Normal", f"{hw_summary.loc[True, 'Species Observed']:.1f} species", f"{hw_summary.loc[True, 'Species Observed'] - hw_summary.loc[False, 'Species Observed']:+.1f} fewer species", delta_color="normal")

    render_explanation(
        context="Connecting physical heat (SST), water chemistry (pH), and marine biodiversity (Species Observed) across reef surveys.",
        description="Polylines trace individual surveys across three inverted axes comparing normal conditions (blue) against Marine Heatwaves (pink-orange).",
        conclusion="Marine Heatwaves spike to 30.0–33.2 °C while simultaneously driving lower pH (7.998 vs. 8.059) and steep biodiversity losses (97.6 vs. 124.4 species)."
    )

# 08. ANIMATED UNDERWATER REEF (OPTION 1 & OPTION 2)
section_header("sec-8", "Interactive Reef Dive", "08. Coral Reef Bleaching: Animated Underwater Experience")
yearly_summary = get_global_timeline_data(df_global)
st.markdown("<p style='color:#bae6fd;font-size:1.05rem;margin:-4px 0 14px 0;font-weight:700;'>Dive into our 60-FPS animated coral reef! Fish glide continuously without resetting and bubbles rise smoothly as you explore <b>Option 1</b> (real historical timeline) or <b>Option 2</b> (biological color shifts from healthy symbiosis to bleaching and mortality).</p>", unsafe_allow_html=True)

anim_mode = st.radio(
    "Choose Underwater View:",
    ["Option 1: Bleaching Timeline (Historical World Timeline 1980–2020)", "Option 2: Bleaching Stages (Biological Coral Health & Color Shifts)"],
    horizontal=True,
    key="vis8_mode_choice"
)

if anim_mode.startswith("Option 1"):
    if yearly_summary is not None and not yearly_summary.empty:
        yearly_pack = {}
        for _, r in yearly_summary.iterrows():
            y_int = int(r["Year"])
            b_val, s_val, w_val = float(r["mean_bleaching"]), float(r["pct_severe"]), float(r["pct_world_bleached"])
            d_idx = min(100.0, max(0.0, b_val * 1.7 + s_val * 0.45))
            st_txt = "Healthy Baseline Symbiosis" if d_idx < 25 else ("Widespread Thermal Bleaching" if d_idx < 65 else "Catastrophic Planetary Mass Bleaching")
            yearly_pack[y_int] = {
                "b": round(b_val, 1), "s": round(s_val, 1), "w": round(w_val, 1), "d": round(d_idx, 1),
                "surveys": int(r["surveys"]),
                "ssta": f"{r['mean_ssta']:+.2f} °C" if pd.notna(r["mean_ssta"]) else "N/A",
                "dhw": f"{r['mean_dhw']:.1f} DHW" if pd.notna(r["mean_dhw"]) else "N/A",
                "status": st_txt
            }
        years_list = sorted(list(yearly_pack.keys()))
        default_yr = 1998 if 1998 in years_list else years_list[0]
        rec0 = yearly_pack[default_yr]

        tl_js = f"""
        const data = {json.dumps(yearly_pack)};
        const years = {json.dumps(years_list)};
        let idx = years.indexOf({default_yr}), playing = false, timer = null;
        function updateVisual(i) {{
          idx = i; const yr = years[i], r = data[yr];
          document.getElementById("tank-disp").innerText = yr;
          document.getElementById("tank-slider").value = i;
          document.getElementById("hud-title").innerText = "Year " + yr + " Coral Reef (" + r.surveys + " surveys)";
          document.getElementById("hud-sub").innerText = "World Reefs Bleached: " + r.w + "% | Mean Severity: " + r.b + "%";
          document.getElementById("hud-status").innerText = r.status;
          document.getElementById("kpi-w").innerText = r.w + "%";
          document.getElementById("kpi-b").innerText = r.b + "%";
          document.getElementById("kpi-s").innerText = r.s + "%";
          document.getElementById("kpi-h").innerText = r.ssta + " (" + r.dhw + ")";
          const g = document.getElementById("hud-gauge-fill");
          g.style.width = r.w + "%";
          g.style.background = r.w < 35 ? "#00f5d4" : (r.w < 70 ? "#ffd166" : "#ff6b8b");
          paintReefColors(r.d);
        }}
        function pause() {{ playing = false; const b = document.getElementById("btn-play"); b.innerText = "Play Timeline"; b.style.background = "linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%)"; if (timer) clearInterval(timer); timer = null; }}
        function togglePlay() {{
          if (!playing) {{ playing = true; const b = document.getElementById("btn-play"); b.innerText = "Pause"; b.style.background = "#ff6b8b"; timer = setInterval(() => updateVisual((idx + 1) % years.length), 2000); }}
          else pause();
        }}
        function onSliderDrag(v) {{ pause(); updateVisual(parseInt(v, 10)); }}
        function jumpToYear(yr) {{ pause(); const i = years.indexOf(yr); if (i >= 0) updateVisual(i); }}
        updateVisual(idx);
        """
        render_reef_tank(
            height_px=605, tank_height_px=440,
            init_title=f"Year {default_yr} Coral Reef",
            init_sub=f"World Reefs Bleached: {rec0['w']}% | Mean Severity: {rec0['b']}%",
            init_status=rec0["status"], init_gauge_pct=rec0["w"],
            play_label="Play Timeline", slider_max=len(years_list) - 1, slider_step=1, slider_val=years_list.index(default_yr), disp_text=str(default_yr),
            quick_label="Jump to Event:",
            quick_buttons=[("1998 Super El Niño", "jumpToYear(1998)"), ("2002 Pan-Pacific", "jumpToYear(2002)"), ("2005 Caribbean", "jumpToYear(2005)"), ("2010 Global Pulse", "jumpToYear(2010)"), ("2016 Third Global", "jumpToYear(2016)"), ("2018 Cool Recovery", "jumpToYear(2018)")],
            kpi_cards=[("kpi-w", "World Reefs Bleached", f"{rec0['w']}%"), ("kpi-b", "Mean Severity", f"{rec0['b']}%"), ("kpi-s", "Severely Damaged (≥30%)", f"{rec0['s']}%"), ("kpi-h", "Heat Anomaly / DHW", f"{rec0['ssta']}")],
            custom_js_logic=tl_js,
        )

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Bar(x=yearly_summary["Year"], y=yearly_summary["pct_world_bleached"], name="World Reefs Bleached (>0%)", marker_color="rgba(0, 245, 212, 0.45)", hovertemplate="<b>Year %{x}</b><br>World Reefs Bleached: %{y:.1f}%<extra></extra>"))
        fig_timeline.add_trace(go.Scatter(x=yearly_summary["Year"], y=yearly_summary["mean_bleaching"], mode="lines+markers", name="Mean Bleaching (%)", line=dict(color="#f0fdfa", width=2.6), marker=dict(size=7, color="#00f5d4"), hovertemplate="<b>Year %{x}</b><br>Mean Bleaching: %{y:.1f}%<extra></extra>"))
        fig_timeline.add_trace(go.Scatter(x=yearly_summary["Year"], y=yearly_summary["pct_severe"], mode="lines", name="Severe Share (≥30%)", line=dict(color="#ff6b8b", width=2.2, dash="dash"), hovertemplate="<b>Year %{x}</b><br>Severely Bleached: %{y:.1f}%<extra></extra>"))
        fig_timeline.update_layout(**make_layout(height=340, margin=dict(l=55, r=25, t=100, b=50), title=dict(text="Percentage of World Coral Reefs Bleached Over Time", y=0.96, x=0.01, xanchor="left", font=dict(size=15, family="Titan One, cursive", color="#00f5d4")), xaxis=dict(title="Year", dtick=4, **AXIS_STYLE), yaxis=dict(title="Percentage (%)", range=[0, 108], **AXIS_STYLE), legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0.5, xanchor="center")))
        st.plotly_chart(fig_timeline, use_container_width=True)

        render_explanation(
            context="Global reef surveys aggregated by well-sampled survey years (n ≥ 15).",
            description="Press Play Timeline (2.0s per year) or drag the slider directly below the tank to watch coral pigmentation and fish abundance respond smoothly.",
            conclusion="In 1998, 99.7% of surveyed reefs experienced bleaching (43.1% mean severity), whereas cool periods like 2018 saw over 78% remain unbleached."
        )
else:
    stg_js = """
    let stg = 0, playing = false, timer = null;
    function updateStage(v) {
      stg = parseInt(v, 10);
      document.getElementById("tank-disp").innerText = stg + "%";
      document.getElementById("tank-slider").value = stg;
      let title = "Stage 1: Healthy Coral Colony", sub = "Active Symbiosis | Rich Zooxanthellae Pigments", col = "#00f5d4";
      if (stg >= 25 && stg < 75) { title = "Stage 2: Thermal Bleaching (Still Alive!)"; sub = "Algae Expelled | Clear Tissue Exposes White Skeleton"; col = "#ffd166"; }
      else if (stg >= 75) { title = "Stage 3: Coral Mortality & Turf Algae"; sub = "Skeleton Smothered by Murky Filamentous Turf Algae"; col = "#ff6b8b"; }
      document.getElementById("hud-title").innerText = title;
      document.getElementById("hud-sub").innerText = sub;
      document.getElementById("hud-status").innerText = stg + "% Degradation Index";
      const g = document.getElementById("hud-gauge-fill");
      g.style.width = stg + "%"; g.style.background = col;
      paintReefColors(stg);
    }
    function pause() { playing = false; const b = document.getElementById("btn-play"); b.innerText = "Play Stage Animation"; b.style.background = "linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%)"; if (timer) clearInterval(timer); timer = null; }
    function togglePlay() {
      if (!playing) { playing = true; const b = document.getElementById("btn-play"); b.innerText = "Pause"; b.style.background = "#ff6b8b"; timer = setInterval(() => updateStage(stg + 10 > 100 ? 0 : stg + 10), 1800); }
      else pause();
    }
    function onSliderDrag(v) { pause(); updateStage(v); }
    function jumpStage(v) { pause(); updateStage(v); }
    updateStage(0);
    """
    render_reef_tank(
        height_px=540, tank_height_px=440,
        init_title="Stage 1: Healthy Coral Colony", init_sub="Active Symbiosis | Rich Zooxanthellae Pigments", init_status="0% Degradation Index", init_gauge_pct=0,
        play_label="Play Stage Animation", slider_max=100, slider_step=2, slider_val=0, disp_text="0%",
        quick_label="Jump to Stage:",
        quick_buttons=[("Healthy (0%)", "jumpStage(0)"), ("Pale Stress (25%)", "jumpStage(25)"), ("Bleached (50%)", "jumpStage(50)"), ("Necrosis (75%)", "jumpStage(75)"), ("Dead Algae (100%)", "jumpStage(100)")],
        kpi_cards=[],
        custom_js_logic=stg_js,
    )

    st.markdown("<p style='font-size:1.35rem;font-weight:900;color:#f0fdfa;font-family:Titan One,cursive;margin:18px 0 14px 0;'>The Three Biological Stages of Coral Health:</p>", unsafe_allow_html=True)
    for col_box, (accent, stg, sub_h, col_txt, desc_txt, dhw_t, share_t) in zip(st.columns(3), [
        ("#00f5d4", "Stage 1: Healthy", "Active Symbiosis", "Color: Vibrant Pink, Gold & Teal", "Symbiotic algae live inside coral tissue, providing vivid color and 90% of daily energy via sunlight.", "0–2 °C-weeks", "40.2% of surveys"),
        ("#ffd166", "Stage 2: Bleached", "Algae Expelled (Alive!)", "Color: Stark Ghost-White", "Heat stress forces corals to expel algae, revealing the white calcium skeleton. Starving, yet still recoverable!", "4–8 °C-weeks", "35.7% of surveys"),
        ("#ff6b8b", "Stage 3: Dead", "Algal Smothering", "Color: Murky Olive & Grey", "Prolonged heat kills coral polyps. Fuzzy brown turf algae permanently overgrow the dead skeleton.", "≥ 8 °C-weeks", "24.1% of surveys"),
    ]):
        with col_box:
            st.markdown(f"""<div style="background:rgba(4,24,48,0.96);border:2px solid rgba(0,245,212,0.58);border-top:5px solid {accent};border-radius:18px;padding:18px 20px;height:100%;box-shadow:0 8px 22px rgba(0,10,24,0.55);">
                <div style="color:{accent};font-size:0.9rem;font-weight:900;text-transform:uppercase;font-family:Titan One,cursive;">{stg}</div>
                <h4 style="margin:4px 0 8px 0;color:#f0fdfa;font-size:1.18rem;font-family:Fredoka,sans-serif;">{sub_h}</h4>
                <div style="font-size:0.92rem;color:{accent};font-weight:700;margin-bottom:6px;">{col_txt}</div>
                <p style="font-size:0.88rem;color:#f1f5f9;line-height:1.5;margin-bottom:12px;">{desc_txt}</p>
                <div style="background:rgba(8,42,78,0.98);padding:10px 12px;border-radius:12px;font-size:0.84rem;color:#bae6fd;"><b style="color:#ffffff;">Heat Stress:</b> {dhw_t}<br><b style="color:#ffffff;">Global Share:</b> {share_t}</div>
            </div>""", unsafe_allow_html=True)

    render_explanation(
        context="Field scientists classify reef condition visually across healthy colonies, bleached-but-living skeletons, and algae-covered dead rubble.",
        description="Use the slider below the tank or press Play Stage Animation (1.8s per step) to watch smooth color transitions across the 0%–100% degradation continuum.",
        conclusion="Bleached corals are alive and can recover within 2–4 weeks if waters cool, whereas crossing 8 °C-weeks causes permanent mortality."
    )

# 09. PLAY WITH THE CORAL REEF SIMULATOR
section_header("sec-9", "Interactive Reef Sandbox", "09. Play with the Coral Reef: 5 & 10-Year Ecosystem Simulator")
st.markdown("<p style='color:#bae6fd;font-size:1.06rem;font-weight:700;margin:-4px 0 16px 0;'>Take command of the ocean! Tune <b>heat, El Niño frequency, La Niña cooling relief, ocean pH, water runoff, and oxygen</b>—check the safe vs. dangerous boundaries—then hit <b>Run Ocean Simulation</b> to watch 5 or 10 years unfold live in the reef tank!</p>", unsafe_allow_html=True)

presets = {
    "Tropical Sanctuary": dict(temp=26.4, ph=8.12, enso=8, lanina=4, turb=1.5, do=7.2),
    "2016 Super El Niño Assault": dict(temp=29.8, ph=7.96, enso=3, lanina=10, turb=4.5, do=5.2),
    "Acidic & Murky Coast": dict(temp=28.6, ph=7.84, enso=5, lanina=8, turb=8.5, do=4.4),
    "La Niña Cooling Rescue": dict(temp=27.8, ph=8.08, enso=6, lanina=2, turb=2.0, do=6.8),
}
for p_col, (p_name, p_vals) in zip(st.columns(4), presets.items()):
    if p_col.button(p_name, key=f"preset_{p_name}", use_container_width=True):
        st.session_state.update({
            "sim_temp_slider": p_vals["temp"], "sim_ph_slider": p_vals["ph"],
            "sim_enso_slider": p_vals["enso"], "sim_lanina_slider": p_vals["lanina"],
            "sim_turb_slider": p_vals["turb"], "sim_do_slider": p_vals["do"],
        })

def status_badge(ok_cond: bool, warn_cond: bool, ok_txt: str, warn_txt: str, bad_txt: str):
    cls, txt = ("badge-safe", ok_txt) if ok_cond else (("badge-warn", warn_txt) if warn_cond else ("badge-danger", bad_txt))
    st.markdown(f'<div class="{cls}">{txt}</div>', unsafe_allow_html=True)

col_sim_ctrl, col_sim_view = st.columns([1.08, 1.48])

with col_sim_ctrl:
    st.markdown("<div style='background:rgba(4,24,48,0.96);border:2.5px solid rgba(0,245,212,0.68);border-radius:20px;padding:18px 20px;box-shadow:0 8px 24px rgba(0,10,24,0.58);'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin:0 0 10px 0;font-family:Titan One,cursive;color:#00f5d4;'>Ocean Control Dials</h3>", unsafe_allow_html=True)

    sim_temp = st.slider("1. Ocean Heat / Baseline Temp (°C):", 24.0, 33.0, 26.4, 0.2, key="sim_temp_slider")
    status_badge(sim_temp <= 28.2, sim_temp <= 29.4, "Recommended: 24.0–28.2 °C (Thriving Symbiosis)", "Caution: 28.3–29.4 °C (Thermal Watch)", "Dangerous: > 29.4 °C (Severe Bleaching)")

    sim_enso = st.slider("2. El Niño Heatwave Frequency (Every N Years):", 2, 12, 8, 1, key="sim_enso_slider")
    status_badge(sim_enso >= 7, sim_enso >= 5, "Recommended: Every 7–12 Yrs (Full Recovery Window)", "Caution: Every 5–6 Yrs (Tight Recovery)", "Dangerous: Every 2–4 Yrs (Chronic Heat Collapse)")

    sim_lanina = st.slider("3. La Niña Cooling Relief (Every N Years):", 2, 12, 4, 1, key="sim_lanina_slider")
    status_badge(sim_lanina <= 5, sim_lanina <= 8, "Recommended: Every 2–5 Yrs (Frequent Cool Relief)", "Caution: Every 6–8 Yrs (Moderate Relief)", "Dangerous: Every 9–12 Yrs (Rare Cooling)")

    sim_ph = st.slider("4. Seawater pH Level (Acidification):", 7.70, 8.30, 8.12, 0.02, key="sim_ph_slider")
    status_badge(sim_ph >= 8.05, sim_ph >= 7.95, "Recommended: 8.05–8.25 pH (Strong Skeleton Growth)", "Caution: 7.95–8.04 pH (Slower Calcification)", "Dangerous: < 7.95 pH (Corrosive Acid Stress)")

    sim_turb = st.slider("5. Water Turbidity & Runoff (NTU):", 0.5, 15.0, 1.5, 0.5, key="sim_turb_slider")
    status_badge(sim_turb <= 2.5, sim_turb <= 5.0, "Recommended: ≤ 2.5 NTU (Crystal Clear Sunlight)", "Caution: 2.6–5.0 NTU (Cloudy Runoff)", "Dangerous: > 5.0 NTU (Sediment Smothers Reef)")

    sim_do = st.slider("6. Dissolved Oxygen (mg/L):", 3.0, 9.0, 7.2, 0.2, key="sim_do_slider")
    status_badge(sim_do >= 6.0, sim_do >= 4.5, "Recommended: ≥ 6.0 mg/L (Rich Marine Respiration)", "Caution: 4.5–5.9 mg/L (Low-Oxygen Stress)", "Dangerous: < 4.5 mg/L (Hypoxic Dead Zone)")

    sim_duration = st.radio("Simulation Duration:", [5, 10], horizontal=True, key="sim_duration_radio", format_func=lambda x: f"{x}-Year Forecast")
    st.button("Run Ocean Simulation", key="btn_run_sim", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_sim_view:
    sim_records = simulate_reef(sim_temp, sim_ph, sim_enso, sim_lanina, sim_turb, sim_do, years=sim_duration)
    final_rec = sim_records[-1]
    final_c, final_b, final_f = final_rec["cover"], final_rec["bleaching"], final_rec["fish"]

    sim_js = f"""
    const recs = {json.dumps(sim_records)};
    let sIdx = 0, playing = false, timer = null;
    function renderSim(i) {{
      sIdx = i; const r = recs[i];
      document.getElementById("tank-slider").value = i;
      document.getElementById("tank-disp").innerText = "Yr " + r.year;
      document.getElementById("hud-title").innerText = "Simulated Year " + r.year + " of " + recs.length;
      document.getElementById("hud-sub").innerText = "Live Coral: " + r.cover + "% | Bleaching: " + r.bleaching + "% | Fish: " + r.fish + "/100";
      document.getElementById("skpi-c").innerText = r.cover + "%";
      document.getElementById("skpi-b").innerText = r.bleaching + "%";
      document.getElementById("skpi-f").innerText = r.fish + "/100";
      document.getElementById("skpi-t").innerText = r.temp + " °C";
      const st = document.getElementById("hud-status");
      st.innerText = r.event + " (" + r.temp + " °C)";
      st.style.color = r.event.includes("El Nino") ? "#ff6b8b" : (r.event.includes("La Nina") ? "#38bdf8" : "#00f5d4");
      const g = document.getElementById("hud-gauge-fill");
      g.style.width = r.cover + "%";
      g.style.background = r.cover >= 55 ? "#00f5d4" : (r.cover >= 30 ? "#ffd166" : "#ff6b8b");
      paintReefColors(Math.min(100, Math.max(0, r.bleaching * 0.78 + (100 - r.cover) * 0.52)));
    }}
    function pause() {{ playing = false; const b = document.getElementById("btn-play"); b.innerText = "Replay " + recs.length + "-Yr Sim"; b.style.background = "linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%)"; if (timer) clearInterval(timer); timer = null; }}
    function startSim() {{
      if (timer) clearInterval(timer); playing = true;
      const b = document.getElementById("btn-play"); b.innerText = "Pause Sim"; b.style.background = "#ff6b8b";
      renderSim(0);
      timer = setInterval(() => {{ if (sIdx + 1 < recs.length) renderSim(sIdx + 1); else pause(); }}, 1700);
    }}
    function togglePlay() {{ if (!playing) startSim(); else pause(); }}
    function onSliderDrag(v) {{ pause(); renderSim(parseInt(v, 10)); }}
    startSim();
    """
    render_reef_tank(
        height_px=555, tank_height_px=390,
        init_title=f"Simulated Year {sim_duration} of {sim_duration}",
        init_sub=f"Live Coral: {final_c}% | Bleaching: {final_b}% | Fish: {int(final_f)}/100",
        init_status=f"{final_rec['event']} ({final_rec['temp']} °C)",
        init_gauge_pct=final_c,
        play_label=f"Replay {sim_duration}-Yr Sim",
        slider_max=len(sim_records) - 1, slider_step=1, slider_val=len(sim_records) - 1,
        disp_text=f"Yr {sim_duration}",
        quick_label="", quick_buttons=[],
        kpi_cards=[("skpi-c", "Live Coral Cover", f"{final_c}%"), ("skpi-b", "Bleaching Risk", f"{final_b}%"), ("skpi-f", "Fish Life Index", f"{int(final_f)}/100"), ("skpi-t", "Water Temp", f"{final_rec['temp']} °C")],
        custom_js_logic=sim_js,
    )

    if final_c >= 60.0:
        sim_verdict = f"Thriving Reef Sanctuary ({final_c:.1f}% live cover): Balanced temperatures, alkaline pH, and periodic La Niña cooling let symbiotic algae flourish and fish biodiversity reach {final_f:.0f}/100."
    elif final_c >= 30.0:
        sim_verdict = f"Stressed Reef Community ({final_c:.1f}% live cover): Intermittent El Niño heat pulses and water stress trimmed coral cover and reduced reef fish richness to {final_f:.0f}/100."
    else:
        sim_verdict = f"Ecosystem Collapse ({final_c:.1f}% live cover): Frequent heatwaves, acidification, or murky runoff overwhelmed coral recovery, leaving algae-covered rubble and a fish score of {final_f:.0f}/100."

    sim_df = pd.DataFrame(sim_records)
    fig_sim = go.Figure()
    fig_sim.add_trace(go.Scatter(x=sim_df["year"], y=sim_df["cover"], mode="lines+markers", name="Live Coral Cover (%)", line=dict(color="#00f5d4", width=3.2), marker=dict(size=8, color="#00f5d4"), hovertemplate="<b>Year %{x}</b><br>Live Coral: %{y:.1f}%<extra></extra>"))
    fig_sim.add_trace(go.Scatter(x=sim_df["year"], y=sim_df["bleaching"], mode="lines+markers", name="Bleaching (%)", line=dict(color="#ff6b8b", width=2.4, dash="dot"), marker=dict(size=6, color="#ff6b8b"), hovertemplate="<b>Year %{x}</b><br>Bleaching: %{y:.1f}%<extra></extra>"))
    fig_sim.add_trace(go.Scatter(x=sim_df["year"], y=sim_df["fish"], mode="lines+markers", name="Fish Index", line=dict(color="#ffd166", width=2.2), marker=dict(size=6, color="#ffd166"), hovertemplate="<b>Year %{x}</b><br>Fish Index: %{y:.0f}/100<extra></extra>"))
    fig_sim.update_layout(**make_layout(height=330, margin=dict(l=55, r=25, t=100, b=50), title=dict(text=f"{sim_duration}-Year Simulated Ecosystem Trajectory", y=0.96, x=0.01, xanchor="left", font=dict(size=15, family="Titan One, cursive", color="#00f5d4")), xaxis=dict(title="Simulated Year", dtick=1, **AXIS_STYLE), yaxis=dict(title="Score / Percentage (%)", range=[0, 108], **AXIS_STYLE), legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0.5, xanchor="center")))
    st.plotly_chart(fig_sim, use_container_width=True)

    st.markdown(f'<div class="narrative-box"><p><span class="narrative-label">Simulation Outcome:</span> {sim_verdict}</p></div>', unsafe_allow_html=True)