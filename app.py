--- a/app.py
+++ b/app.py
@@
 # ╭─────────────────────────  CONFIG  ─────────────────────────╮
 FRED_KEY  = os.getenv("FRED_KEY", "")
+QUANDL_KEY= os.getenv("QUANDL_KEY", "")
 SERIES    = {                       #  FRED series used
@@
-# ---------------------- Helpers -----------------------------------------
+# ---------------------- Helpers -----------------------------------------
 def fred(series_id: str) -> pd.DataFrame:
@@
     return df["value"]
+
+def fetch_cot_eur_net():
+    """
+    Fetch the latest COT net position for Euro futures (speculators)
+    from Quandl's CFTC dataset.
+    """
+    if not QUANDL_KEY:
+        return math.nan
+    # Dataset CFTC/131741_FO_L_ALL = Euro FX futures, long minus short by noncommercials
+    url = (
+        f"https://www.quandl.com/api/v3/datasets/CFTC/131741_FO_L_ALL/data.json"
+        f"?limit=1&api_key={QUANDL_KEY}"
+    )
+    r = requests.get(url, timeout=10)
+    js = r.json().get("dataset_data", {})
+    data = js.get("data", [])
+    if not data or len(data[0]) < 5:
+        return math.nan
+    # In Quandl CFTC, column 4 = 'Noncommercial Positions: Net Positions'
+    return float(data[0][4])
@@
 @st.cache_data(ttl=3600, show_spinner="Fetching macro data ⏳")
 def get_snapshot():
     # Use human‑readable labels as keys
-    snap = {SERIES[k]: fred(k).iloc[-1] for k in SERIES}
+    snap = {SERIES[k]: fred(k).iloc[-1] for k in SERIES}
+    # COT sentiment for EUR
+    snap["EUR COT net"] = fetch_cot_eur_net()
 
     # YoY inflation
@@
     return snap
@@
 # ------------------ Fundamental driver functions ------------------------
 signals = []
 comments = []
 
 def add_sig(pair, direction, score, reason):
     signals.append((pair, direction, score, reason))
 
 # 1️⃣  Interest‑rate change → USD bias
@@
 # 6️⃣  Real‑yield core model
@@
 # Remove duplicates keeping highest score per pair+dir
 df_sig = (
@@
 )
 
+# 7️⃣  COT sentiment (EUR speculators net‐long => contrarian signal)
+cot = data.get("EUR COT net", math.nan)
+if not math.isnan(cot):
+    # if speculators net‑long > 50k contracts, heavy crowd = potential reversal
+    if cot > 50_000:
+        add_sig("EURUSD", "SHORT", 60, f"EUR COT net {int(cot):,} → crowd long, fade")
+    # if extreme net‑short, contrarian long
+    elif cot < -50_000:
+        add_sig("EURUSD", "LONG", 60, f"EUR COT net {int(cot):,} → crowd short, buy")
+
+# Rebuild df_sig to include any new COT entries
+df_sig = (
+    pd.DataFrame(signals, columns=["Pair", "Dir", "Score", "Reason"])
+      .sort_values(["Score"], ascending=False)
+      .drop_duplicates(subset=["Pair", "Dir"])
+      .reset_index(drop=True)
+)
 
 # -----------------  Display  -------------------------------------------
 st.subheader("Latest Macro Snapshot")
@@
 nice = {
@@
-    "FedChange_bps": "Fed Δ last month (bps)",
+    "FedChange_bps": "Fed Δ last month (bps)",
+   "EUR COT net":  "EUR COT net (contracts)",
 }
 st.table(pd.Series(data).rename(index=nice).to_frame("Value"))
