import os, math, requests, pandas as pd, streamlit as st

st.set_page_config(page_title="FX & Gold Signals", page_icon="📈")

API_KEY = os.getenv("FRED_KEY", "")  # empty for now – will still run locally
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

def fred(series_id):
    url = f"{FRED_URL}?series_id={series_id}&file_type=json&api_key={API_KEY}"
    data = requests.get(url, timeout=10).json()
    if not data.get("observations"):              # bad key or quota exceeded
        return math.nan
    return float(data["observations"][-1]["value"])

data = {
    "10‑Y Real Yield": fred("DFII10"),
    "Broad USD Index": fred("DTWEXBGS"),
    "Gold USD":        fred("GOLDAMGBD228NLBM"),
}

signals = []
if data["10‑Y Real Yield"] > 1:  signals.append(("XAUUSD", "SHORT", "Real yield > 1 %"))
elif data["10‑Y Real Yield"] < 0: signals.append(("XAUUSD", "LONG",  "Real yield < 0 %"))

if data["Broad USD Index"] > 120: signals.append(("EURUSD", "LONG",  "USD index extreme"))
elif data["Broad USD Index"] < 95: signals.append(("EURUSD", "SHORT", "USD weak"))

st.title("📈 FX & Gold Signals (local demo)")
st.write("If numbers show NaN, you haven't added a FRED key yet—still OK for structure.")

st.subheader("Macro snapshot")
st.table(pd.Series(data, name="Value"))

st.subheader("Signals")
if signals:
    st.table(pd.DataFrame(signals, columns=["Symbol", "Direction", "Reason"]))
else:
    st.info("No signals right now.")
