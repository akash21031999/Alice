"""
ALPHA TERMINAL v6 — Agentic Moonshot Pipeline
Automated supply-chain intelligence. Top 5 asymmetric bets. Every week.

4-Agent Pipeline (all Gemini — fully free):
  Agent 1 — RESEARCHER    Maps supply chain for each theme. Tier 1/2/3 + bottleneck.
  Agent 2 — SCORER        Asymmetry score: TAM/MCAP × smart-money delta × quant signals.
  Agent 3 — RANKER        Kills noise, ranks top 5, stores results.
  Agent 4 — WRITER        One-click article generator (LinkedIn/X/Substack).

Free data sources:
  Yahoo Finance v8 API    Prices, history, options (no yfinance library)
  EDGAR EFTS              13F institutional + Form 4 insider + 8-K catalysts
  Google News RSS         News velocity per ticker
  USASpending.gov         Pentagon contract awards
  USPTO PatentsView       Patent filings
  CoinGecko               BTC/crypto price
  Finnhub (optional)      60 calls/min free — real insider + sentiment data
  Polygon.io (optional)   5 calls/min free — enhanced market data
"""

import streamlit as st
st.set_page_config(
    page_title="ALPHA TERMINAL v6",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import requests, feedparser, json, re, time, threading, math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# ══════════════════════════════════════════════════════════════════════════════
#  DARK CYBER TERMINAL DESIGN
#  v5 aesthetic preserved and enhanced — Roboto Mono + green on black
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500;700&family=Share+Tech+Mono&display=swap');

/* ── RESET & BASE ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; font-style: normal !important; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewContainer"] > section > div,
.main, .main > div {
    background-color: #020509 !important;
    font-family: 'Roboto Mono', 'Share Tech Mono', monospace !important;
    color: #00ffaa !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background: #030710 !important;
    border-right: 1px solid #0d2818 !important;
}
[data-testid="stSidebar"] * { color: #4dffb4 !important; }
[data-testid="stSidebar"] strong { color: #00ffaa !important; font-weight: 700 !important; }
.block-container { padding: 0 1.8rem 4rem !important; max-width: 1500px !important; }
em, i { font-style: normal !important; }
strong, b { font-weight: 700 !important; color: #00ffaa !important; }
a { color: #00ffaa !important; text-decoration: none !important; }
a:hover { text-decoration: underline !important; color: #4dffb4 !important; }

/* ── TERMINAL HEADER ─────────────────────────────────────────────────── */
.at-header {
    background: #020509;
    border-bottom: 2px solid #00ffaa;
    padding: 14px 0 12px;
    margin-bottom: 0;
}
.at-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #00ffaa !important;
    letter-spacing: 3px;
    text-transform: uppercase;
    line-height: 1;
}
.at-title .v6 { color: #ff6b35 !important; }
.at-sub {
    font-size: 0.62rem;
    color: #1a7a45 !important;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
}
.at-status-row {
    display: flex; gap: 8px; margin-left: auto; align-items: center; flex-wrap: wrap;
}
.at-badge {
    font-size: 0.65rem; font-weight: 700; padding: 3px 10px;
    border-radius: 2px; letter-spacing: 1.5px; text-transform: uppercase; white-space: nowrap;
    font-family: 'Roboto Mono', monospace;
}
.badge-active { background: #003d1f; color: #00ffaa !important; border: 1px solid #00ffaa; }
.badge-warn   { background: #2d1900; color: #ff6b35 !important; border: 1px solid #ff6b35; }
.badge-info   { background: #001533; color: #00aaff !important; border: 1px solid #00aaff; }

/* ── TICKER RIBBON ───────────────────────────────────────────────────── */
.ticker-ribbon {
    display: flex;
    background: #030710;
    border-bottom: 1px solid #0d2818;
    padding: 6px 0;
    margin: 0 -1.8rem 20px;
    overflow-x: auto;
    scrollbar-width: none;
}
.ticker-ribbon::-webkit-scrollbar { display: none; }
.titem {
    display: flex; align-items: center; gap: 8px;
    padding: 0 16px; border-right: 1px solid #0d2818; flex-shrink: 0;
}
.tlbl  { font-size: 0.6rem; color: #1a7a45 !important; letter-spacing: 1.5px; text-transform: uppercase; }
.tprice{ font-size: 0.8rem; font-weight: 700; color: #e0e0e0 !important; }
.tup   { font-size: 0.68rem; color: #00ffaa !important; font-weight: 500; }
.tdn   { font-size: 0.68rem; color: #ff4444 !important; font-weight: 500; }
.tfl   { font-size: 0.68rem; color: #1a7a45 !important; }

/* ── SCAN PANEL ─────────────────────────────────────────────────────── */
.scan-panel {
    background: #030710;
    border: 1px solid #0d2818;
    border-top: 2px solid #00ffaa;
    padding: 18px 22px 16px;
    margin-bottom: 18px;
}
.scan-label {
    font-size: 0.6rem; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #1a7a45 !important; margin-bottom: 8px; display: block;
}

/* ── THEME GRID ─────────────────────────────────────────────────────── */
.theme-grid { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
.theme-pill {
    font-size: 0.65rem; font-weight: 500; padding: 3px 10px;
    border: 1px solid #0d4a25; border-radius: 2px; cursor: pointer;
    color: #4dffb4 !important; background: #030d08;
    letter-spacing: 0.5px; transition: all 0.1s;
}
.theme-pill:hover { border-color: #00ffaa; color: #00ffaa !important; background: #001a0d; }
.theme-pill.selected { border-color: #00ffaa; background: #001a0d; color: #00ffaa !important; }

/* ── RESULT TABLE ───────────────────────────────────────────────────── */
.result-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    margin: 12px 0;
}
.result-table th {
    background: #030d08;
    color: #1a7a45 !important;
    font-size: 0.6rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #0d4a25;
    font-weight: 700;
}
.result-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #030d08;
    color: #c8fae0 !important;
    vertical-align: top;
}
.result-table tr:hover td { background: #030d08; }
.result-table tr.top-pick td { border-left: 2px solid #00ffaa; }

.score-bar-bg { background: #030d08; border-radius: 1px; height: 5px; width: 80px; display: inline-block; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 1px; }

.rank-num { font-size: 1.3rem; font-weight: 700; color: #00ffaa !important; line-height: 1; }
.rank-num.r2 { color: #4dffb4 !important; }
.rank-num.r3 { color: #1a9963 !important; }
.rank-num.r4,.rank-num.r5 { color: #0d6640 !important; }

.ticker-cell { font-size: 1.0rem; font-weight: 700; color: #00ffaa !important; letter-spacing: 1px; }
.company-cell { font-size: 0.75rem; color: #4dffb4 !important; margin-top: 2px; }
.tier-badge {
    font-size: 0.58rem; font-weight: 700; padding: 1px 6px; border-radius: 2px;
    letter-spacing: 1px; text-transform: uppercase;
}
.tier-t1 { background: #001a0d; color: #1a9963 !important; border: 1px solid #0d4a25; }
.tier-t2 { background: #001a33; color: #00aaff !important; border: 1px solid #003366; }
.tier-t3 { background: #2d1900; color: #ff8c00 !important; border: 1px solid #4d2e00; }
.tier-bn { background: #2d0000; color: #ff4444 !important; border: 1px solid #4d0000; }

.chg-up { color: #00ffaa !important; font-weight: 700; }
.chg-dn { color: #ff4444 !important; font-weight: 700; }

/* ── ASYMMETRY SCORE ─────────────────────────────────────────────────── */
.asym-score {
    font-size: 1.4rem; font-weight: 700; font-family: 'Roboto Mono', monospace;
    line-height: 1;
}
.asym-score.s9, .asym-score.s10 { color: #00ffaa !important; text-shadow: 0 0 10px rgba(0,255,170,0.5); }
.asym-score.s7, .asym-score.s8  { color: #4dffb4 !important; }
.asym-score.s5, .asym-score.s6  { color: #00aaff !important; }
.asym-score.slow               { color: #4a5568 !important; }

/* ── SMART MONEY ─────────────────────────────────────────────────────── */
.sm-bullish { color: #00ffaa !important; font-weight: 700; }
.sm-bearish { color: #ff4444 !important; font-weight: 700; }
.sm-neutral { color: #4a5568 !important; }

/* ── AGENT STATUS ────────────────────────────────────────────────────── */
.agent-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px; background: #030710;
    border: 1px solid #0d2818; border-radius: 2px; margin: 4px 0;
}
.agent-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.agent-dot.running  { background: #ff6b35; animation: blink 0.8s infinite; }
.agent-dot.complete { background: #00ffaa; }
.agent-dot.waiting  { background: #0d4a25; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.agent-name { font-size: 0.72rem; font-weight: 700; color: #00ffaa !important; letter-spacing: 1px; text-transform: uppercase; }
.agent-detail { font-size: 0.68rem; color: #1a9963 !important; margin-left: auto; }

/* ── ARTICLE CARD ────────────────────────────────────────────────────── */
.article-card {
    background: #030710;
    border: 1px solid #0d4a25;
    border-top: 2px solid #00ffaa;
    border-radius: 2px;
    padding: 16px 18px;
    margin: 8px 0;
    color: #c8fae0 !important;
    line-height: 1.7;
    font-size: 0.85rem;
}
.article-card h2, .article-card h3 {
    color: #00ffaa !important;
    font-weight: 700;
    letter-spacing: 1px;
    margin: 12px 0 6px;
}

/* ── NEWS CARDS ──────────────────────────────────────────────────────── */
.news-card {
    border-bottom: 1px solid #0d2818;
    padding: 8px 0;
}
.news-title { color: #c8fae0 !important; font-size: 0.78rem; line-height: 1.4; display: block; }
.news-src   { color: #1a7a45 !important; font-size: 0.65rem; margin-top: 2px; display: block; }

/* ── SECTION HEADER ─────────────────────────────────────────────────── */
.sec-hdr {
    font-size: 0.6rem; font-weight: 700; letter-spacing: 3px;
    text-transform: uppercase; color: #1a7a45 !important;
    border-bottom: 1px solid #0d4a25; padding-bottom: 6px; margin: 20px 0 14px;
    display: block;
}

/* ── METRIC CARDS ────────────────────────────────────────────────────── */
.metric-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.metric-box {
    background: #030d08; border: 1px solid #0d4a25; flex: 1; min-width: 110px;
    padding: 12px 14px;
}
.metric-lbl { font-size: 0.58rem; color: #1a7a45 !important; text-transform: uppercase; letter-spacing: 1.5px; display: block; margin-bottom: 4px; }
.metric-val { font-size: 1.1rem; font-weight: 700; color: #00ffaa !important; font-family: 'Roboto Mono', monospace; }
.metric-val.red { color: #ff4444 !important; }
.metric-val.orange { color: #ff6b35 !important; }

/* ── INPUTS / BUTTONS ────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #030710 !important;
    border: 1px solid #0d4a25 !important;
    border-radius: 2px !important;
    color: #00ffaa !important;
    font-family: 'Roboto Mono', monospace !important;
    font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00ffaa !important;
    box-shadow: 0 0 8px rgba(0,255,170,0.2) !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #1a7a45 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #030710 !important;
    border: 1px solid #0d4a25 !important;
    border-radius: 2px !important;
    color: #00ffaa !important;
}
div.stButton > button {
    border-radius: 2px !important;
    font-weight: 700 !important;
    font-family: 'Roboto Mono', monospace !important;
    font-size: 0.82rem !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    transition: all 0.12s !important;
}
div.stButton > button[kind="primary"] {
    background: #00ffaa !important;
    border: 1px solid #00ffaa !important;
    color: #020509 !important;
}
div.stButton > button[kind="primary"]:hover {
    background: #4dffb4 !important;
    box-shadow: 0 0 20px rgba(0,255,170,0.3) !important;
}
div.stButton > button[kind="secondary"] {
    background: #030710 !important;
    border: 1px solid #0d4a25 !important;
    color: #00ffaa !important;
}
div.stButton > button[kind="secondary"]:hover {
    border-color: #00ffaa !important;
}

/* ── STREAMLIT OVERRIDES ─────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid #0d4a25 !important; border-radius: 2px !important; }
[data-testid="stDataFrame"] * { color: #c8fae0 !important; background: #020509 !important; }
[data-testid="stMetricValue"] { color: #00ffaa !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #1a7a45 !important; font-size: 0.7rem !important; }
details[data-testid="stExpander"] { border: 1px solid #0d4a25 !important; border-radius: 2px !important; background: #030710 !important; }
details[data-testid="stExpander"] summary { color: #00ffaa !important; }
[data-testid="stStatusWidget"] { border-radius: 2px !important; }
div[data-testid="stMarkdownContainer"] * { font-style: normal !important; }
div[data-testid="stMarkdownContainer"] em { font-style: normal !important; color: #4dffb4 !important; }
div[data-testid="stMarkdownContainer"] p  { color: #c8fae0 !important; line-height: 1.75 !important; font-size: 0.85rem !important; }
div[data-testid="stMarkdownContainer"] li { color: #c8fae0 !important; line-height: 1.65 !important; }
div[data-testid="stMarkdownContainer"] strong { color: #00ffaa !important; font-weight: 700 !important; }
div[data-testid="stMarkdownContainer"] h2 { color: #00ffaa !important; font-weight: 700 !important; border-bottom: 1px solid #0d4a25 !important; }
div[data-testid="stMarkdownContainer"] h3 { color: #4dffb4 !important; font-weight: 700 !important; }
div[data-testid="stMarkdownContainer"] code { background: #030d08 !important; color: #00ffaa !important; padding: 1px 5px !important; border: 1px solid #0d4a25 !important; font-size: 0.82em !important; }
div[data-testid="stMarkdownContainer"] table { display: block !important; overflow-x: auto !important; border-collapse: collapse !important; }
div[data-testid="stMarkdownContainer"] th { background: #030d08 !important; color: #1a7a45 !important; padding: 7px 11px !important; border: 1px solid #0d4a25 !important; }
div[data-testid="stMarkdownContainer"] td { padding: 6px 11px !important; border: 1px solid #0d2818 !important; color: #c8fae0 !important; }
div[data-testid="stMarkdownContainer"] hr { border-color: #0d4a25 !important; }
[data-testid="stProgress"] > div > div { background: #00ffaa !important; }
[data-testid="stStatusWidget"] { background: #030710 !important; border-color: #0d4a25 !important; }

/* ── TABS ─────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #0d4a25 !important; background: #020509 !important; }
[data-testid="stTabs"] button {
    font-family: 'Roboto Mono', monospace !important;
    font-size: 0.72rem !important; font-weight: 700 !important;
    color: #1a7a45 !important; padding: 10px 18px !important;
    border-bottom: 2px solid transparent !important; border-radius: 0 !important;
    background: transparent !important; margin-bottom: -2px !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important;
}
[data-testid="stTabs"] button:hover { color: #4dffb4 !important; }
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #00ffaa !important; border-bottom: 2px solid #00ffaa !important;
}

/* ── SCROLLBAR ───────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #020509; }
::-webkit-scrollbar-thumb { background: #0d4a25; border-radius: 2px; }

/* ── MOBILE ──────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
    .block-container { padding: 0 0.8rem 2rem !important; }
    .at-status-row { display: none; }
    .ticker-ribbon { margin: 0 -0.8rem 16px; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  20 PREDEFINED SUPPLY-CHAIN THEMES — the automated pipeline scans these
# ══════════════════════════════════════════════════════════════════════════════
THEMES = [
    {"id":"lidar",          "name":"LiDAR / Autonomous Sensing",   "tags":["robotaxi","autonomy","depth sensing"]},
    {"id":"photonics",      "name":"Photonics / InP Wafers",       "tags":["optical","GaAs","compound semi"]},
    {"id":"ssbattery",      "name":"Solid-State Batteries",        "tags":["EV","energy storage","electrolyte"]},
    {"id":"euv",            "name":"EUV Lithography",              "tags":["ASML","chipmaking","photomask"]},
    {"id":"glp1",           "name":"GLP-1 / Obesity Drugs",        "tags":["semaglutide","CDMO","API supply"]},
    {"id":"hypersonic",     "name":"Hypersonic Weapons",           "tags":["DARPA","refractory","TPS materials"]},
    {"id":"quantum",        "name":"Quantum Computing",            "tags":["cryogenics","dilution fridges","qubit"]},
    {"id":"smallsat",       "name":"Small Satellites / LEO",       "tags":["RKLB","launch","solar arrays"]},
    {"id":"uranium",        "name":"Uranium / Nuclear Renaissance","tags":["SMR","fuel supply","enrichment"]},
    {"id":"robotics",       "name":"Humanoid Robotics",            "tags":["actuators","BLDC motors","sensors"]},
    {"id":"aichip",         "name":"AI Chip Supply Chain",         "tags":["HBM","CoWoS","advanced packaging"]},
    {"id":"rareearth",      "name":"Rare Earth / Critical Minerals","tags":["neodymium","dysprosium","mining"]},
    {"id":"biodefense",     "name":"Biodefense / mRNA Vaccines",   "tags":["LNP","lipid nanoparticle","BARDA"]},
    {"id":"undersea",       "name":"Undersea Cables / Sonar",      "tags":["submarine","sonar","acoustic"]},
    {"id":"edgeinference",  "name":"Edge AI Inference Chips",      "tags":["NPU","RISC-V","sub-7nm"]},
    {"id":"electrolyzer",   "name":"Green Hydrogen / Electrolyzers","tags":["PEM","iridium","stack"]},
    {"id":"copper",         "name":"Copper Mining & Processing",   "tags":["FCEV","grid","electrification"]},
    {"id":"axle_chips",     "name":"Power Semiconductors / SiC GaN","tags":["EV inverter","MOSFET","Wolfspeed"]},
    {"id":"cybersec",       "name":"OT / ICS Cybersecurity",       "tags":["SCADA","grid security","defense"]},
    {"id":"directed_energy","name":"Directed Energy Weapons",      "tags":["high power laser","fiber laser","beam"]},
]

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
for k, v in [
    ("pipeline_results", {}),   # {theme_id: {agent1, agent2, agent3 results}}
    ("top5", []),               # final ranked top 5
    ("last_run", None),
    ("agent_status", {}),       # {theme_id: {a1,a2,a3,a4: "waiting/running/done"}}
    ("macro_cache", {}),
    ("article_cache", {}),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR CONFIG
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("**🏦 ALPHA TERMINAL v6**")
    st.divider()
    gemini_key  = st.text_input("Gemini API Key", type="password", placeholder="AIza...", key="si_gemini",
                                help="Free · aistudio.google.com/app/apikey")
    finnhub_key = st.text_input("Finnhub (optional)", type="password", placeholder="60 req/min free", key="si_finnhub")
    polygon_key = st.text_input("Polygon.io (optional)", type="password", placeholder="5 req/min free", key="si_polygon")
    tg_token    = st.text_input("Telegram Token", type="password", placeholder="optional", key="si_tg")
    tg_chat     = st.text_input("Telegram Chat ID", placeholder="optional", key="si_tgchat")

    st.divider()
    st.markdown("**Pipeline Settings**")
    themes_to_scan = st.slider("Themes per scan", 1, 20, 5, key="sl_themes")
    auto_run       = st.checkbox("Auto-run on load", value=False, key="cb_auto")
    custom_themes  = st.text_input("Custom themes (comma-sep)", placeholder="CRISPR, Space Mining...", key="ti_custom")

    st.divider()
    last_run = st.session_state.get("last_run")
    last_str = last_run[:16].replace("T"," ") if last_run else "Never"
    n_top5   = len(st.session_state.get("top5",[]))
    st.markdown(f'<div style="font-size:0.72rem;color:#1a7a45;line-height:1.9">'
                f'Last scan: {last_str}<br>'
                f'Top picks found: {n_top5}<br>'
                f'{"🟢 AI Ready" if gemini_key else "🔴 No API Key"}</div>',
                unsafe_allow_html=True)
    if st.button("CLEAR SESSION", key="btn_clr", use_container_width=True):
        for k in ["pipeline_results","top5","last_run","agent_status","article_cache"]:
            st.session_state[k] = {} if "cache" in k or "results" in k or "status" in k else ([] if k=="top5" else None)
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  DATA LAYER — all free, all direct
# ══════════════════════════════════════════════════════════════════════════════
YF = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"application/json"}

@st.cache_data(ttl=180, show_spinner=False)
def yf_price(sym):
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d",headers=YF,timeout=6)
        c=[x for x in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x]
        return (round(c[-1],2),round((c[-1]/c[-2]-1)*100,2)) if len(c)>=2 else (None,None)
    except: return None,None

@st.cache_data(ttl=300, show_spinner=False)
def yf_history(sym,rng="3mo"):
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range={rng}",headers=YF,timeout=8)
        d=r.json()["chart"]["result"][0]
        closes=[c for c in d["indicators"]["quote"][0]["close"] if c is not None]
        vols  =[v for v in d["indicators"]["quote"][0].get("volume",[]) if v is not None]
        return closes,vols,d.get("meta",{})
    except: return [],[],{}

@st.cache_data(ttl=300, show_spinner=False)
def yf_summary(sym):
    """Get company name + fundamentals from Yahoo Finance summary."""
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=assetProfile,financialData,defaultKeyStatistics",
                       headers=YF,timeout=8)
        js=r.json().get("quoteSummary",{}).get("result",[])
        if not js: return {}
        out={}
        profile=js[0].get("assetProfile",{})
        fin    =js[0].get("financialData",{})
        stats  =js[0].get("defaultKeyStatistics",{})
        out["sector"]    =profile.get("sector","")
        out["industry"]  =profile.get("industry","")
        out["employees"] =profile.get("fullTimeEmployees",0)
        out["mcap"]      =stats.get("marketCap",{}).get("raw",0)
        out["forward_pe"]=fin.get("forwardPE",{}).get("raw",None)
        out["target_mean"]=fin.get("targetMeanPrice",{}).get("raw",None)
        out["current"]   =fin.get("currentPrice",{}).get("raw",None)
        return out
    except: return {}

@st.cache_data(ttl=600, show_spinner=False)
def yf_options_pc(sym):
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v7/finance/options/{sym}",headers=YF,timeout=8)
        root=r.json().get("optionChain",{}).get("result",[])
        if not root: return None
        cv=pv=0
        for block in root[:3]:
            for ob in block.get("options",[]):
                cv+=sum(c.get("volume") or 0 for c in ob.get("calls",[]))
                pv+=sum(p.get("volume") or 0 for p in ob.get("puts",[]))
        return round(pv/max(cv,1),3) if cv else None
    except: return None

@st.cache_data(ttl=300, show_spinner=False)
def get_macro():
    syms={"SPX":"%5EGSPC","VIX":"%5EVIX","10Y":"%5ETNX","DXY":"DX-Y.NYB","Gold":"GC%3DF","Oil":"CL%3DF"}
    out={lbl:yf_price(sym) for lbl,sym in syms.items()}
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price",
            params={"ids":"bitcoin","vs_currencies":"usd","include_24hr_change":"true"},
            timeout=5,headers={"User-Agent":"AlphaTerminal/6.0"})
        d=r.json()["bitcoin"]; out["BTC"]=(round(d["usd"],0),round(d["usd_24h_change"],2))
    except: out["BTC"]=(None,None)
    return out

@st.cache_data(ttl=900, show_spinner=False)
def edgar_13f_signal(ticker):
    """EDGAR full-text search for 13F filings mentioning this ticker — proxy for institutional interest."""
    try:
        r=requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=13F-HR&dateRange=custom"
            f"&startdt={(datetime.now()-timedelta(days=90)).strftime('%Y-%m-%d')}",
            headers={"User-Agent":"AlphaTerminal research@alpha.ai"},timeout=10)
        hits=r.json().get("hits",{}).get("hits",[])
        return {"count":len(hits),"filers":[h["_source"].get("entity_name","") for h in hits[:5]]}
    except: return {"count":0,"filers":[]}

@st.cache_data(ttl=900, show_spinner=False)
def edgar_insider_score(ticker):
    """EDGAR Form 4 — open-market buy cluster score."""
    try:
        start=(datetime.now()-timedelta(days=45)).strftime("%Y-%m-%d")
        r=requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={start}",
            headers={"User-Agent":"AlphaTerminal research@alpha.ai"},timeout=10)
        hits=r.json().get("hits",{}).get("hits",[])
        dates=[h["_source"].get("file_date","") for h in hits[:10]]
        unique=len(set(dates))
        return {"filings":len(hits),"unique_dates":unique,"cluster":unique>=3}
    except: return {"filings":0,"unique_dates":0,"cluster":False}

@st.cache_data(ttl=600, show_spinner=False)
def finnhub_insider_net(sym,key):
    if not key: return 0
    try:
        r=requests.get(f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={sym}&token={key}",timeout=6)
        data=r.json().get("data",[])
        cutoff=(datetime.now()-timedelta(days=45)).strftime("%Y-%m-%d")
        buys =len([t for t in data if str(t.get("transactionType","")).upper() in ["P","BUY"] and str(t.get("transactionDate",""))>=cutoff])
        sells=len([t for t in data if str(t.get("transactionType","")).upper() in ["S","SALE"] and str(t.get("transactionDate",""))>=cutoff])
        return buys-sells
    except: return 0

@st.cache_data(ttl=600, show_spinner=False)
def polygon_short_interest(sym,key):
    """Polygon.io short interest (free tier)."""
    if not key: return None
    try:
        r=requests.get(f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{sym}?apiKey={key}",timeout=6)
        d=r.json().get("ticker",{})
        return {"short_pct":d.get("shortInterest",None),"float_pct":None}
    except: return None

@st.cache_data(ttl=600, show_spinner=False)
def news_count(ticker,days=7):
    """Google News RSS — article count for news velocity."""
    try:
        url=f"https://news.google.com/rss/search?q={requests.utils.quote(ticker+' stock')}&hl=en-US&gl=US&ceid=US:en"
        feed=feedparser.parse(url)
        entries=feed.entries[:20]
        cutoff=datetime.now()-timedelta(days=days)
        recent=[]; headlines=[]
        for e in entries:
            try:
                import email.utils
                dt=datetime(*email.utils.parsedate(e.get("published",""))[:6])
                if dt>cutoff: recent.append(e.title)
                headlines.append({"title":e.title,"source":e.get("source",{}).get("title",""),"link":e.get("link","")})
            except:
                headlines.append({"title":e.title,"source":"","link":""})
        return len(recent), headlines[:5]
    except: return 0,[]

@st.cache_data(ttl=1800, show_spinner=False)
def dod_contracts(company,days=30):
    try:
        end=datetime.now().strftime("%Y-%m-%d")
        start=(datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")
        payload={"filters":{"time_period":[{"start_date":start,"end_date":end}],
            "agencies":[{"type":"awarding_agency","tier":"toptier","name":"Department of Defense"}],
            "award_type_codes":["A","B","C","D"],"recipient_search_text":[company[:30]]},
            "fields":["recipient_name","total_obligated_amount","action_date"],"sort":"total_obligated_amount","order":"desc","limit":3,"page":1}
        r=requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",json=payload,timeout=12,
                        headers={"Content-Type":"application/json"})
        results=r.json().get("results",[])
        return sum(float(x.get("total_obligated_amount",0)) for x in results)/1e6
    except: return 0.0

# ══════════════════════════════════════════════════════════════════════════════
#  QUANTITATIVE ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def calc_rsi(c,n=14):
    if len(c)<n+1: return 50.0
    a=np.array(c,dtype=float); d=np.diff(a)
    g=np.where(d>0,d,0.); l=np.where(d<0,-d,0.)
    return round(float(100-100/(1+np.mean(g[-n:])/(np.mean(l[-n:])+1e-9))),1)

def calc_macd_hist(c):
    if len(c)<35: return 0
    s=pd.Series(c,dtype=float)
    m=s.ewm(span=12,adjust=False).mean()-s.ewm(span=26,adjust=False).mean()
    return round(float((m-m.ewm(span=9,adjust=False).mean()).iloc[-1]),4)

def quant_score(closes,vols,meta,price):
    """Score 0-3 based on technical signals."""
    if not closes or not price: return 0,{}
    rsi=calc_rsi(closes); mh=calc_macd_hist(closes)
    vr=round(vols[-1]/max(float(np.mean(vols[-21:-1])),1),2) if len(vols)>21 and vols[-1] else 1.0
    w52h=meta.get("fiftyTwoWeekHigh",0) or 0; w52l=meta.get("fiftyTwoWeekLow",0) or 0
    pct52=(price-w52l)/max(w52h-w52l,0.01) if w52h and w52l else 0.5
    ma50=float(np.mean(closes[-50:])) if len(closes)>=50 else price
    sc=0.0
    if rsi<35: sc+=1.0
    elif rsi<45: sc+=0.5
    if mh>0: sc+=0.5
    if pct52<0.3: sc+=0.8
    if price>ma50: sc+=0.3
    if vr>2.0: sc+=0.5
    return min(3.0,round(sc,1)),{"rsi":rsi,"macd_hist":mh,"vol_ratio":vr,"pct52":round(pct52*100,0),"ma50_above":price>ma50}

# ══════════════════════════════════════════════════════════════════════════════
#  ASYMMETRY SCORE — the core algorithm
# ══════════════════════════════════════════════════════════════════════════════
def calc_asymmetry_score(ticker,tier,smart_money_score,quant_sc,mcap_b,dod_m,news_v,pc_ratio):
    """
    Asymmetry Score (0-10):
      Tier bonus        — T3/bottleneck companies score higher (smaller, less known)
      Smart money       — institutional 13F + insider cluster
      Quantitative      — RSI/MACD/vol technical stack
      Size alpha        — smaller MCAP = more upside potential
      Catalyst          — DoD contracts, news velocity, low P/C
    """
    score=0.0
    # Tier bonus
    tier_pts={"T1":0.5,"T2":1.5,"T3":2.5,"BOTTLENECK":3.0,"MOAT":2.8}.get(tier,1.0)
    score+=tier_pts
    # Smart money (0-2)
    score+=min(2.0,smart_money_score)
    # Quant signals (0-2)
    score+=min(2.0,quant_sc*0.67)
    # Size alpha — smaller is more asymmetric
    if mcap_b:
        if mcap_b<0.3:   score+=2.0
        elif mcap_b<1.0: score+=1.5
        elif mcap_b<5.0: score+=1.0
        elif mcap_b<15:  score+=0.5
    # Catalysts
    if dod_m>100: score+=0.8
    elif dod_m>10: score+=0.4
    if news_v>5: score+=0.4
    elif news_v>2: score+=0.2
    if pc_ratio and pc_ratio<0.5: score+=0.4  # heavy calls = bullish dark money
    return round(min(10.0,score),1)

# ══════════════════════════════════════════════════════════════════════════════
#  4-AGENT PIPELINE — all Gemini, all free
# ══════════════════════════════════════════════════════════════════════════════

AGENT1_SYSTEM = """You are a Supply Chain Forensic Analyst — the world's best at finding the company
that giants cannot live without.

CLASSIFICATION RULES:
- TIER 1: Large direct suppliers (well-known, low asymmetry)
- TIER 2: Component/process suppliers (overlooked, higher asymmetry)
- TIER 3: Raw material/IP/specialty (where the real alpha is — small, unknown)
- BOTTLENECK: The ONE company that owns a process or IP that cannot be bypassed
- MOAT: Regulatory/patent position that takes years to replicate

STRICT OUTPUT FORMAT:
For each company: **$TICKER** | TIER | What they supply | Why asymmetric | Market cap estimate ($B)
End with exactly: TICKERS: TIER=$TICKER, TIER=$TICKER, TIER=$TICKER, BOTTLENECK=$TICKER, MOAT=$TICKER
(Use N/A if none found for that category)"""

AGENT2_SYSTEM = """You are a Quantitative Smart Money Analyst.
Given a ticker and quantitative data, score its asymmetric investment potential.
Be precise. Only use numbers from the data provided.
Return a structured score with exact reasoning."""

AGENT3_SYSTEM = """You are a Chief Investment Officer ranking asymmetric investment opportunities.
You filter out hype and retail noise. You surface only institutionally-grade overlooked names.
Rules: Never recommend large-cap well-known companies as the primary bet.
The best bet is always the overlooked Tier 2/3 supplier with strong fundamentals and smart-money accumulation.
Be brutally honest. If a theme has no good plays, say so."""

AGENT4_SYSTEM = """You are a financial content writer creating posts for institutional-grade research publications.
Style: authoritative, data-driven, contrarian edge. Avoid generic financial language.
Format varies by platform. Always end with 3 specific tickers and why they're asymmetric."""

def call_gemini_raw(system,user,key,temperature=0.2):
    """Non-streaming Gemini call with Google Search grounding."""
    if not key: return "[No API key]"
    try:
        client=genai.Client(api_key=key)
        srch=types.Tool(google_search=types.GoogleSearch())
        config=types.GenerateContentConfig(tools=[srch],temperature=temperature,system_instruction=system)
        return client.models.generate_content(model="gemini-2.5-flash",contents=user,config=config).text
    except Exception as e: return f"[Error: {e}]"

def stream_gemini(system,user,key,temperature=0.3):
    if not key: yield "[No API key]"; return
    try:
        client=genai.Client(api_key=key)
        srch=types.Tool(google_search=types.GoogleSearch())
        config=types.GenerateContentConfig(tools=[srch],temperature=temperature,system_instruction=system)
        resp=client.models.generate_content_stream(model="gemini-2.5-flash",contents=user,config=config)
        for chunk in resp:
            if chunk.text: yield chunk.text
    except Exception as e: yield f"[Error: {e}]"

def agent1_researcher(theme,key):
    """Maps supply chain for a theme. Returns full map + extracted tickers."""
    t=theme["name"]; tags=", ".join(theme["tags"])
    prompt=f"""Date: {datetime.now():%Y-%m-%d}
RESEARCH THEME: {t}
RELATED KEYWORDS: {tags}

Map the COMPLETE supply chain. Use Google Search for current data.

## TIER 1 — Direct Suppliers (3-4 companies, **$TICKER**)
## TIER 2 — Hidden Asymmetric Plays (3-4 companies, **$TICKER**, why overlooked)
## TIER 3 — Raw Material / IP Moat (2-3 companies, **$TICKER**, the deepest alpha)
## BOTTLENECK — The one company giants CANNOT bypass (**$TICKER**)
## MOAT — Regulatory/patent position nobody can replicate (**$TICKER**)

For EACH company: market cap estimate, why it's asymmetric, what smart money would miss.

TICKERS: T1=$X,T2=$X,T3=$X,BOTTLENECK=$X,MOAT=$X"""
    return call_gemini_raw(AGENT1_SYSTEM,prompt,key,temperature=0.15)

def extract_tickers_from_map(chain_map):
    """Parse tickers + tier from Agent 1 output."""
    results={}
    # From TICKERS: line
    m=re.search(r'TICKERS:\s*([^\n]+)',chain_map,re.IGNORECASE)
    if m:
        raw=m.group(1)
        for pair in re.finditer(r'(T1|T2|T3|BOTTLENECK|MOAT|BN|MOAT)\s*=\s*\$?([A-Z][A-Z0-9\-]{0,5})',raw,re.IGNORECASE):
            tier=pair.group(1).upper(); sym=pair.group(2).upper()
            if sym not in ["NA","N/A"] and len(sym)>=2: results[sym]=tier
    # From **$TICKER** in body (bonus tickers)
    for m2 in re.finditer(r'\*\*\$([A-Z]{2,6})\*\*',chain_map):
        sym=m2.group(1)
        if sym not in results: results[sym]="T2"  # unlabelled = assume T2
    return results  # {ticker: tier}

def agent2_scorer(ticker,tier,theme_name,chain_context,key,f_key="",p_key=""):
    """Score a single ticker. Runs all quantitative + smart-money layers."""
    closes,vols,meta=yf_history(ticker,"6mo")
    price,chg=yf_price(ticker)
    if not price: return None

    # Quant
    qsc,qsigs=quant_score(closes,vols,meta,price)

    # Fundamentals
    summary=yf_summary(ticker)
    mcap_b=round((summary.get("mcap",0) or 0)/1e9,2)
    target=summary.get("target_mean")
    upside=round((target/price-1)*100,1) if target and price else None

    # Smart money
    ins13f=edgar_13f_signal(ticker)
    ins4  =edgar_insider_score(ticker)
    fh_net=finnhub_insider_net(ticker,f_key) if f_key else 0
    smart_money_raw=0.0
    if ins13f["count"]>=5: smart_money_raw+=1.0
    elif ins13f["count"]>=2: smart_money_raw+=0.5
    if ins4["cluster"]: smart_money_raw+=1.5
    elif ins4["filings"]>=2: smart_money_raw+=0.5
    if fh_net>=3: smart_money_raw+=1.0
    elif fh_net>=1: smart_money_raw+=0.5
    smart_money_raw=min(3.0,smart_money_raw)

    # News + options
    news_count_7d,headlines=news_count(ticker)
    pc=yf_options_pc(ticker)
    dod_m=dod_contracts(ticker)

    # Asymmetry score
    asym=calc_asymmetry_score(ticker,tier,smart_money_raw,qsc,mcap_b,dod_m,news_count_7d,pc)

    # AI enrichment
    ai_prompt=f"""TICKER: {ticker} | TIER: {tier} | THEME: {theme_name}
PRICE: ${price} ({chg:+.2f}%) | MCAP: ${mcap_b:.2f}B | UPSIDE vs analyst: {upside or 'N/A'}%
QUANT: RSI={qsigs.get('rsi',50)} MACD_hist={qsigs.get('macd_hist',0)} Vol_ratio={qsigs.get('vol_ratio',1)}×
SMART MONEY: 13F count={ins13f['count']}, Insider cluster={ins4['cluster']}, FH net={fh_net}
NEWS: {news_count_7d} articles/7d | P/C: {pc} | DoD contracts: ${dod_m:.0f}M
ASYMMETRY SCORE (calculated): {asym}/10
SUPPLY CHAIN CONTEXT: {chain_context[:300]}

In 3 sentences: (1) Is this a real asymmetric play or hype? (2) What catalyst reprices it? (3) What kills the thesis?
End with: VERDICT: [BUY/WATCH/SKIP] — [one sentence]"""

    ai_verdict=call_gemini_raw(AGENT2_SYSTEM,ai_prompt,key,temperature=0.2)

    return {
        "ticker":ticker,"tier":tier,"theme":theme_name,
        "price":price,"chg":chg,"mcap_b":mcap_b,
        "upside":upside,"asym_score":asym,
        "rsi":qsigs.get("rsi",50),"vol_ratio":qsigs.get("vol_ratio",1),
        "macd_hist":qsigs.get("macd_hist",0),
        "quant_score":qsc,
        "smart_money":round(smart_money_raw,1),
        "ins13f_count":ins13f["count"],"ins_cluster":ins4["cluster"],
        "fh_net":fh_net,"news_7d":news_count_7d,"pc_ratio":pc,"dod_m":dod_m,
        "headlines":headlines,"ai_verdict":ai_verdict,
        "chain_context":chain_context[:400],
    }

def agent3_ranker(all_candidates,key):
    """Rank all candidates. Return top 5 with AI justification."""
    if not all_candidates: return []
    # Pre-sort by asymmetry score
    sorted_cands=sorted(all_candidates,key=lambda x:x["asym_score"],reverse=True)[:20]
    table="\n".join([
        f"{i+1}. {c['ticker']} ({c['tier']}, {c['theme']}) — Asym {c['asym_score']}/10 | "
        f"MCAP ${c['mcap_b']:.1f}B | RSI {c['rsi']} | SM {c['smart_money']}/3 | "
        f"DoD ${c['dod_m']:.0f}M | Verdict: {c.get('ai_verdict','')[:80]}"
        for i,c in enumerate(sorted_cands)
    ])
    prompt=f"""Date: {datetime.now():%Y-%m-%d}
CANDIDATE POOL ({len(sorted_cands)} names pre-ranked by asymmetry score):
{table}

SELECTION CRITERIA:
- Tier 2/3 companies with genuine moat (not just momentum)
- Smart money accumulation NOT yet reflected in price
- Catalyst visible in next 30-90 days
- Downside risk is limited (not a binary bet)
- Avoid large-cap obvious plays (already priced in)

Select the TOP 5. For each, provide:
RANK: X
TICKER: [ticker]
WHY: [2 sentences — what the market is missing]
CATALYST: [specific upcoming event or trigger]
RISK: [single biggest risk]
---"""
    ranking=call_gemini_raw(AGENT3_SYSTEM,prompt,key,temperature=0.15)

    # Parse ranks and match to candidates
    top5=[]
    for block in ranking.split("---"):
        ticker_m=re.search(r'TICKER:\s*\$?([A-Z]{2,6})',block)
        if not ticker_m: continue
        sym=ticker_m.group(1).upper()
        # Find in candidates
        cand=next((c for c in sorted_cands if c["ticker"]==sym),None)
        if not cand: continue
        why_m=re.search(r'WHY:\s*(.+?)(?:CATALYST:|$)',block,re.DOTALL)
        cat_m=re.search(r'CATALYST:\s*(.+?)(?:RISK:|$)',block,re.DOTALL)
        risk_m=re.search(r'RISK:\s*(.+?)$',block,re.DOTALL)
        cand["why"]  =why_m.group(1).strip()[:200]  if why_m  else ""
        cand["catalyst"]=cat_m.group(1).strip()[:150] if cat_m  else ""
        cand["risk"] =risk_m.group(1).strip()[:120]  if risk_m else ""
        cand["rank"] =len(top5)+1
        top5.append(cand)
        if len(top5)==5: break

    # If parser got fewer than 5, fill from sorted candidates
    remaining=[c for c in sorted_cands if c["ticker"] not in [t["ticker"] for t in top5]]
    while len(top5)<5 and remaining:
        c=remaining.pop(0)
        c["rank"]=len(top5)+1; c["why"]="Highest asymmetry score in pipeline."
        c["catalyst"]="Monitor earnings + institutional filings."; c["risk"]="Thesis not yet confirmed by AI."
        top5.append(c)
    return top5[:5]

def agent4_writer(picks,theme_name,platform,key):
    """Generate content from top picks."""
    picks_str="\n".join([
        f"{p['rank']}. ${p['ticker']} — {p['tier']} — Asym {p['asym_score']}/10 — ${p['mcap_b']:.1f}B MCAP\n"
        f"   Why: {p.get('why','')}\n   Catalyst: {p.get('catalyst','')}"
        for p in picks[:5]])
    formats={
        "X Thread":   "Write a 7-tweet X/Twitter thread. Tweet 1: controversial hook. Tweets 2-6: one pick each with the key insight. Tweet 7: CTA + disclaimer. Max 280 chars per tweet.",
        "LinkedIn":   "Write a professional LinkedIn post (400-600 words). Bold opening line. 3 data points. Call out the asymmetric opportunity. End with a question to drive comments.",
        "Substack":   "Write a full Substack research note (800-1000 words). Title, intro, thesis, each pick with data, risks, conclusion. Professional tone with contrarian edge.",
        "Telegram":   "Write a Telegram channel post. Short, punchy. 5 picks in bullet format. Each: ticker, score, one-line thesis, catalyst. Under 300 words.",
    }
    prompt=f"""Date: {datetime.now():%Y-%m-%d}
THEME: {theme_name}
TOP PICKS FROM PIPELINE:
{picks_str}

FORMAT INSTRUCTIONS: {formats.get(platform,'Write a professional financial summary.')}

TONE: Institutional + contrarian edge. Never say "invest" or "buy" — say "position" or "opportunity".
Always include: specific tickers, asymmetry score, market cap, why it's overlooked.
End with: "Not financial advice. Do your own research." """
    return stream_gemini(AGENT4_SYSTEM,prompt,key,temperature=0.4)

def send_telegram(text,token,chat_id):
    if not token or not chat_id: return
    for chunk in [text[i:i+4000] for i in range(0,len(text),4000)]:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat_id,"text":chunk},timeout=10)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(selected_themes, key, f_key="", p_key="", progress_placeholder=None):
    """
    Runs the 4-agent pipeline across all selected themes.
    Returns top5 list.
    """
    all_candidates=[]
    total_steps=len(selected_themes)*2+2  # A1 per theme, A2 per ticker, A3, done
    step=0

    def upd(msg):
        nonlocal step; step+=1
        if progress_placeholder:
            pct=min(step/total_steps,0.98)
            progress_placeholder.progress(pct,msg)

    for theme in selected_themes:
        # AGENT 1 — Map supply chain
        upd(f"[A1] Mapping supply chain: {theme['name']}...")
        chain_map=agent1_researcher(theme,key)
        ticker_map=extract_tickers_from_map(chain_map)

        if not ticker_map:
            continue

        # AGENT 2 — Score each ticker (parallel)
        upd(f"[A2] Scoring {len(ticker_map)} tickers from {theme['name']}...")
        scored=[]
        lock=threading.Lock()

        def score_t(sym,tier):
            result=agent2_scorer(sym,tier,theme["name"],chain_map[:500],key,f_key,p_key)
            if result:
                with lock: scored.append(result)

        threads=[threading.Thread(target=score_t,args=(sym,tier),daemon=True)
                 for sym,tier in list(ticker_map.items())[:8]]  # cap at 8 per theme
        for th in threads: th.start()
        for th in threads: th.join(timeout=90)
        all_candidates.extend(scored)

    # AGENT 3 — Rank globally
    upd("[A3] Ranking top 5 from all candidates...")
    top5=agent3_ranker(all_candidates,key)
    if progress_placeholder: progress_placeholder.progress(1.0,"Pipeline complete ✓")
    return top5,all_candidates

# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def score_class(s):
    if s>=9: return "s9"
    if s>=7: return "s7"
    if s>=5: return "s5"
    return "slow"

def score_color_hex(s):
    if s>=9: return "#00ffaa"
    if s>=7: return "#4dffb4"
    if s>=5: return "#00aaff"
    return "#4a5568"

def tier_badge(tier):
    cls={"T1":"tier-t1","T2":"tier-t2","T3":"tier-t3","BOTTLENECK":"tier-bn","MOAT":"tier-t3"}.get(tier,"tier-t1")
    return f'<span class="tier-badge {cls}">{tier}</span>'

def render_top5_table(top5):
    """Render the main results table."""
    for i,pick in enumerate(top5,1):
        rank_cls=f"r{i}" if i<=5 else ""
        bar_pct=int(pick["asym_score"]*10)
        bar_color=score_color_hex(pick["asym_score"])
        chg=pick.get("chg",0) or 0
        chg_html=f'<span class="chg-up">▲ {chg:.2f}%</span>' if chg>=0 else f'<span class="chg-dn">▼ {abs(chg):.2f}%</span>'
        mcap=pick.get("mcap_b",0) or 0
        mcap_str=f"${mcap:.2f}B" if mcap>0 else "—"
        upside=pick.get("upside")
        upside_str=f'+{upside:.0f}%' if upside else "—"
        sm=pick.get("smart_money",0)
        sm_str="●●●" if sm>=2 else "●●" if sm>=1 else "●"
        sm_cls="sm-bullish" if sm>=1.5 else "sm-neutral"
        dod=pick.get("dod_m",0)
        cluster_icon="⬛" if pick.get("ins_cluster") else ""

        st.markdown(f"""
<div style="background:#030d08;border:1px solid #0d2818;border-left:{'3px solid #00ffaa' if i==1 else '1px solid #0d2818'};padding:16px 18px;margin:8px 0">
  <div style="display:flex;align-items:flex-start;gap:16px;flex-wrap:wrap">
    <div style="min-width:30px">
      <span class="rank-num {rank_cls}">#{i}</span>
    </div>
    <div style="flex:1;min-width:140px">
      <div class="ticker-cell">${pick['ticker']}</div>
      <div class="company-cell">{pick.get('theme','')}</div>
      <div style="margin-top:4px">{tier_badge(pick.get('tier','T2'))}</div>
    </div>
    <div style="text-align:center;min-width:60px">
      <div class="asym-score {score_class(pick['asym_score'])}">{pick['asym_score']}</div>
      <div style="font-size:0.58rem;color:#1a7a45;letter-spacing:1px;text-transform:uppercase">score</div>
      <div style="margin-top:4px"><div class="score-bar-bg"><div class="score-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div></div></div>
    </div>
    <div style="min-width:80px">
      <div style="font-size:0.9rem;font-weight:700;color:#c8fae0">${pick.get('price',0):,.2f}</div>
      <div>{chg_html}</div>
    </div>
    <div style="min-width:70px">
      <div style="font-size:0.78rem;color:#4dffb4">{mcap_str}</div>
      <div style="font-size:0.72rem;color:#1a7a45">mkt cap</div>
    </div>
    <div style="min-width:55px">
      <div style="font-size:0.82rem;color:{'#00ffaa' if upside and upside>0 else '#ff4444'}">{upside_str}</div>
      <div style="font-size:0.68rem;color:#1a7a45">analyst tgt</div>
    </div>
    <div style="min-width:60px">
      <span class="{sm_cls}" style="font-size:0.82rem">{sm_str}</span>
      <div style="font-size:0.68rem;color:#1a7a45">smart$  {cluster_icon}</div>
    </div>
  </div>
  <div style="margin-top:12px;padding-top:8px;border-top:1px solid #0d2818">
    <div style="font-size:0.78rem;color:#c8fae0;line-height:1.5">{pick.get('why','')}</div>
    <div style="font-size:0.72rem;color:#1a9963;margin-top:4px">⚡ {pick.get('catalyst','')}</div>
    <div style="font-size:0.7rem;color:#ff6b35;margin-top:2px">⚠ {pick.get('risk','')}</div>
    {f'<div style="font-size:0.68rem;color:#1a7a45;margin-top:4px">DoD contracts: ${dod:.0f}M | RSI: {pick.get("rsi",50)} | Vol: {pick.get("vol_ratio",1):.1f}×</div>' if dod>0 else ''}
  </div>
</div>""", unsafe_allow_html=True)

def render_mini_radar(pick):
    """Small SVG radar for a single pick."""
    labels=["Asymmetry","Quant","Smart$","Catalyst","Size Alpha"]
    max_vals=[10,3,3,2,2]
    vals=[
        pick.get("asym_score",0)/10*3,
        pick.get("quant_score",0),
        pick.get("smart_money",0),
        min(2.0,(1.0 if pick.get("dod_m",0)>10 else 0)+(0.5 if pick.get("news_7d",0)>3 else 0)+(0.5 if (pick.get("pc_ratio") or 1)<0.6 else 0)),
        (3-min(3,pick.get("mcap_b",10)/10*3)) if pick.get("mcap_b") else 1.5,
    ]
    n=5; cx=cy=70; r=50
    angles=[math.pi/2+2*math.pi*i/n for i in range(n)]
    norms=[min(vals[i]/max_vals[i],1.0) for i in range(n)]
    outer=" ".join([f"{cx+r*math.cos(a):.1f},{cy-r*math.sin(a):.1f}" for a in angles])
    score_pts=" ".join([f"{cx+r*norms[i]*math.cos(angles[i]):.1f},{cy-r*norms[i]*math.sin(angles[i]):.1f}" for i in range(n)])
    axis_lines="".join([f'<line x1="{cx}" y1="{cy}" x2="{cx+r*math.cos(a):.1f}" y2="{cy-r*math.sin(a):.1f}" stroke="#0d4a25" stroke-width="1"/>' for a in angles])
    label_els=""
    for i,(a,lbl) in enumerate(zip(angles,labels)):
        lx=cx+(r+14)*math.cos(a); ly=cy-(r+14)*math.sin(a)
        ta="middle" if abs(lx-cx)<8 else "end" if lx<cx else "start"
        label_els+=f'<text x="{lx:.1f}" y="{ly+3:.1f}" font-size="6" fill="#1a7a45" text-anchor="{ta}" font-family="Roboto Mono,monospace">{lbl[:7]}</text>'
    score=pick.get("asym_score",0); sc=score_color_hex(score)
    return f"""<svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg" style="max-width:140px">
<polygon points="{outer}" fill="none" stroke="#0d4a25" stroke-width="1"/>
{axis_lines}
<polygon points="{score_pts}" fill="{sc}" fill-opacity="0.2" stroke="{sc}" stroke-width="1.5"/>
{label_els}
<text x="{cx}" y="{cy+4}" font-size="16" font-weight="700" fill="{sc}" text-anchor="middle" font-family="Roboto Mono,monospace">{score}</text>
<text x="{cx}" y="{cy+14}" font-size="6" fill="#1a7a45" text-anchor="middle" font-family="Roboto Mono,monospace">/10</text>
</svg>"""

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

# ── HEADER ────────────────────────────────────────────────────────────────────
n_top=len(st.session_state.get("top5",[]))
last_str=st.session_state.get("last_run","Never")
if last_str and last_str!="Never": last_str=last_str[:16].replace("T"," ")

st.markdown(f"""
<div class="at-header">
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <div>
      <div class="at-title">🏦 ALPHA TERMINAL <span class="v6">v6</span></div>
      <div class="at-sub">Agentic Moonshot Pipeline · Supply Chain Intelligence · {datetime.now().strftime("%d %b %Y · %H:%M UTC")}</div>
    </div>
    <div class="at-status-row">
      <span class="at-badge badge-active">{'● LIVE' if gemini_key else '○ OFFLINE'}</span>
      <span class="at-badge badge-info">{n_top} PICKS LOADED</span>
      <span class="at-badge badge-warn">LAST: {last_str}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── TICKER RIBBON ─────────────────────────────────────────────────────────────
macro=get_macro()
ribbon=""
for lbl,(p,c) in macro.items():
    if p:
        cls="tup" if (c or 0)>=0 else "tdn"
        fmt=f"{p:,.0f}" if p>500 else f"{p:.2f}"
        sgn="+" if (c or 0)>=0 else ""
        ribbon+=f'<div class="titem"><span class="tlbl">{lbl}</span><span class="tprice">{fmt}</span><span class="{cls}">{sgn}{c:.2f}%</span></div>'
    else:
        ribbon+=f'<div class="titem"><span class="tlbl">{lbl}</span><span class="tprice">—</span></div>'
st.markdown(f'<div class="ticker-ribbon">{ribbon}</div>', unsafe_allow_html=True)

# ── TABS ───────────────────────────────────────────────────────────────────────
tab_scan, tab_results, tab_deep, tab_stress, tab_article = st.tabs([
    "  ⚡ Pipeline Scan  ",
    f"  🏆 Top 5 Picks ({n_top})  ",
    "  🔬 Deep Dive  ",
    "  💀 Stress-Run  ",
    "  📝 Article Generator  ",
])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — PIPELINE SCAN
# ══════════════════════════════════════════════════════════════════════════════
with tab_scan:
    st.markdown('<div class="scan-panel">', unsafe_allow_html=True)
    st.markdown('<span class="scan-label">Select Themes to Scan — Agent 1 maps each chain, Agent 2 scores every ticker</span>', unsafe_allow_html=True)

    # Build custom theme list
    all_themes=list(THEMES)
    if custom_themes.strip():
        for ct in custom_themes.split(","):
            ct=ct.strip()
            if ct:
                all_themes.append({"id":ct.lower().replace(" ","_"),"name":ct,"tags":[ct]})

    # Theme selection pills (multiselect via checkboxes in columns)
    selected_ids=[]
    cols=st.columns(4)
    for i,th in enumerate(all_themes):
        with cols[i%4]:
            if st.checkbox(th["name"], key=f"th_{th['id']}", value=(i<themes_to_scan)):
                selected_ids.append(th["id"])

    selected_themes=[t for t in all_themes if t["id"] in selected_ids][:themes_to_scan]
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:0.7rem;color:#1a7a45;margin:8px 0 12px">{len(selected_themes)} themes selected · ~{len(selected_themes)*5} tickers to score · ~{len(selected_themes)*3} min estimated</div>', unsafe_allow_html=True)

    run_col,info_col=st.columns([2,3])
    with run_col:
        run_btn=st.button("⚡  RUN WEEKLY MOONSHOT SCAN", type="primary", key="btn_run", use_container_width=True)
    with info_col:
        st.markdown("""<div style="font-size:0.68rem;color:#1a7a45;line-height:1.7">
Agent 1: Supply chain map (Gemini + Google Search) &nbsp;·&nbsp;
Agent 2: Score each ticker (quant + EDGAR + news) &nbsp;·&nbsp;
Agent 3: Global ranking → Top 5 &nbsp;·&nbsp;
All free APIs · Zero paid subscriptions required</div>""", unsafe_allow_html=True)

    if run_btn:
        if not gemini_key:
            st.warning("Add Gemini API key in sidebar. Free at aistudio.google.com/app/apikey")
            st.stop()
        if not selected_themes:
            st.warning("Select at least one theme.")
            st.stop()

        prog=st.progress(0,"Initialising pipeline...")
        agent_status=st.empty()
        agent_status.markdown(f"""
<div class="agent-row"><span class="agent-dot running"></span><span class="agent-name">Agent 1 — Researcher</span><span class="agent-detail">Mapping {len(selected_themes)} supply chains...</span></div>
<div class="agent-row"><span class="agent-dot waiting"></span><span class="agent-name">Agent 2 — Scorer</span><span class="agent-detail">Waiting...</span></div>
<div class="agent-row"><span class="agent-dot waiting"></span><span class="agent-name">Agent 3 — Ranker</span><span class="agent-detail">Waiting...</span></div>""", unsafe_allow_html=True)

        top5,all_cands=run_pipeline(selected_themes,gemini_key,finnhub_key,polygon_key,prog)

        agent_status.markdown(f"""
<div class="agent-row"><span class="agent-dot complete"></span><span class="agent-name">Agent 1 — Researcher</span><span class="agent-detail">✓ {len(selected_themes)} chains mapped</span></div>
<div class="agent-row"><span class="agent-dot complete"></span><span class="agent-name">Agent 2 — Scorer</span><span class="agent-detail">✓ {len(all_cands)} tickers scored</span></div>
<div class="agent-row"><span class="agent-dot complete"></span><span class="agent-name">Agent 3 — Ranker</span><span class="agent-detail">✓ Top {len(top5)} selected</span></div>""", unsafe_allow_html=True)

        st.session_state["top5"]=top5
        st.session_state["last_run"]=datetime.now().isoformat()
        st.session_state["all_candidates"]=all_cands

        # Telegram push
        if tg_token and tg_chat and top5:
            msg=f"🏦 ALPHA TERMINAL v6\n{datetime.now():%Y-%m-%d %H:%M}\n\nTOP {len(top5)} MOONSHOT PICKS:\n\n"
            for p in top5:
                msg+=f"#{p['rank']} ${p['ticker']} — {p['asym_score']}/10 — ${p.get('mcap_b',0):.1f}B\n{p.get('why','')[:100]}\n\n"
            send_telegram(msg,tg_token,tg_chat)

        prog.progress(1.0,"✓ Pipeline complete")
        st.rerun()

    # Auto-run
    if auto_run and not st.session_state.get("top5") and gemini_key:
        st.info("Auto-run enabled. Click 'RUN WEEKLY MOONSHOT SCAN' or disable auto-run in sidebar.")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — TOP 5 RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    top5=st.session_state.get("top5",[])
    if not top5:
        st.markdown("""<div style="background:#030710;border:1px solid #0d4a25;padding:24px;text-align:center;color:#1a7a45">
TERMINAL IDLE — Run the Pipeline Scan to surface this week's top asymmetric plays.</div>""", unsafe_allow_html=True)
    else:
        last=st.session_state.get("last_run","")
        avg_score=round(float(np.mean([p["asym_score"] for p in top5])),1)
        total_mcap=round(sum(p.get("mcap_b",0) or 0 for p in top5),1)
        sm_picks=sum(1 for p in top5 if p.get("smart_money",0)>=1.5)

        st.markdown(f"""
<div class="metric-row">
  <div class="metric-box"><span class="metric-lbl">Top picks</span><span class="metric-val">{len(top5)}</span></div>
  <div class="metric-box"><span class="metric-lbl">Avg asymmetry</span><span class="metric-val">{avg_score}/10</span></div>
  <div class="metric-box"><span class="metric-lbl">Total MCAP</span><span class="metric-val">${total_mcap:.0f}B</span></div>
  <div class="metric-box"><span class="metric-lbl">Smart $ confirmed</span><span class="metric-val">{sm_picks}</span></div>
  <div class="metric-box"><span class="metric-lbl">Scan date</span><span class="metric-val" style="font-size:0.8rem">{last[:10]}</span></div>
</div>""", unsafe_allow_html=True)

        st.markdown('<span class="sec-hdr">Top 5 Asymmetric Picks — This Week</span>', unsafe_allow_html=True)
        render_top5_table(top5)

        # Radar row
        st.markdown('<span class="sec-hdr">Asymmetry Radar — Signal Profile</span>', unsafe_allow_html=True)
        radar_cols=st.columns(len(top5))
        for i,(col,pick) in enumerate(zip(radar_cols,top5)):
            with col:
                st.markdown(f'<div style="text-align:center;color:#00ffaa;font-size:0.75rem;font-weight:700;margin-bottom:4px">${pick["ticker"]}</div>', unsafe_allow_html=True)
                st.markdown(render_mini_radar(pick), unsafe_allow_html=True)

        # News feed per pick
        st.markdown('<span class="sec-hdr">Live Intelligence Feed</span>', unsafe_allow_html=True)
        news_cols=st.columns(min(len(top5),5))
        for i,(col,pick) in enumerate(zip(news_cols,top5)):
            with col:
                st.markdown(f'<div style="font-size:0.72rem;font-weight:700;color:#00ffaa;margin-bottom:8px">${pick["ticker"]}</div>', unsafe_allow_html=True)
                for h in pick.get("headlines",[])[:4]:
                    title=h.get("title",""); src=h.get("source",""); link=h.get("link","")
                    st.markdown(f'<div class="news-card"><a href="{link}" target="_blank" class="news-title">{title}</a><span class="news-src">{src}</span></div>', unsafe_allow_html=True)

        # Export
        df=pd.DataFrame([{"Ticker":p["ticker"],"Theme":p["theme"],"Tier":p["tier"],
            "Score":p["asym_score"],"MCAP_B":p.get("mcap_b",""),"Price":p.get("price",""),
            "Upside%":p.get("upside",""),"RSI":p.get("rsi",""),"SmartMoney":p.get("smart_money",""),
            "DoD_M":p.get("dod_m",""),"Why":p.get("why",""),"Catalyst":p.get("catalyst","")} for p in top5])
        st.download_button("⬇ EXPORT CSV",data=df.to_csv(index=False),
            file_name=f"alpha_terminal_v6_{datetime.now():%Y%m%d}.csv",mime="text/csv",key="btn_exp_csv")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — DEEP DIVE (Agent 2 + chart on single ticker)
# ══════════════════════════════════════════════════════════════════════════════
with tab_deep:
    st.markdown('<span class="sec-hdr">Single Ticker Deep Dive — Full 8-Signal Analysis</span>', unsafe_allow_html=True)
    d1,d2,d3=st.columns([2,2,1])
    with d1: dd_sym=st.text_input("TICKER",placeholder="$NVDA · $AXTI · $RKLB",key="ti_dd",label_visibility="collapsed")
    with d2: dd_theme=st.text_input("THEME CONTEXT",placeholder="e.g. AI chip supply chain",key="ti_dd_theme",label_visibility="collapsed")
    with d3: dd_btn=st.button("SCAN",type="primary",key="btn_dd",use_container_width=True)

    if dd_btn and dd_sym.strip():
        if not gemini_key:
            st.warning("Add Gemini API key in sidebar.")
        else:
            t=dd_sym.strip().upper().replace("$","")
            ctx=dd_theme.strip() or "Direct analysis"
            with st.spinner(f"Running deep analysis on {t}..."):
                result=agent2_scorer(t,"T2",ctx,ctx,gemini_key,finnhub_key,polygon_key)
            if result:
                # Metrics
                st.markdown(f"""
<div class="metric-row">
  <div class="metric-box"><span class="metric-lbl">Asym Score</span><span class="metric-val">{result['asym_score']}/10</span></div>
  <div class="metric-box"><span class="metric-lbl">Price</span><span class="metric-val">${result['price']:,.2f}</span></div>
  <div class="metric-box"><span class="metric-lbl">MCAP</span><span class="metric-val">${result.get('mcap_b',0):.2f}B</span></div>
  <div class="metric-box"><span class="metric-lbl">RSI</span><span class="metric-val">{result['rsi']}</span></div>
  <div class="metric-box"><span class="metric-lbl">Vol Ratio</span><span class="metric-val">{result['vol_ratio']}×</span></div>
  <div class="metric-box"><span class="metric-lbl">Smart $</span><span class="metric-val">{result['smart_money']}/3</span></div>
  <div class="metric-box"><span class="metric-lbl">DoD Contracts</span><span class="metric-val">${result['dod_m']:.0f}M</span></div>
  <div class="metric-box"><span class="metric-lbl">News/7d</span><span class="metric-val">{result['news_7d']}</span></div>
</div>""", unsafe_allow_html=True)

                # Radar
                r1,r2=st.columns([1,2])
                with r1:
                    st.markdown(render_mini_radar(result),unsafe_allow_html=True)
                with r2:
                    st.markdown(f'<div class="article-card">{result.get("ai_verdict","")}</div>',unsafe_allow_html=True)

                # News
                headlines=result.get("headlines",[])
                if headlines:
                    st.markdown('<span class="sec-hdr">Live News</span>', unsafe_allow_html=True)
                    for h in headlines[:5]:
                        st.markdown(f'<div class="news-card"><a href="{h.get("link","")}" target="_blank" class="news-title">{h.get("title","")}</a><span class="news-src">{h.get("source","")}</span></div>', unsafe_allow_html=True)
            else:
                st.error(f"Could not fetch data for {t}. Check ticker symbol.")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — STRESS-RUN (v5 original mode — manual query, preserved)
# ══════════════════════════════════════════════════════════════════════════════
with tab_stress:
    st.markdown("""<div style="font-size:0.72rem;color:#1a7a45;margin-bottom:12px">
STRESS-RUN MODE — Original v5 manual scanner. Type a ticker ($NVDA) or theme (Solid State Electrolytes).
Gemini maps Tier 1/2/3 + suggests the asymmetric bet. Instant, single-query mode.
</div>""", unsafe_allow_html=True)

    s1,s2=st.columns([4,1])
    with s1:
        stress_input=st.text_input("RESEARCH TARGET",placeholder="e.g. 'Solid State Electrolytes' or '$NVDA'",
                                    key="ti_stress",label_visibility="collapsed")
    with s2:
        stress_btn=st.button("RUN STRESS-RUN",type="primary",key="btn_stress",use_container_width=True)

    if stress_btn and stress_input.strip():
        if not gemini_key:
            st.warning("Add Gemini API key in sidebar.")
        else:
            is_ticker=stress_input.strip().startswith("$")
            target=stress_input.strip().replace("$","").upper()

            if is_ticker:
                prompt=f"""STRESS-RUN ANALYSIS: {target} · Date: {datetime.now():%Y-%m-%d}
1. MACRO/MICRO: Live news + sentiment. What is the real market consensus vs narrative?
2. RESULTS: Latest quarterly — revenue, margins, guidance. Management tone: Hawkish or Dovish?
3. ASYMMETRIC BETS: Map the supply chain. Find the Tier 2/3 supplier that is a BETTER risk/reward than {target}.
4. SELF-CRITIQUE: What kills this thesis? What does smart money know that retail doesn't?
STRICT: End with 'TICKERS: {target}, [BET_1], [BET_2]'"""
            else:
                prompt=f"""SUPPLY CHAIN MAPPER: {stress_input} · Date: {datetime.now():%Y-%m-%d}
1. MAP: Tier 1, 2, 3 players. Who supplies what. Market caps.
2. BOTTLENECK: Who owns the critical IP, process, or raw material?
3. ASYMMETRIC PLAYS: 3 obscure public companies with genuine upside potential (not hype).
4. SMART MONEY LENS: Which of these names is institutional accumulation targeting?
STRICT: End with 'TICKERS: [T1], [T2], [T3]'"""

            with st.status(f"AGENT STRESS-TESTING: {stress_input}...", expanded=True) as sr:
                out=st.empty(); full=""
                for chunk in stream_gemini(AGENT1_SYSTEM,prompt,gemini_key,temperature=0.2):
                    full+=chunk; out.markdown(f'<div class="article-card">{full}</div>',unsafe_allow_html=True)
                sr.update(label="✓ Stress-run complete",state="complete")

            st.session_state["stress_result"]=full
            st.session_state["stress_target"]=stress_input

            # Extract tickers and get live data
            ticker_map=extract_tickers_from_map(full)
            if ticker_map:
                st.markdown('<span class="sec-hdr">Financial Workstation</span>', unsafe_allow_html=True)
                rows=[]
                for sym,tier in list(ticker_map.items())[:6]:
                    p,chg=yf_price(sym)
                    summary=yf_summary(sym)
                    mcap=round((summary.get("mcap",0) or 0)/1e9,2)
                    tgt=summary.get("target_mean")
                    upside=round((tgt/p-1)*100,1) if tgt and p else None
                    rows.append({"TICKER":sym,"TIER":tier,"PRICE":f"${p:,.2f}" if p else "—",
                                 "CHG%":f"{chg:+.2f}%" if chg else "—",
                                 "MCAP":f"${mcap:.2f}B" if mcap else "—",
                                 "ANALYST UPSIDE":f"{upside:+.1f}%" if upside else "—",
                                 "P/E":summary.get("forward_pe","—")})
                st.table(pd.DataFrame(rows))

                # News per ticker
                st.markdown('<span class="sec-hdr">Live Intelligence Feed</span>', unsafe_allow_html=True)
                ticker_list=list(ticker_map.keys())[:4]
                news_cols_sr=st.columns(len(ticker_list))
                for col,sym in zip(news_cols_sr,ticker_list):
                    with col:
                        st.markdown(f'<div style="font-size:0.72rem;font-weight:700;color:#00ffaa;margin-bottom:6px">${sym}</div>', unsafe_allow_html=True)
                        _,headlines=news_count(sym)
                        for h in headlines[:4]:
                            st.markdown(f'<div class="news-card"><a href="{h.get("link","")}" target="_blank" class="news-title">{h.get("title","")}</a><span class="news-src">{h.get("source","")}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — ARTICLE GENERATOR (Agent 4)
# ══════════════════════════════════════════════════════════════════════════════
with tab_article:
    st.markdown('<span class="sec-hdr">Agent 4 — One-Click Content Generator</span>', unsafe_allow_html=True)
    top5=st.session_state.get("top5",[])
    if not top5:
        st.markdown('<div style="background:#030710;border:1px solid #0d4a25;padding:18px;color:#1a7a45">Run the Pipeline Scan first to load picks for article generation.</div>', unsafe_allow_html=True)
    else:
        # Source selection
        a1,a2=st.columns([2,2])
        with a1:
            theme_labels=list(set(p["theme"] for p in top5))
            selected_theme_label=st.selectbox("Theme",["All Picks"]+theme_labels,key="sb_art_theme")
        with a2:
            platform=st.selectbox("Platform",["X Thread","LinkedIn","Substack","Telegram"],key="sb_art_platform")

        article_picks=top5 if selected_theme_label=="All Picks" else [p for p in top5 if p["theme"]==selected_theme_label]
        theme_name=selected_theme_label

        if st.button(f"⚡ GENERATE {platform.upper()} CONTENT",type="primary",key="btn_art"):
            if not gemini_key:
                st.warning("Add Gemini API key.")
            else:
                with st.status(f"Agent 4 writing {platform} content...",expanded=True) as art_s:
                    out=st.empty(); full=""
                    for chunk in agent4_writer(article_picks,theme_name,platform,gemini_key):
                        full+=chunk; out.markdown(f'<div class="article-card">{full}</div>',unsafe_allow_html=True)
                    art_s.update(label=f"✓ {platform} content ready",state="complete")
                st.session_state["article_cache"][platform]=full

                col1,col2=st.columns(2)
                with col1:
                    st.download_button(f"⬇ DOWNLOAD {platform}",data=full,
                        file_name=f"alpha_{platform.lower().replace(' ','_')}_{datetime.now():%Y%m%d_%H%M}.txt",
                        mime="text/plain",key=f"dl_art_{platform}")
                with col2:
                    if tg_token and tg_chat and platform=="Telegram":
                        if st.button("→ POST TO TELEGRAM",key="btn_tg_post",use_container_width=True):
                            send_telegram(full,tg_token,tg_chat)
                            st.success("Posted to Telegram channel.")

        # Show cached articles
        if st.session_state.get("article_cache"):
            with st.expander("📁 Previously generated content"):
                for pl,content in st.session_state["article_cache"].items():
                    st.markdown(f"**{pl}**")
                    st.markdown(f'<div class="article-card">{content[:400]}...</div>',unsafe_allow_html=True)

st.divider()
st.markdown(f'<div style="font-size:0.6rem;color:#0d4a25;text-align:center;letter-spacing:1.5px">ALPHA TERMINAL v6 · AGENTIC PIPELINE · GEMINI 2.5 FLASH + GOOGLE SEARCH GROUNDING · EDGAR · USASPENDING.GOV · NOT FINANCIAL ADVICE · {datetime.now():%Y}</div>', unsafe_allow_html=True)
