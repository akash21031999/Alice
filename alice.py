"""
Alice — AI Trading Research Agent
Inspired by OpenAlice (github.com/TraderAlice/OpenAlice)

Architecture translated from TypeScript/Node to Python/Streamlit:
  persona.default.md   → ALICE_PERSONA system prompt (configurable)
  engine.json          → sidebar config + session state
  brain/ (memory)      → st.session_state["brain"] + JSONL download
  analysis-kit/        → Python market data + indicator functions
  Guard pipeline       → pre-trade safety checker
  Git-like wallet      → stage → review → confirm workflow
  Cron/heartbeat       → auto-refresh with market check
  JSONL sessions       → conversation history stored in session state

Research-only mode — no live trade execution.
"""

import streamlit as st
st.set_page_config(
    page_title="Alice",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import requests, feedparser, json, time, re, hashlib, threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN — clean white, terminal-adjacent
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; font-style: normal !important; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewContainer"] > section > div,
.main, .main > div {
    background-color: #f9fafb !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #111827 !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}
[data-testid="stSidebar"] * { color: #374151 !important; font-style: normal !important; }
[data-testid="stSidebar"] strong { color: #111827 !important; font-weight: 600 !important; }
.block-container { padding: 1.2rem 2rem 3rem !important; max-width: 1400px !important; }
em, i { font-style: normal !important; }
strong, b { font-weight: 600 !important; color: #111827 !important; }
a { color: #2563eb !important; }

/* TOP BAR */
.alice-top {
    display: flex; align-items: center; gap: 14px;
    padding: 10px 0 14px; border-bottom: 1px solid #e5e7eb; margin-bottom: 18px;
}
.alice-avatar {
    width: 38px; height: 38px; border-radius: 10px;
    background: linear-gradient(135deg, #1e40af, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; font-weight: 800; color: #fff !important; flex-shrink: 0;
}
.alice-title { font-size: 1.15rem; font-weight: 800; color: #111827 !important; letter-spacing: -0.5px; }
.alice-sub   { font-size: 0.72rem; color: #6b7280 !important; margin-top: 1px; }
.alice-status-row { display: flex; gap: 12px; margin-left: auto; align-items: center; flex-wrap: wrap; }
.alice-pill {
    font-size: 0.68rem; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; border: 1px solid; white-space: nowrap;
}
.pill-green  { background: #f0fdf4; border-color: #86efac; color: #15803d !important; }
.pill-blue   { background: #eff6ff; border-color: #93c5fd; color: #1d4ed8 !important; }
.pill-amber  { background: #fffbeb; border-color: #fcd34d; color: #92400e !important; }
.pill-gray   { background: #f3f4f6; border-color: #d1d5db; color: #6b7280 !important; }

/* CHAT MESSAGES */
.chat-wrap { display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; }
.msg {
    display: flex; gap: 12px; align-items: flex-start; max-width: 100%;
}
.msg.user  { flex-direction: row-reverse; }
.msg-avatar {
    width: 32px; height: 32px; border-radius: 9px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.82rem; font-weight: 700;
}
.msg-avatar.alice { background: linear-gradient(135deg,#1e40af,#7c3aed); color:#fff !important; }
.msg-avatar.user  { background: #f3f4f6; color: #374151 !important; }

.msg-bubble {
    padding: 12px 16px; border-radius: 12px; max-width: 85%;
    font-size: 0.9rem; line-height: 1.7; word-wrap: break-word;
    overflow-wrap: break-word;
}
.msg-bubble.alice {
    background: #ffffff; border: 1px solid #e5e7eb;
    border-bottom-left-radius: 4px; color: #1f2937 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.msg-bubble.user {
    background: #2563eb; color: #ffffff !important;
    border-bottom-right-radius: 4px;
}
.msg-bubble.user * { color: #ffffff !important; }
.msg-bubble.system {
    background: #fafafa; border: 1px dashed #e5e7eb;
    color: #6b7280 !important; font-size: 0.82rem; max-width: 100%;
    border-radius: 8px;
}
.msg-meta { font-size: 0.65rem; color: #9ca3af !important; margin-top: 4px; }

/* REASONING BLOCK */
.reasoning-block {
    background: #f8fafc; border: 1px solid #e5e7eb;
    border-left: 3px solid #7c3aed;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
    font-size: 0.82rem; color: #374151 !important;
}
.reasoning-label {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #7c3aed !important; margin-bottom: 6px; display: block;
}

/* TRADE STAGE (git-like wallet) */
.stage-card {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 16px 20px; margin: 8px 0; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.stage-header {
    display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
    padding-bottom: 10px; border-bottom: 1px solid #f3f4f6;
}
.stage-label {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 2px 8px; border-radius: 4px;
}
.stage-staged   { background: #fffbeb; color: #92400e !important; }
.stage-reviewed { background: #eff6ff; color: #1d4ed8 !important; }
.stage-rejected { background: #fff1f2; color: #9f1239 !important; }

.stage-ticker { font-size: 1.1rem; font-weight: 800; color: #111827 !important; font-family: 'JetBrains Mono', monospace; }
.stage-row    { display: flex; gap: 20px; flex-wrap: wrap; margin: 8px 0; }
.stage-item   { }
.stage-lbl    { font-size: 0.6rem; color: #9ca3af !important; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 2px; font-weight: 600; }
.stage-val    { font-size: 0.9rem; font-weight: 700; color: #111827 !important; font-family: 'JetBrains Mono', monospace; }
.stage-val.g  { color: #16a34a !important; }
.stage-val.r  { color: #dc2626 !important; }
.stage-val.b  { color: #2563eb !important; }

/* GUARD RESULT */
.guard-pass { background:#f0fdf4; border:1px solid #86efac; border-radius:7px; padding:10px 14px; font-size:0.82rem; color:#15803d !important; }
.guard-warn { background:#fffbeb; border:1px solid #fde68a; border-radius:7px; padding:10px 14px; font-size:0.82rem; color:#92400e !important; }
.guard-fail { background:#fff1f2; border:1px solid #fca5a5; border-radius:7px; padding:10px 14px; font-size:0.82rem; color:#991b1b !important; }

/* BRAIN / MEMORY */
.brain-card {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 14px 18px; margin: 6px 0;
}
.brain-type { font-size: 0.62rem; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #9ca3af !important; margin-bottom: 4px; display: block; }
.brain-text { font-size: 0.85rem; color: #1f2937 !important; line-height: 1.55; }
.brain-ts   { font-size: 0.65rem; color: #d1d5db !important; margin-top: 5px; display: block; }

/* MACRO STRIP */
.macro-strip { display:flex; gap:6px; margin-bottom:16px; overflow-x:auto; padding-bottom:2px; }
.macro-strip::-webkit-scrollbar { height:3px; }
.macro-strip::-webkit-scrollbar-thumb { background:#d1d5db; border-radius:2px; }
.mbox { flex:1; min-width:80px; background:#ffffff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; text-align:center; flex-shrink:0; }
.mlbl   { font-size:0.57rem; color:#9ca3af !important; text-transform:uppercase; letter-spacing:1.2px; display:block; margin-bottom:2px; font-weight:600; }
.mprice { font-size:0.9rem; font-weight:700; color:#111827 !important; font-family:'JetBrains Mono',monospace; display:block; }
.up  { color:#16a34a !important; font-size:0.65rem; font-weight:600; }
.dn  { color:#dc2626 !important; font-size:0.65rem; font-weight:600; }
.fl  { color:#9ca3af !important; font-size:0.65rem; }

/* HEARTBEAT */
.heartbeat {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 14px; background: #ffffff; border: 1px solid #e5e7eb;
    border-radius: 8px; margin-bottom: 14px; font-size: 0.75rem;
}
.hb-dot { width:8px; height:8px; border-radius:50%; background:#16a34a; flex-shrink:0; animation: hbpulse 2s infinite; }
@keyframes hbpulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.hb-label { color: #374151 !important; font-weight: 500; }
.hb-time  { color: #9ca3af !important; margin-left: auto; font-family:'JetBrains Mono',monospace; }

/* SECTION LABEL */
.mm-label {
    font-size:0.62rem; font-weight:700; letter-spacing:1.8px; text-transform:uppercase;
    color:#9ca3af !important; border-bottom:1px solid #e5e7eb; padding-bottom:6px; margin:18px 0 12px; display:block;
}

/* INPUTS */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background:#ffffff !important; border:1.5px solid #d1d5db !important;
    border-radius:8px !important; color:#111827 !important; font-size:0.9rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color:#2563eb !important; box-shadow:0 0 0 3px rgba(37,99,235,0.1) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background:#ffffff !important; border:1.5px solid #d1d5db !important; border-radius:8px !important;
}
div.stButton > button { border-radius:8px !important; font-weight:600 !important; font-size:0.85rem !important; }
div.stButton > button[kind="primary"] { background:#2563eb !important; border:1px solid #2563eb !important; color:#fff !important; }
div.stButton > button[kind="primary"]:hover { background:#1d4ed8 !important; }

/* MARKDOWN */
div[data-testid="stMarkdownContainer"] * { font-style:normal !important; }
div[data-testid="stMarkdownContainer"] em { font-style:normal !important; color:#374151 !important; }
div[data-testid="stMarkdownContainer"] p  { color:#374151 !important; line-height:1.75 !important; margin:6px 0 !important; }
div[data-testid="stMarkdownContainer"] li { color:#374151 !important; line-height:1.65 !important; margin:3px 0 !important; }
div[data-testid="stMarkdownContainer"] strong { color:#111827 !important; font-weight:700 !important; }
div[data-testid="stMarkdownContainer"] h2 { color:#111827 !important; font-weight:700 !important; border-bottom:1px solid #f3f4f6 !important; padding-bottom:4px !important; }
div[data-testid="stMarkdownContainer"] h3 { color:#1e40af !important; font-weight:700 !important; }
div[data-testid="stMarkdownContainer"] code { background:#f3f4f6 !important; color:#1f2937 !important; padding:1px 5px !important; border-radius:4px !important; font-size:0.84em !important; }
div[data-testid="stMarkdownContainer"] table { display:block !important; overflow-x:auto !important; border-collapse:collapse !important; width:100% !important; }
div[data-testid="stMarkdownContainer"] th { background:#f3f4f6 !important; color:#111827 !important; padding:8px 12px !important; border:1px solid #e5e7eb !important; font-weight:600 !important; }
div[data-testid="stMarkdownContainer"] td { padding:7px 12px !important; border:1px solid #e5e7eb !important; color:#374151 !important; }
div[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#f9fafb !important; }

/* TABS */
[data-testid="stTabs"] [role="tablist"] { border-bottom:2px solid #e5e7eb !important; }
[data-testid="stTabs"] button { font-size:0.8rem !important; font-weight:500 !important; color:#6b7280 !important; padding:8px 16px !important; border-bottom:2px solid transparent !important; border-radius:0 !important; background:transparent !important; margin-bottom:-2px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#111827 !important; font-weight:700 !important; border-bottom:2px solid #2563eb !important; }
[data-testid="stMetricValue"] { color:#111827 !important; font-weight:700 !important; }
hr { border:none !important; border-top:1px solid #e5e7eb !important; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-thumb { background:#d1d5db; border-radius:3px; }

@media (max-width:768px) {
    .block-container { padding:0.8rem 0.9rem 2rem !important; }
    .msg-bubble { max-width:94%; }
    .stage-row { gap:12px; }
    .alice-status-row { display:none; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  ALICE PERSONA — inspired by OpenAlice persona.default.md
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_PERSONA = """You are Alice, an AI trading research agent.

IDENTITY:
You are methodical, precise, and honest about uncertainty. You think like a quant analyst
with the communication style of a thoughtful portfolio manager. You never guess — if you
don't know something, you say so and use web search to find it.

REASONING STYLE (inspired by OpenAlice):
Before every analysis, you think step by step:
1. What is the user actually asking?
2. What data do I have? What data do I need?
3. What are the bull and bear cases?
4. What signals are stacking vs conflicting?
5. What is my conviction level and why?

CORE PRINCIPLES:
- Every trade idea needs a catalyst, not just a pattern
- Risk management is non-negotiable — always state stop loss and max risk
- Correlations matter — if you already own NVDA, buying AMD is not diversification
- Regime matters — a great stock in the wrong macro regime is still a bad trade
- Insider buying + technical setup + macro tailwind = high conviction stacking

COMMUNICATION:
- Be specific — "$145.20 entry, $162 target, $138 stop" not "it looks interesting"
- Show your reasoning — explain WHY, not just WHAT
- Flag risks prominently — a 3× return with a 90% loss probability is not a good trade
- Use live web search for current data — never guess prices or recent events

MEMORY (Brain):
You maintain a brain — a persistent set of notes about the user's portfolio,
preferences, and previous analyses. Reference it when relevant.

FORMAT:
When analysing a stock or trade, always structure as:
## Thesis
## Signal Stack
## Entry / Target / Stop
## Risk Factors
## Conviction: [LOW/MEDIUM/HIGH] — [one sentence why]"""

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE — mirrors OpenAlice's file-driven state
# ══════════════════════════════════════════════════════════════════════════════
DEFAULTS = {
    "messages":       [],        # conversation history (JSONL equivalent)
    "brain":          [],        # persistent memory entries
    "staged_ideas":   [],        # git-like stage area
    "heartbeat_ts":   None,      # last heartbeat timestamp
    "heartbeat_data": None,      # last heartbeat result
    "persona":        DEFAULT_PERSONA,
    "emotion":        "focused", # cognitive state
    "session_id":     hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
    "macro_cache":    {},
    "macro_ts":       None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — config (engine.json equivalent)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("**◇ Alice Config**")
    st.divider()

    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...",
                               key="si_gemini", help="Free · aistudio.google.com/app/apikey")
    tg_token   = st.text_input("Telegram Token", type="password", placeholder="optional", key="si_tg")
    tg_chat    = st.text_input("Telegram Chat ID", placeholder="optional", key="si_tgchat")

    st.divider()
    st.markdown("**Persona** *(persona.md equivalent)*")
    with st.expander("Edit Alice's persona"):
        persona_edit = st.text_area("Persona", value=st.session_state["persona"],
                                    height=200, key="ta_persona")
        if st.button("Save persona", key="btn_save_persona"):
            st.session_state["persona"] = persona_edit
            _msg = {"role":"system","content":f"[Persona updated at {datetime.now():%H:%M}]",
                    "ts": datetime.now().isoformat()}
            st.session_state["brain"].append({"type":"config","text":"Persona updated","ts":datetime.now().isoformat()})
            st.success("Persona saved")

    st.divider()
    st.markdown("**Engine** *(engine.json equivalent)*")
    heartbeat_on  = st.checkbox("Heartbeat enabled", value=True, key="cb_hb")
    hb_interval   = st.selectbox("Check interval", ["30 min","60 min","4 hours","Manual"], key="sb_hbint")
    show_reasoning= st.checkbox("Show reasoning", value=True, key="cb_reason")
    max_memory    = st.slider("Max brain entries", 10, 100, 50, key="sl_maxmem")

    st.divider()
    st.markdown("**Guard** *(safety rules)*")
    guard_max_concentration = st.slider("Max single position %", 5, 50, 20, key="sl_guard_conc")
    guard_min_rr   = st.slider("Min risk/reward", 1.0, 5.0, 1.5, 0.1, key="sl_guard_rr")
    guard_watchlist= st.text_input("Allowed symbols (blank = all)", placeholder="NVDA,TSLA,BTC...", key="ti_guard_wl")

    st.divider()
    dot = "🟢" if gemini_key else "🔴"
    st.markdown(f'<span style="font-size:0.78rem">{dot} Gemini &nbsp; {"🟢" if tg_token else "⚫"} Telegram</span>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear chat", key="btn_clr_chat", use_container_width=True):
            st.session_state["messages"] = []
            st.rerun()
    with col2:
        if st.button("Clear brain", key="btn_clr_brain", use_container_width=True):
            st.session_state["brain"] = []
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  DATA LAYER — analysis-kit equivalent
# ══════════════════════════════════════════════════════════════════════════════
YF = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Accept":"application/json"}

@st.cache_data(ttl=120, show_spinner=False)
def yf_price(sym):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d",
                         headers=YF, timeout=6)
        c = [x for x in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x]
        return (round(c[-1],2), round((c[-1]/c[-2]-1)*100,2)) if len(c)>=2 else (None,None)
    except: return None, None

@st.cache_data(ttl=300, show_spinner=False)
def yf_history(sym, rng="6mo"):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range={rng}",
                         headers=YF, timeout=8)
        d = r.json()["chart"]["result"][0]
        closes = [c for c in d["indicators"]["quote"][0]["close"] if c is not None]
        vols   = [v for v in d["indicators"]["quote"][0].get("volume",[]) if v is not None]
        return closes, vols, d.get("meta",{})
    except: return [], [], {}

@st.cache_data(ttl=300, show_spinner=False)
def get_macro():
    syms = {"SPX":"%5EGSPC","VIX":"%5EVIX","10Y":"%5ETNX","DXY":"DX-Y.NYB",
            "Gold":"GC%3DF","Oil":"CL%3DF"}
    out  = {lbl: yf_price(sym) for lbl,sym in syms.items()}
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
            params={"ids":"bitcoin","vs_currencies":"usd","include_24hr_change":"true"},
            timeout=5, headers={"User-Agent":"Alice/1.0"})
        d = r.json()["bitcoin"]
        out["BTC"] = (round(d["usd"],0), round(d["usd_24h_change"],2))
    except: out["BTC"] = (None,None)
    return out

@st.cache_data(ttl=600, show_spinner=False)
def get_news(query, n=6):
    try:
        url  = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        from feedparser import parse
        feed = parse(url)
        return [{"title":e.get("title",""),"source":e.get("source",{}).get("title",""),
                 "link":e.get("link","")} for e in feed.entries[:n]]
    except: return []

# ── Quantitative indicators ────────────────────────────────────────────────────
def calc_rsi(closes, n=14):
    if len(closes)<n+1: return 50.0
    a=np.array(closes,dtype=float); d=np.diff(a)
    g=np.where(d>0,d,0.); l=np.where(d<0,-d,0.)
    return round(float(100-100/(1+np.mean(g[-n:])/(np.mean(l[-n:])+1e-9))),1)

def calc_macd(closes):
    if len(closes)<35: return None,None,None
    s=pd.Series(closes,dtype=float)
    m=s.ewm(span=12,adjust=False).mean()-s.ewm(span=26,adjust=False).mean()
    sig=m.ewm(span=9,adjust=False).mean()
    return round(float(m.iloc[-1]),3),round(float(sig.iloc[-1]),3),round(float((m-sig).iloc[-1]),3)

def calc_bb(closes, n=20):
    if len(closes)<n: return None,None,None
    arr=np.array(closes[-n:],dtype=float)
    return round(np.mean(arr)+2*np.std(arr),2),round(np.mean(arr),2),round(np.mean(arr)-2*np.std(arr),2)

def vol_ratio(vols, n=20):
    if len(vols)<n+1 or not vols[-1]: return None
    return round(vols[-1]/max(np.mean(vols[-n-1:-1]),1),2)

def analyse_ticker(sym):
    """Full technical snapshot for a ticker — returns structured dict."""
    closes, vols, meta = yf_history(sym, "1y")
    price, chg = yf_price(sym)
    if not closes or not price:
        return None
    rsi      = calc_rsi(closes)
    ml,ms,mh = calc_macd(closes)
    bu,bm,bl = calc_bb(closes)
    vr       = vol_ratio(vols)
    w52h     = meta.get("fiftyTwoWeekHigh",0) or 0
    w52l     = meta.get("fiftyTwoWeekLow",0)  or 0
    ma50     = round(float(np.mean(closes[-50:])),2) if len(closes)>=50 else None
    ma200    = round(float(np.mean(closes[-200:])),2) if len(closes)>=200 else None
    m1       = round((closes[-1]/closes[-22]-1)*100,2) if len(closes)>=22 else None
    m5       = round((closes[-1]/closes[-5]-1)*100,2)  if len(closes)>=5  else None

    # Entry / target / stop heuristics
    atr = None
    if len(closes)>=15:
        diffs = [abs(closes[i]-closes[i-1]) for i in range(1,min(15,len(closes)))]
        atr   = round(float(np.mean(diffs)),2)
    entry  = round(price*0.998,2)
    stop   = round(max(price*0.89, price-3*(atr or price*0.05)),2)
    target = round(price*1.18,2)
    upside = round((target/price-1)*100,1)
    dn     = round((stop/price-1)*100,1)
    rr     = round(upside/abs(dn),2) if dn<0 else 0

    return {
        "ticker":sym,"price":price,"chg":chg,
        "rsi":rsi,"macd":ml,"macd_sig":ms,"macd_hist":mh,
        "bb_upper":bu,"bb_mid":bm,"bb_lower":bl,
        "vol_ratio":vr,"ma50":ma50,"ma200":ma200,
        "w52h":w52h,"w52l":w52l,"m1":m1,"m5":m5,
        "entry":entry,"target":target,"stop":stop,
        "upside":upside,"downside":dn,"rr":rr,
    }

# ══════════════════════════════════════════════════════════════════════════════
#  GUARD PIPELINE — pre-trade safety checks (from OpenAlice Guard)
# ══════════════════════════════════════════════════════════════════════════════
def run_guard(idea):
    """
    Safety checks before staging a trade idea.
    Returns (passed: bool, checks: list[dict])
    """
    checks = []
    allowed_syms = [s.strip().upper() for s in guard_watchlist.split(",")] if guard_watchlist.strip() else []

    # 1. Symbol whitelist
    if allowed_syms and idea.get("ticker","").upper() not in allowed_syms:
        checks.append({"name":"Symbol whitelist","status":"FAIL",
                        "msg":f"{idea['ticker']} not in allowed list: {', '.join(allowed_syms)}"})
    else:
        checks.append({"name":"Symbol whitelist","status":"PASS","msg":"Symbol allowed"})

    # 2. Risk/reward
    rr = idea.get("rr", 0)
    if rr < guard_min_rr:
        checks.append({"name":"Risk/Reward","status":"WARN",
                        "msg":f"R/R {rr}× is below minimum {guard_min_rr}×"})
    else:
        checks.append({"name":"Risk/Reward","status":"PASS","msg":f"R/R {rr}× ≥ {guard_min_rr}×"})

    # 3. Stop loss present
    if not idea.get("stop"):
        checks.append({"name":"Stop loss","status":"FAIL","msg":"No stop loss defined"})
    else:
        checks.append({"name":"Stop loss","status":"PASS","msg":f"Stop defined at ${idea.get('stop')}"})

    # 4. RSI overbought check
    rsi = idea.get("rsi", 50)
    if rsi and rsi > 75:
        checks.append({"name":"RSI overbought","status":"WARN",
                        "msg":f"RSI {rsi} — entering at overbought level"})
    else:
        checks.append({"name":"RSI overbought","status":"PASS","msg":f"RSI {rsi} — acceptable entry"})

    # 5. Downside > 15%
    dn = idea.get("downside", 0)
    if dn and dn < -15:
        checks.append({"name":"Max drawdown","status":"WARN",
                        "msg":f"Stop loss implies {dn:.1f}% drawdown — consider tighter stop"})
    else:
        checks.append({"name":"Max drawdown","status":"PASS","msg":"Drawdown within acceptable range"})

    # 6. Duplicate check (already staged)
    staged_tickers = [s["ticker"] for s in st.session_state.get("staged_ideas",[])]
    if idea.get("ticker") in staged_tickers:
        checks.append({"name":"Duplicate stage","status":"WARN",
                        "msg":f"{idea['ticker']} already in staging area"})
    else:
        checks.append({"name":"Duplicate stage","status":"PASS","msg":"Not a duplicate"})

    passed = not any(c["status"]=="FAIL" for c in checks)
    return passed, checks

# ══════════════════════════════════════════════════════════════════════════════
#  BRAIN — persistent memory (brain/ equivalent)
# ══════════════════════════════════════════════════════════════════════════════
def add_memory(mem_type, text):
    """Add an entry to Alice's brain memory."""
    entry = {"type":mem_type,"text":text,"ts":datetime.now().isoformat()}
    st.session_state["brain"].append(entry)
    # Trim to max
    if len(st.session_state["brain"]) > max_memory:
        st.session_state["brain"] = st.session_state["brain"][-max_memory:]

def get_brain_context(n=10):
    """Get recent brain entries as context string."""
    recent = st.session_state["brain"][-n:]
    if not recent: return "No prior memory."
    return "\n".join([f"[{e['type'].upper()} {e['ts'][:10]}] {e['text']}" for e in recent])

def export_jsonl():
    """Export conversation as JSONL (OpenAlice sessions format)."""
    lines = []
    for msg in st.session_state["messages"]:
        lines.append(json.dumps(msg))
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
#  HEARTBEAT — periodic market check (heartbeat.json equivalent)
# ══════════════════════════════════════════════════════════════════════════════
HB_INTERVALS = {"30 min":1800,"60 min":3600,"4 hours":14400,"Manual":999999}
HB_SECS = HB_INTERVALS.get(hb_interval, 3600)

def should_heartbeat():
    last = st.session_state.get("heartbeat_ts")
    if not last or not heartbeat_on: return False
    try:
        elapsed = (datetime.now()-datetime.fromisoformat(last)).total_seconds()
        return elapsed > HB_SECS
    except: return False

def run_heartbeat(key):
    """
    Periodic market health check — mirrors OpenAlice heartbeat.default.md logic.
    Returns a brief structured report.
    """
    macro = get_macro()
    macro_str = " | ".join([f"{k}:{v[0]}({'+' if (v[1] or 0)>=0 else ''}{v[1]:.1f}%)"
                             for k,v in macro.items() if v[0]])
    brain_ctx = get_brain_context(5)
    news = get_news("stock market today 2026",4)
    news_str = "\n".join([f"• {n['title']}" for n in news])

    prompt = f"""Date: {datetime.now():%Y-%m-%d %H:%M}

LIVE MACRO: {macro_str}
LATEST NEWS:
{news_str}

RECENT MEMORY:
{brain_ctx}

Run a brief heartbeat check (max 150 words):
1. MARKET STATUS: current regime in one sentence
2. KEY ALERT: anything unusual or actionable right now?
3. WATCHLIST CHECK: any of my previously discussed positions need attention?
4. EMOTIONAL STATE: your assessment of market sentiment (one word + one sentence)

End with: HEARTBEAT_OK if nothing urgent, or CHAT_YES: [topic] if something needs discussion."""

    return call_gemini(st.session_state["persona"], prompt, key)

# ══════════════════════════════════════════════════════════════════════════════
#  GEMINI ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def call_gemini(system, user, key):
    if not key: return "[No API key — add in sidebar]"
    try:
        client = genai.Client(api_key=key)
        srch   = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[srch], temperature=0.3, system_instruction=system)
        return client.models.generate_content(model="gemini-2.5-flash",contents=user,config=config).text
    except Exception as e: return f"[API error: {e}]"

def stream_gemini(system, user, key):
    if not key: yield "⚠️ Add Gemini API key in sidebar."; return
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.3),
            contents=user)
        for chunk in resp:
            if chunk.text: yield chunk.text
    except Exception as e: yield f"\n❌ {e}"

def send_telegram(text, token, chat_id):
    if not token or not chat_id: return
    for chunk in [text[i:i+4000] for i in range(0,len(text),4000)]:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                         json={"chat_id":chat_id,"text":chunk},timeout=10)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  ALICE RESPONSE ENGINE — the core reasoning loop
# ══════════════════════════════════════════════════════════════════════════════
def build_context(user_msg):
    """Build full context for Alice's response."""
    # Detect ticker mentions
    tickers = re.findall(r'\b([A-Z]{1,5})\b', user_msg.upper())
    common_words = {"THE","AND","FOR","ARE","BUT","NOT","YOU","ALL","CAN","HAS",
                    "HER","WAS","ONE","OUR","OUT","IF","WHO","WHY","HOW","WHAT",
                    "WHEN","TELL","ME","MY","DO","I","A","IN","ON","AT","IS","IT",
                    "TO","BE","AS","AN","OF","OR","BY","SO","UP","VS","BUY","SELL",
                    "RSI","DCF","PE","EPS","ETF","IPO","CEO","CFO","AI","FED","US"}
    tickers = [t for t in tickers if t not in common_words and len(t)>=2][:3]

    context_parts = [f"Date: {datetime.now():%Y-%m-%d %H:%M}"]

    # Live data for mentioned tickers
    ticker_data = {}
    for t in tickers[:3]:
        data = analyse_ticker(t)
        if data:
            ticker_data[t] = data
            context_parts.append(
                f"\nLIVE DATA — {t}: Price=${data['price']} ({data['chg']:+.2f}%) | "
                f"RSI={data['rsi']} | MACD={data['macd']} vs {data['macd_sig']} | "
                f"1M={data.get('m1',0):+.1f}% | Vol ratio={data['vol_ratio']}× | "
                f"52W H/L=${data['w52h']}/${data['w52l']} | "
                f"MA50=${data['ma50']} MA200=${data['ma200']}"
            )
            news = get_news(f"{t} stock news 2026", 4)
            if news:
                context_parts.append(f"RECENT NEWS — {t}:")
                for n in news[:3]:
                    context_parts.append(f"  • {n['title']}")

    # Macro
    macro = get_macro()
    macro_str = " | ".join([f"{k}:{v[0]}({'+' if (v[1] or 0)>=0 else ''}{v[1]:.2f}%)"
                             for k,v in macro.items() if v[0]])
    context_parts.append(f"\nLIVE MACRO: {macro_str}")

    # Brain memory
    brain_ctx = get_brain_context(8)
    context_parts.append(f"\nMEMORY (brain):\n{brain_ctx}")

    # Recent conversation (last 6 turns)
    recent_msgs = st.session_state["messages"][-6:]
    if recent_msgs:
        conv = "\n".join([f"{'Alice' if m['role']=='assistant' else 'User'}: {m['content'][:300]}"
                          for m in recent_msgs])
        context_parts.append(f"\nRECENT CONVERSATION:\n{conv}")

    return "\n".join(context_parts), ticker_data

def alice_respond(user_msg, key, show_reason=True):
    """
    Main response generator — streams Alice's reply.
    Also extracts trade ideas and stages them.
    """
    context, ticker_data = build_context(user_msg)

    # Reasoning prefix (show_reasoning toggle)
    reasoning_prompt = ""
    if show_reason:
        reasoning_prompt = """Before answering, briefly show your reasoning in a
REASONING block (2-3 bullet points max) starting with «REASONING:».
Then give your full response. The REASONING block should show how you're
approaching the problem, what data you're using, and your confidence level."""

    full_prompt = f"""{context}

USER MESSAGE: {user_msg}

{reasoning_prompt}

Remember to:
- Use live web search for current data and recent news
- Reference memory/brain context when relevant
- If the user asks about a specific stock, provide the full technical analysis
- If you identify a high-conviction trade idea, end with:
  STAGE_IDEA: {{"ticker":"X","entry":0,"target":0,"stop":0,"thesis":"..."}}"""

    return stream_gemini(st.session_state["persona"], full_prompt, key), ticker_data

# ══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
macro = get_macro()
n_staged = len(st.session_state.get("staged_ideas",[]))
n_mem    = len(st.session_state.get("brain",[]))
emotion  = st.session_state.get("emotion","focused")
last_hb  = st.session_state.get("heartbeat_ts","Never")
last_hb_str = last_hb[:16].replace("T"," ") if last_hb and last_hb != "Never" else "Never"

st.markdown(f"""
<div class="alice-top">
  <div class="alice-avatar">A</div>
  <div>
    <div class="alice-title">Alice</div>
    <div class="alice-sub">AI Trading Research Agent &nbsp;·&nbsp; {datetime.now().strftime("%d %b %Y · %H:%M UTC")}</div>
  </div>
  <div class="alice-status-row">
    <span class="alice-pill {'pill-green' if gemini_key else 'pill-gray'}">
      {'● AI Active' if gemini_key else '○ No API Key'}
    </span>
    <span class="alice-pill pill-blue">{n_staged} staged</span>
    <span class="alice-pill pill-amber">{n_mem} memories</span>
    <span class="alice-pill pill-gray">♡ {emotion}</span>
    <span class="alice-pill pill-gray">hb: {last_hb_str}</span>
  </div>
</div>""", unsafe_allow_html=True)

# Macro strip
strip = ""
for lbl,(p,c) in macro.items():
    if p:
        cls = "up" if (c or 0)>=0 else "dn"
        fmt = f"{p:,.0f}" if p>500 else f"{p:.2f}"
        sgn = "+" if (c or 0)>=0 else ""
        strip += f'<div class="mbox"><span class="mlbl">{lbl}</span><span class="mprice">{fmt}</span><span class="{cls}">{sgn}{c:.2f}%</span></div>'
    else:
        strip += f'<div class="mbox"><span class="mlbl">{lbl}</span><span class="mprice">—</span><span class="fl">—</span></div>'
st.markdown(f'<div class="macro-strip">{strip}</div>', unsafe_allow_html=True)

# Heartbeat bar
if heartbeat_on:
    next_hb = "—"
    if last_hb and last_hb != "Never":
        try:
            elapsed = (datetime.now()-datetime.fromisoformat(last_hb)).total_seconds()
            remaining = max(0, HB_SECS-elapsed)
            next_hb = f"{int(remaining//60)}m {int(remaining%60)}s"
        except: pass
    st.markdown(f"""<div class="heartbeat">
      <span class="hb-dot"></span>
      <span class="hb-label">Heartbeat active</span>
      <span style="font-size:0.7rem;color:#6b7280">Next check in {next_hb}</span>
      <span class="hb-time">{last_hb_str}</span>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_chat, tab_stage, tab_brain, tab_analyse, tab_history = st.tabs([
    "◇ Chat with Alice",
    f"⊠ Staged Ideas ({n_staged})",
    "◉ Brain / Memory",
    "⊕ Quick Analysis",
    "≡ Session History",
])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — CHAT (the main interface, port 3002 equivalent)
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:

    # Heartbeat auto-trigger
    if should_heartbeat() and gemini_key:
        with st.spinner("Running heartbeat check..."):
            hb_result = run_heartbeat(gemini_key)
        st.session_state["heartbeat_ts"]   = datetime.now().isoformat()
        st.session_state["heartbeat_data"] = hb_result
        # Add to conversation
        st.session_state["messages"].append({
            "role":"assistant","content":hb_result,
            "ts":datetime.now().isoformat(),"type":"heartbeat"
        })
        add_memory("heartbeat", hb_result[:200])
        # Telegram push if CHAT_YES
        if "CHAT_YES" in hb_result and tg_token and tg_chat:
            send_telegram(f"◇ Alice Heartbeat\n{datetime.now():%Y-%m-%d %H:%M}\n\n{hb_result}", tg_token, tg_chat)
        st.rerun()

    # Quick action buttons
    qa1,qa2,qa3,qa4,qa5 = st.columns(5)
    quick_prompts = {
        "Market check":    "What is the current market regime? Where is money flowing right now?",
        "Top ideas":       "Based on current macro conditions, what are your top 3 asymmetric trade ideas today?",
        "Risk check":      "Review my staged ideas and flag any risks I should be aware of.",
        "Heartbeat now":   "__HEARTBEAT__",
        "Clear chat":      "__CLEAR__",
    }
    for col, (label, prompt) in zip([qa1,qa2,qa3,qa4,qa5], quick_prompts.items()):
        with col:
            if st.button(label, key=f"qa_{label.replace(' ','_')}", use_container_width=True):
                if prompt == "__CLEAR__":
                    st.session_state["messages"] = []
                    st.rerun()
                elif prompt == "__HEARTBEAT__":
                    if gemini_key:
                        with st.spinner("Running heartbeat..."):
                            hb_result = run_heartbeat(gemini_key)
                        st.session_state["heartbeat_ts"] = datetime.now().isoformat()
                        st.session_state["messages"].append({
                            "role":"assistant","content":hb_result,
                            "ts":datetime.now().isoformat(),"type":"heartbeat"})
                        add_memory("heartbeat",hb_result[:200])
                        st.rerun()
                else:
                    st.session_state["messages"].append({
                        "role":"user","content":prompt,"ts":datetime.now().isoformat()})
                    st.rerun()

    st.markdown("---")

    # Render conversation history
    messages = st.session_state.get("messages",[])
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg.get("content","")
        ts   = msg.get("ts","")[:16].replace("T"," ")
        mtype= msg.get("type","")

        if role == "system" or mtype == "system":
            st.markdown(f'<div class="msg-bubble system">{content}</div>', unsafe_allow_html=True)
            continue

        if role == "user":
            st.markdown(f"""
<div class="msg user">
  <div>
    <div class="msg-bubble user">{content}</div>
    <div class="msg-meta" style="text-align:right">{ts}</div>
  </div>
  <div class="msg-avatar user">You</div>
</div>""", unsafe_allow_html=True)
        else:
            # Split reasoning from main response
            reasoning = ""
            main_content = content
            if "REASONING:" in content:
                parts = content.split("REASONING:",1)
                if len(parts)==2:
                    rest = parts[1]
                    # Find end of reasoning block (double newline or next section)
                    end_idx = rest.find("\n\n")
                    if end_idx > 0:
                        reasoning = rest[:end_idx].strip()
                        main_content = parts[0] + rest[end_idx:].strip()
                    else:
                        reasoning = rest.strip(); main_content = parts[0].strip()

            st.markdown(f"""
<div class="msg">
  <div class="msg-avatar alice">A</div>
  <div style="max-width:85%">
    {"<div class='reasoning-block'><span class='reasoning-label'>Reasoning</span>" + reasoning + "</div>" if reasoning and show_reasoning else ""}
    <div class="msg-bubble alice">{main_content.replace(chr(10),'<br>')}</div>
    <div class="msg-meta">{ts} {"🔔" if mtype=="heartbeat" else ""}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # If last message is from user → generate Alice response
    if messages and messages[-1]["role"] == "user":
        user_msg = messages[-1]["content"]
        if gemini_key:
            with st.chat_message("assistant", avatar="🔷"):
                out_container = st.empty()
                full_response = ""
                ticker_data   = {}

                gen, td = alice_respond(user_msg, gemini_key, show_reasoning)
                ticker_data = td

                for chunk in gen:
                    full_response += chunk
                    # Show clean version (hide STAGE_IDEA JSON from display)
                    display = re.sub(r'STAGE_IDEA:\s*\{[^}]+\}','',full_response)
                    out_container.markdown(display)

            # Save Alice's response
            st.session_state["messages"].append({
                "role":"assistant","content":full_response,
                "ts":datetime.now().isoformat()
            })

            # Auto-extract and stage trade ideas
            stage_matches = re.findall(r'STAGE_IDEA:\s*(\{[^}]+\})', full_response)
            for match in stage_matches:
                try:
                    idea = json.loads(match)
                    # Enrich with live data if available
                    t = idea.get("ticker","")
                    if t in ticker_data:
                        td_item = ticker_data[t]
                        idea.setdefault("entry",  td_item["entry"])
                        idea.setdefault("target", td_item["target"])
                        idea.setdefault("stop",   td_item["stop"])
                        idea.setdefault("rsi",    td_item["rsi"])
                        idea.setdefault("rr",     td_item["rr"])
                        idea.setdefault("upside", td_item["upside"])
                        idea.setdefault("downside",td_item["downside"])
                    idea["staged_at"] = datetime.now().isoformat()
                    idea["status"]    = "staged"
                    st.session_state["staged_ideas"].append(idea)
                    add_memory("trade_idea", f"Staged {t}: {idea.get('thesis','')[:100]}")
                except: pass

            # Auto-save important content to brain
            if any(kw in user_msg.lower() for kw in ["portfolio","watchlist","prefer","risk","hold"]):
                add_memory("user_context", f"User said: {user_msg[:150]}")
            if ticker_data:
                for sym, data in ticker_data.items():
                    add_memory("analysis", f"Analysed {sym} @ ${data['price']} — RSI {data['rsi']}, score context")

            # Update emotion based on content
            if any(w in full_response.lower() for w in ["bullish","opportunity","strong buy"]):
                st.session_state["emotion"] = "optimistic"
            elif any(w in full_response.lower() for w in ["cautious","risk","concern","warn"]):
                st.session_state["emotion"] = "cautious"
            elif any(w in full_response.lower() for w in ["bearish","avoid","dangerous"]):
                st.session_state["emotion"] = "concerned"
            else:
                st.session_state["emotion"] = "focused"

            st.rerun()
        else:
            st.warning("Add your Gemini API key in the sidebar to chat with Alice.")

    # Chat input
    user_input = st.chat_input("Ask Alice anything — 'Analyse NVDA', 'Top ideas today', 'Check my portfolio'...")
    if user_input:
        st.session_state["messages"].append({
            "role":"user","content":user_input,"ts":datetime.now().isoformat()})
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — STAGED IDEAS (git-like wallet: stage → review → confirm)
# ══════════════════════════════════════════════════════════════════════════════
with tab_stage:
    st.markdown("### ⊠ Staged Ideas")
    st.markdown("Alice stages high-conviction ideas here. Review → run Guard checks → confirm or reject.")
    st.caption("Inspired by OpenAlice's git-like wallet: `stage → commit → push`. Research-only — no execution.")

    staged = st.session_state.get("staged_ideas",[])
    if not staged:
        st.info("No ideas staged yet. Chat with Alice and she'll automatically stage high-conviction setups.")
    else:
        for idx, idea in enumerate(staged):
            status = idea.get("status","staged")
            status_cls = f"stage-{status}"

            # Render card
            chg_cls = "g" if (idea.get("upside",0) or 0) > 0 else "r"
            st.markdown(f"""
<div class="stage-card">
  <div class="stage-header">
    <span class="stage-label {status_cls}">{status.upper()}</span>
    <span class="stage-ticker">{idea.get('ticker','—')}</span>
    <span style="font-size:0.75rem;color:#6b7280;margin-left:auto">{idea.get('staged_at','')[:16].replace('T',' ')}</span>
  </div>
  <div class="stage-row">
    <div class="stage-item"><span class="stage-lbl">Entry</span><span class="stage-val b">${idea.get('entry','—')}</span></div>
    <div class="stage-item"><span class="stage-lbl">Target</span><span class="stage-val g">${idea.get('target','—')}</span></div>
    <div class="stage-item"><span class="stage-lbl">Stop</span><span class="stage-val r">${idea.get('stop','—')}</span></div>
    <div class="stage-item"><span class="stage-lbl">Upside</span><span class="stage-val {chg_cls}">{idea.get('upside','—')}%</span></div>
    <div class="stage-item"><span class="stage-lbl">R/R</span><span class="stage-val">{idea.get('rr','—')}×</span></div>
    <div class="stage-item"><span class="stage-lbl">RSI</span><span class="stage-val">{idea.get('rsi','—')}</span></div>
  </div>
  <div style="font-size:0.83rem;color:#374151;margin-top:6px">{idea.get('thesis','No thesis provided.')}</div>
</div>""", unsafe_allow_html=True)

            # Guard + action buttons
            col_g, col_r, col_del = st.columns([2,1,1])
            with col_g:
                if st.button(f"Run Guard checks", key=f"guard_{idx}", use_container_width=True):
                    passed, checks = run_guard(idea)
                    for c in checks:
                        cls = "guard-pass" if c["status"]=="PASS" else "guard-warn" if c["status"]=="WARN" else "guard-fail"
                        icon = "✓" if c["status"]=="PASS" else "⚠" if c["status"]=="WARN" else "✗"
                        st.markdown(f'<div class="{cls}">{icon} <strong>{c["name"]}</strong> — {c["msg"]}</div>', unsafe_allow_html=True)
                    if passed:
                        st.session_state["staged_ideas"][idx]["status"] = "reviewed"
                        add_memory("guard", f"Guard PASSED for {idea.get('ticker')} — all checks clear")
                    else:
                        st.session_state["staged_ideas"][idx]["status"] = "rejected"
                        add_memory("guard", f"Guard FAILED for {idea.get('ticker')}")

            with col_r:
                if st.button("Deep Dive →", key=f"dd_stage_{idx}", use_container_width=True):
                    ticker = idea.get("ticker","")
                    if gemini_key and ticker:
                        data = analyse_ticker(ticker)
                        ctx  = f"TICKER:{ticker}\n"
                        if data:
                            ctx += f"Price:${data['price']} RSI:{data['rsi']} MACD:{data['macd']} 1M:{data.get('m1',0):+.1f}%"
                        with st.spinner(f"Running deep dive on {ticker}..."):
                            result = call_gemini(st.session_state["persona"],
                                f"Run a complete investment thesis for {ticker}.\n{ctx}\n"
                                f"Staged thesis: {idea.get('thesis','')}\n\n"
                                f"Structure: Thesis / Signal Stack / Catalysts / Supply Chain / Bear Case / Final Verdict",
                                gemini_key)
                        with st.expander(f"◇ Alice on {ticker}", expanded=True):
                            st.markdown(result)
                        add_memory("deep_dive",f"Deep dive on {ticker}: {result[:150]}")

            with col_del:
                if st.button("Remove", key=f"rm_{idx}", use_container_width=True):
                    st.session_state["staged_ideas"].pop(idx)
                    st.rerun()

        st.divider()
        # Manual stage
        st.markdown("**Stage an idea manually**")
        m1,m2,m3,m4 = st.columns(4)
        with m1: manual_ticker = st.text_input("Ticker",placeholder="NVDA",key="ti_manual_ticker")
        with m2: manual_entry  = st.number_input("Entry $",min_value=0.0,value=0.0,key="ni_entry")
        with m3: manual_target = st.number_input("Target $",min_value=0.0,value=0.0,key="ni_target")
        with m4: manual_stop   = st.number_input("Stop $",min_value=0.0,value=0.0,key="ni_stop")
        manual_thesis = st.text_area("Thesis",placeholder="Why this trade?",height=70,key="ta_manual_thesis")
        if st.button("Stage idea →", type="primary", key="btn_manual_stage"):
            if manual_ticker.strip():
                t = manual_ticker.strip().upper()
                data = analyse_ticker(t)
                rr = round((manual_target-manual_entry)/max(manual_entry-manual_stop,0.01),2) if manual_stop>0 else 0
                idea = {
                    "ticker":t,"entry":manual_entry or (data["entry"] if data else 0),
                    "target":manual_target or (data["target"] if data else 0),
                    "stop":manual_stop or (data["stop"] if data else 0),
                    "thesis":manual_thesis or "Manual entry","status":"staged",
                    "staged_at":datetime.now().isoformat(),
                    "rsi":data["rsi"] if data else None,"rr":rr,
                    "upside":round((manual_target/manual_entry-1)*100,1) if manual_entry>0 else 0,
                    "downside":round((manual_stop/manual_entry-1)*100,1) if manual_entry>0 else 0,
                }
                st.session_state["staged_ideas"].append(idea)
                add_memory("trade_idea",f"Manually staged {t}: {manual_thesis[:80]}")
                st.success(f"✓ {t} staged")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — BRAIN (persistent memory / emotion / frontal lobe)
# ══════════════════════════════════════════════════════════════════════════════
with tab_brain:
    st.markdown("### ◉ Alice's Brain")
    st.markdown("Persistent memory across the session. Alice references this context in every response.")
    st.caption("Mirrors OpenAlice's `data/brain/` — frontal lobe memory + emotion state.")

    brain = st.session_state.get("brain",[])

    # Emotion display
    emotion_colors = {
        "focused":"#2563eb","optimistic":"#16a34a","cautious":"#d97706",
        "concerned":"#dc2626","excited":"#7c3aed","neutral":"#6b7280"
    }
    em = st.session_state.get("emotion","focused")
    em_color = emotion_colors.get(em,"#6b7280")
    st.markdown(f"""<div style="display:inline-flex;align-items:center;gap:8px;padding:8px 16px;
        background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:16px">
        <span style="width:10px;height:10px;border-radius:50%;background:{em_color};display:inline-block"></span>
        <span style="font-size:0.82rem;font-weight:600;color:#111827">Emotional state: {em.capitalize()}</span>
    </div>""", unsafe_allow_html=True)

    # Manual memory entry
    col_mt, col_mv = st.columns([1,3])
    with col_mt: mem_type = st.selectbox("Type",["note","analysis","risk","trade_idea","user_context"], key="sb_memtype")
    with col_mv: mem_text = st.text_input("Memory text",placeholder="Add a note to Alice's brain...",key="ti_memtext")
    if st.button("Add to brain →", key="btn_addmem"):
        if mem_text.strip():
            add_memory(mem_type, mem_text.strip())
            st.success("Added")
            st.rerun()

    if not brain:
        st.info("Brain is empty. Alice builds memory automatically as you chat.")
    else:
        st.markdown(f'<span class="mm-label">{len(brain)} memory entries</span>', unsafe_allow_html=True)
        # Group by type
        types = sorted(set(e["type"] for e in brain))
        filter_type = st.selectbox("Filter by type", ["All"]+types, key="sb_brain_filter")
        shown = [e for e in reversed(brain) if filter_type=="All" or e["type"]==filter_type]
        for e in shown[:40]:
            type_colors = {
                "heartbeat":"#7c3aed","analysis":"#2563eb","trade_idea":"#16a34a",
                "guard":"#d97706","deep_dive":"#0369a1","user_context":"#6b7280",
                "note":"#374151","config":"#9ca3af","risk":"#dc2626",
            }
            tc = type_colors.get(e["type"],"#6b7280")
            st.markdown(f"""<div class="brain-card">
  <span class="brain-type" style="color:{tc}">{e['type']}</span>
  <div class="brain-text">{e['text']}</div>
  <span class="brain-ts">{e['ts'][:16].replace('T',' ')}</span>
</div>""", unsafe_allow_html=True)

    # Export brain as JSON
    if brain:
        st.download_button("⬇ Export brain as JSON",
            data=json.dumps(brain, indent=2),
            file_name=f"alice_brain_{datetime.now():%Y%m%d_%H%M}.json",
            mime="application/json", key="btn_dl_brain")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — QUICK ANALYSIS (analysis-kit equivalent)
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyse:
    st.markdown("### ⊕ Quick Analysis")
    st.markdown("Direct access to Alice's analysis tools without going through chat.")

    ac1, ac2 = st.columns([3,1])
    with ac1: analyse_ticker_input = st.text_input("Ticker",placeholder="NVDA · TSLA · BTC-USD · PLTR",key="ti_analyse",label_visibility="collapsed")
    with ac2: analyse_btn = st.button("Analyse →", type="primary", key="btn_analyse", use_container_width=True)

    if analyse_btn and analyse_ticker_input.strip():
        t = analyse_ticker_input.strip().upper().replace("$","")
        with st.spinner(f"Fetching live data for {t}..."):
            data = analyse_ticker(t)

        if not data:
            st.error(f"Could not fetch data for {t}. Check the ticker symbol.")
        else:
            # Metric row
            col_a,col_b,col_c,col_d,col_e,col_f = st.columns(6)
            col_a.metric("Price",  f"${data['price']:,.2f}", f"{data['chg']:+.2f}%")
            col_b.metric("RSI(14)", data['rsi'],
                delta="Oversold" if data['rsi']<35 else "Overbought" if data['rsi']>70 else "Normal",
                delta_color="off")
            col_c.metric("MACD", f"{data['macd']}", f"vs {data['macd_sig']}")
            col_d.metric("1M Return", f"{data.get('m1',0):+.1f}%")
            col_e.metric("Vol Ratio", f"{data['vol_ratio']}×")
            col_f.metric("R/R", f"{data['rr']}×")

            # Levels
            st.markdown('<span class="mm-label">Trade levels (calculated)</span>', unsafe_allow_html=True)
            lc1,lc2,lc3,lc4,lc5 = st.columns(5)
            lc1.metric("Entry",    f"${data['entry']:,.2f}")
            lc2.metric("Target",   f"${data['target']:,.2f}", f"+{data['upside']:.1f}%")
            lc3.metric("Stop",     f"${data['stop']:,.2f}",   f"{data['downside']:.1f}%")
            lc4.metric("52W High", f"${data['w52h']:,.2f}")
            lc5.metric("52W Low",  f"${data['w52l']:,.2f}")

            # MAs
            st.markdown('<span class="mm-label">Moving averages</span>', unsafe_allow_html=True)
            ma_c1,ma_c2 = st.columns(2)
            if data["ma50"]:
                above50 = data["price"] > data["ma50"]
                ma_c1.metric("50 MA", f"${data['ma50']:,.2f}",
                    f"Price {'above' if above50 else 'below'} 50MA",
                    delta_color="normal" if above50 else "inverse")
            if data["ma200"]:
                above200 = data["price"] > data["ma200"]
                ma_c2.metric("200 MA", f"${data['ma200']:,.2f}",
                    f"Price {'above' if above200 else 'below'} 200MA",
                    delta_color="normal" if above200 else "inverse")

            # News
            news = get_news(f"{t} stock 2026", 5)
            if news:
                st.markdown('<span class="mm-label">Recent news</span>', unsafe_allow_html=True)
                for n in news:
                    st.markdown(f'<div class="brain-card"><div class="brain-text"><a href="{n["link"]}" target="_blank">{n["title"]}</a></div><span class="brain-ts">{n["source"]}</span></div>', unsafe_allow_html=True)

            # AI analysis
            if gemini_key:
                st.markdown('<span class="mm-label">Alice\'s analysis</span>', unsafe_allow_html=True)
                with st.status(f"Alice analysing {t}...", expanded=True) as an_s:
                    out = st.empty(); full = ""
                    quant_ctx = (f"Price:${data['price']}({data['chg']:+.2f}%) | RSI:{data['rsi']} | "
                                 f"MACD:{data['macd']} vs {data['macd_sig']} | 1M:{data.get('m1',0):+.1f}% | "
                                 f"Vol:{data['vol_ratio']}× | 52WH:${data['w52h']} L:${data['w52l']} | "
                                 f"MA50:${data['ma50']} MA200:${data['ma200']}")
                    news_ctx = "\n".join([f"• {n['title']}" for n in news[:3]])
                    for chunk in stream_gemini(st.session_state["persona"],
                        f"Analyse {t}.\nDATA:{quant_ctx}\nNEWS:\n{news_ctx}\n\n"
                        f"Structure: Thesis / Signal Stack / Catalysts / Bear Case / Verdict",
                        gemini_key):
                        full+=chunk; out.markdown(full)
                    an_s.update(label=f"✓ Analysis complete — {t}", state="complete")

                add_memory("analysis", f"Quick analysis on {t}: {full[:150]}")
                col_dl, col_st = st.columns(2)
                with col_dl:
                    st.download_button("⬇ Download", data=full,
                        file_name=f"alice_analysis_{t}_{datetime.now():%Y%m%d_%H%M}.txt",
                        mime="text/plain", key=f"dl_analysis_{t}")
                with col_st:
                    if st.button(f"Stage {t} →", key=f"stage_{t}", type="primary"):
                        idea = {"ticker":t,"entry":data["entry"],"target":data["target"],
                                "stop":data["stop"],"rsi":data["rsi"],"rr":data["rr"],
                                "upside":data["upside"],"downside":data["downside"],
                                "thesis":full[:200],"staged_at":datetime.now().isoformat(),"status":"staged"}
                        st.session_state["staged_ideas"].append(idea)
                        add_memory("trade_idea",f"Staged {t} via quick analysis")
                        st.success(f"✓ {t} staged — go to ⊠ Staged Ideas tab")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — SESSION HISTORY (JSONL sessions equivalent)
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### ≡ Session History")
    st.markdown("Full conversation stored as JSONL — the same format OpenAlice uses in `data/sessions/`.")

    messages = st.session_state.get("messages",[])
    staged   = st.session_state.get("staged_ideas",[])
    sid      = st.session_state.get("session_id","—")

    col_s1,col_s2,col_s3,col_s4 = st.columns(4)
    col_s1.metric("Session ID",  sid)
    col_s2.metric("Messages",    len(messages))
    col_s3.metric("Staged ideas",len(staged))
    col_s4.metric("Brain entries",len(st.session_state.get("brain",[])))

    if messages:
        st.markdown('<span class="mm-label">Conversation log</span>', unsafe_allow_html=True)
        for msg in messages:
            role = "👤 You" if msg["role"]=="user" else "◇ Alice"
            ts   = msg.get("ts","")[:16].replace("T"," ")
            preview = msg["content"][:200].replace("\n"," ")
            with st.expander(f"{role} · {ts} — {preview[:60]}..."):
                st.text(msg["content"])

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("⬇ Export JSONL (conversation)",
                data=export_jsonl(),
                file_name=f"alice_session_{sid}_{datetime.now():%Y%m%d}.jsonl",
                mime="text/plain", key="btn_dl_jsonl")
        with col_dl2:
            full_export = {
                "session_id":sid, "exported_at":datetime.now().isoformat(),
                "messages":messages, "brain":st.session_state.get("brain",[]),
                "staged_ideas":staged, "persona":st.session_state.get("persona",""),
            }
            st.download_button("⬇ Export full session JSON",
                data=json.dumps(full_export, indent=2),
                file_name=f"alice_full_{sid}_{datetime.now():%Y%m%d}.json",
                mime="application/json", key="btn_dl_full")

        if tg_token and tg_chat and st.button("→ Send summary to Telegram", key="btn_tg_summary"):
            summary = f"◇ Alice Session Summary\n{datetime.now():%Y-%m-%d %H:%M}\n\n"
            summary += f"Messages: {len(messages)} | Staged: {len(staged)} | Brain: {len(st.session_state.get('brain',[]))}\n\n"
            if staged:
                summary += "STAGED IDEAS:\n"
                for s in staged:
                    summary += f"• {s['ticker']} — Entry ${s.get('entry','?')} Target ${s.get('target','?')} Stop ${s.get('stop','?')}\n"
            send_telegram(summary, tg_token, tg_chat)
            st.success("Summary sent to Telegram")
    else:
        st.info("No conversation history yet. Start chatting with Alice.")
