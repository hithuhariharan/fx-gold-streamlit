# -----------------------------  app.py  ---------------------------------
import os, math, requests, datetime as dt
import pandas as pd, streamlit as st

# ╭─────────────────────────  CONFIG  ─────────────────────────╮
FRED_KEY  = os.getenv("FRED_KEY", "")
SERIES    = {                       #  FRED series used
    "DFF":      "Fed Funds Effective",
    "DFII10":   "10‑Y Real Yield",
    "CPIAUCSL": "CPI (All Urban)",
    "DTWEXBGS": "USD Broad Index",
    "VIXCLS":   "VIX Close",
}
START_DATE = "2024-01-01"           # how far back to pull (fast)
# ╰────────────────────────────────────────────────────────────╯

st.set_page_config(page_title="FX & Gold Signals", page_icon="📈")
st.title("📈 Fundamentals‑Driven FX & Gold Signals")

API = "https://api.stlouisfed.org/fred/series/observations"

# ---------------------- Helpers -----------------------------------------
def fred(series_id: str) -> pd.DataFrame:
    url = (
        f"{API}?series_id={series_id}&observation_start={START_DATE}"
        f"&api_key={FRED_KEY}&file_type=json"
    )
    js = requests.get(url, timeout=10).json()
    if "observations" not in js or not js["observations"]:
        st.error(f"FRED error for {series_id}: {js.get('error_message','no data')}")
        return pd.DataFrame()
    df = pd.DataFrame(js["observations"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"]  = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df["value"]

@st.cache_data(ttl=3600, show_spinner="Fetching macro data ⏳")
def get_snapshot():
    snap = {k: fred(k).iloc[-1] for k in SERIES}
    # YoY inflation
    cpi = fred("CPIAUCSL")
    yoy = ((cpi.iloc[-1] / cpi.iloc[-13]) - 1) * 100 if len(cpi) > 12 else math.nan
    snap["CPI_YoY%"] = round(yoy, 2)
    # Fed last change
    ff = fred("DFF").dropna()
    snap["FedChange_bps"] = round((ff.iloc[-1] - ff.iloc[-22]) * 100, 1) if len(ff) > 21 else math.nan
    return snap

data = get_snapshot()

# ------------------ Fundamental driver functions ------------------------
signals = []
comments = []

def add_sig(pair, direction, score, reason):
    signals.append((pair, direction, score, reason))

# 1️⃣  Interest‑rate change → USD bias
if data["FedChange_bps"] >= 25:
    add_sig("EURUSD", "SHORT", 70, "Recent Fed hike → USD stronger")
    add_sig("XAUUSD", "SHORT", 60, "Higher policy rate ↑ opp. cost of gold")
elif data["FedChange_bps"] <= -25:
    add_sig("EURUSD", "LONG", 70, "Fed cut → USD weaker")
    add_sig("XAUUSD", "LONG", 60, "Lower rates supportive")

# 2️⃣  Carry / rate differential (simplified with real yield vs zero‑rate JPY)
if data["10‑Y Real Yield"] > 1:
    add_sig("USDJPY", "LONG", 65, "Positive real‑yield gap vs Japan")

# 3️⃣  Inflation hedge
if not math.isnan(data["CPI_YoY%"]) and data["CPI_YoY%"] > 4:
    add_sig("XAUUSD", "LONG", 70, f"High YoY inflation {data['CPI_YoY%']} %")

# 4️⃣  USD strength inverse for gold
if data["USD Broad Index"] >= 120:
    add_sig("XAUUSD", "LONG", 55, "USD extreme strength often mean‑reverts (inverse corr.)")
elif data["USD Broad Index"] <= 95:
    add_sig("XAUUSD", "LONG", 65, "Weak USD typically lifts gold")

# 5️⃣  Risk sentiment via VIX
if data["VIX Close"] >= 25:
    add_sig("USDJPY", "SHORT", 60, "Risk‑off → buy JPY (safe haven)")
    add_sig("XAUUSD", "LONG", 60, "Risk‑off → gold hedge")

# 6️⃣  Real‑yield core model
if data["10‑Y Real Yield"] < 0:
    add_sig("XAUUSD", "LONG", 80, "Negative real yield bullish gold")
elif data["10‑Y Real Yield"] > 1:
    add_sig("XAUUSD", "SHORT", 70, "Real yield > 1 % bearish gold")

# Remove duplicates keeping highest score per pair+dir
df_sig = (
    pd.DataFrame(signals, columns=["Pair", "Dir", "Score", "Reason"])
      .sort_values(["Score"], ascending=False)
      .drop_duplicates(subset=["Pair", "Dir"])
      .reset_index(drop=True)
)

# -----------------  Display  -------------------------------------------
st.subheader("Latest Macro Snapshot")
nice = {
    "Fed Funds Effective": "Fed Funds (%)",
    "10‑Y Real Yield": "10‑Y Real Yield (%)",
    "CPI (All Urban)": "CPI Level",
    "CPI_YoY%": "CPI YoY %",
    "USD Broad Index": "USD Index (DTWEXBGS)",
    "VIX Close": "VIX Close",
    "FedChange_bps": "Fed Δ last month (bps)",
}
st.table(pd.Series(data).rename(index=nice).to_frame("Value"))

st.subheader("Fundamentals‑Driven Signals")
if df_sig.empty:
    st.info("No strong signals right now.")
else:
    st.table(df_sig)

st.caption(
    "Toy example ⟶ 7 FRED series, mapped to fundamental rules. "
    "Extend by adding more series & logic in the driver section."
)
# -----------------------------------------------------------------------
