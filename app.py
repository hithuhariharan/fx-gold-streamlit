import os, math, requests
import pandas as pd, streamlit as st

# ╭─────────────────────────  CONFIG  ─────────────────────────╮
FRED_KEY    = os.getenv("FRED_KEY", "")
QUANDL_KEY  = os.getenv("QUANDL_KEY", "")
SERIES      = {
    "DFF":      "Fed Funds Effective",
    "DFII10":   "10‑Y Real Yield",
    "CPIAUCSL": "CPI (All Urban)",
    "DTWEXBGS": "USD Broad Index",
    "VIXCLS":   "VIX Close",
}
START_DATE  = "2024-01-01"
# ╰────────────────────────────────────────────────────────────╯

st.set_page_config(page_title="FX & Gold Signals", page_icon="📈", layout="wide")
st.title("📈 Fundamentals‑Driven FX & Gold Signals with COT")

# ─── Helpers ─────────────────────────────────────────────────────────────

def fred(series_id: str) -> pd.Series:
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&observation_start={START_DATE}"
        f"&api_key={FRED_KEY}&file_type=json"
    )
    js = requests.get(url, timeout=10).json()
    obs = js.get("observations")
    if not obs:
        st.error(f"FRED error ({series_id}): {js.get('error_message','no data')}")
        return pd.Series(dtype=float)
    df = pd.DataFrame(obs)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"]  = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df["value"]

def fetch_cot_eur_net() -> float:
    if not QUANDL_KEY:
        return math.nan
    # CFTC Euro FX futures noncommercial net positions
    url = (
        f"https://data.nasdaq.com/api/v3/datasets/CFTC/131741_FO_L_ALL/data.json"
        f"?api_key={QUANDL_KEY}&limit=1"
    )
    js = requests.get(url, timeout=10).json().get("dataset_data", {})
    rows = js.get("data", [])
    if not rows or len(rows[0]) < 5:
        return math.nan
    # Column index 4 is net noncommercial positions
    return float(rows[0][4])

@st.cache_data(ttl=3600, show_spinner="Fetching macro & COT data ⏳")
def get_snapshot() -> dict:
    snap = {SERIES[k]: fred(k).iloc[-1] for k in SERIES}
    # YoY CPI inflation
    cpi = fred("CPIAUCSL")
    if len(cpi) >= 13:
        yoy = (cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100
        snap["CPI YoY %"] = round(yoy, 2)
    else:
        snap["CPI YoY %"] = math.nan
    # Fed Funds change ~1 month
    ff = fred("DFF").dropna()
    if len(ff) >= 22:
        Δ = (ff.iloc[-1] - ff.iloc[-22]) * 100
        snap["Fed Δ (bps)"] = round(Δ, 1)
    else:
        snap["Fed Δ (bps)"] = math.nan
    # COT sentiment
    snap["EUR COT net"] = fetch_cot_eur_net()
    return snap

data = get_snapshot()

# ─── Generate signals ────────────────────────────────────────────────────

signals = []
def add_sig(pair, dir, score, reason):
    signals.append((pair, dir, score, reason))

# 1) Rate hikes/cuts
if data["Fed Δ (bps)"] >= 25:
    add_sig("EURUSD", "SHORT", 70, "Fed hiking → USD strength")
    add_sig("XAUUSD", "SHORT", 60, "Higher rates ↑ opportunity cost")
elif data["Fed Δ (bps)"] <= -25:
    add_sig("EURUSD", "LONG", 70, "Fed cutting → USD weakness")
    add_sig("XAUUSD", "LONG", 60, "Lower rates support gold")

# 2) Real yield vs gold
ry = data.get("10‑Y Real Yield", math.nan)
if ry < 0:
    add_sig("XAUUSD", "LONG", 80, "Negative real yields → gold hedge")
elif ry > 1:
    add_sig("XAUUSD", "SHORT", 70, "Real yields >1% → gold beared")

# 3) CPI inflation
if data["CPI YoY %"] > 4:
    add_sig("XAUUSD", "LONG", 70, f"High inflation {data['CPI YoY %']}% → gold buy")

# 4) USD index inverse
usdix = data.get("USD Broad Index", math.nan)
if usdix >= 120:
    add_sig("XAUUSD", "LONG", 55, "USD over 120 → gold mean‑revert")
elif usdix <= 95:
    add_sig("XAUUSD", "LONG", 65, "Weak USD → gold demand up")

# 5) Risk‑off via VIX
if data.get("VIX Close", 0) >= 25:
    add_sig("USDJPY", "SHORT", 60, "Risk‑off → JPY safe‑haven")
    add_sig("XAUUSD", "LONG", 60, "Risk‑off → buy gold")

# 6) Carry proxy (real yield >0)
if not math.isnan(ry) and ry > 1:
    add_sig("USDJPY", "LONG", 65, "Positive real yield gap vs Japan")

# 7) COT contrarian for EUR
cot = data.get("EUR COT net", math.nan)
if cot > 50_000:
    add_sig("EURUSD", "SHORT", 60, f"COT net long {int(cot):,} → fade crowd")
elif cot < -50_000:
    add_sig("EURUSD", "LONG", 60, f"COT net short {int(cot):,} → buy weak EUR")

# Dedupe and rank
df_sig = (
    pd.DataFrame(signals, columns=["Pair","Dir","Score","Reason"])
      .sort_values("Score", ascending=False)
      .drop_duplicates(subset=["Pair","Dir"])
      .reset_index(drop=True)
)

# ─── Display ─────────────────────────────────────────────────────────────

st.subheader("Latest Macro & COT Snapshot")
nice = {
    "Fed Funds Effective": "Fed Funds (%)",
    "10‑Y Real Yield":    "10‑Y Real Yield (%)",
    "CPI (All Urban)":    "CPI Level",
    "CPI YoY %":          "CPI YoY (%)",
    "USD Broad Index":    "USD Index",
    "VIX Close":          "VIX",
    "Fed Δ (bps)":        "Fed Δ (bps)",
    "EUR COT net":        "EUR COT net (contracts)",
}
st.table(pd.Series(data).rename(index=nice).to_frame("Value"))

st.subheader("Fundamentals‑Driven Signals")
if df_sig.empty:
    st.info("No strong signals right now.")
else:
    st.table(df_sig)

st.caption(
    "Rules: rate‑change, real yields, inflation, USD index, VIX risk, carry proxy, COT contrarian."
)
