# ---------------- app.py ----------------
import os, math, requests, pandas as pd, streamlit as st

# ---- 1. Page setup -------------------------------------------------
st.set_page_config(page_title="FX & Gold Signals", page_icon="📈", layout="wide")
st.title("📈  Institutional‑Style FX & Gold Signals (Demo)")

# ---- 2. Minimal data layer ----------------------------------------
FRED = "https://api.stlouisfed.org/fred/series/observations"
API_KEY = os.getenv("FRED_KEY", "")          # <- we’ll add this in HF Secrets
PARAMS  = "&observation_start=2024-01-01&file_type=json"

def fred(series_id: str) -> float:
    url = f"{FRED}?series_id={series_id}{PARAMS}&api_key={API_KEY}"
    val = requests.get(url, timeout=10).json()["observations"][-1]["value"]
    return float(val) if val not in ("", ".") else math.nan

@st.cache_data(ttl=3600)                      # refresh every hour
def macro_snapshot():
    return {
        "US 10‑Y Real Yield (DFII10)": fred("DFII10"),
        "Broad USD Index (DTWEXBGS)": fred("DTWEXBGS"),
        "London Gold Fix USD (GOLD)": fred("GOLDAMGBD228NLBM"),
    }

data = macro_snapshot()

# ---- 3. Toy signal logic ------------------------------------------
signals = []
if data["US 10‑Y Real Yield (DFII10)"] > 1:
    signals.append(("XAUUSD", "SHORT", 80, "Real yield > 1 % → high opp. cost"))
elif data["US 10‑Y Real Yield (DFII10)"] < 0:
    signals.append(("XAUUSD", "LONG", 75, "Real yield < 0 % → gold hedge"))

if data["Broad USD Index (DTWEXBGS)"] > 120:
    signals.append(("EURUSD", "LONG", 70, "USD basket extreme > 120 → mean‑revert"))
elif data["Broad USD Index (DTWEXBGS)"] < 95:
    signals.append(("EURUSD", "SHORT", 70, "USD weak < 95 → downside risk"))

# ---- 4. Display ----------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Latest Macro Snapshot")
    st.table(pd.Series(data, name="Value"))

with c2:
    st.subheader("Signals")
    if signals:
        st.table(pd.DataFrame(signals,
                              columns=["Symbol", "Direction", "Confidence", "Reason"]))
    else:
        st.info("No actionable signals right now – check again later.")

st.caption(
    "⚠️  Demo only. Real engine would have full event‑driven, carry and "
    "risk‑sentiment models."
)
# -------------------------------------------------- end -------------
