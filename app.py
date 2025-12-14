
from typing import Dict, List, Any  # add this near the top
PRICES_CACHE: Dict[str, List[Dict[str, Any]]] = {}
diff --git a/app.py b/app.py
index 6e1c1f2..b8c9f3a 100644
--- a/app.py
+++ b/app.py
@@ -1,36 +1,78 @@
-from fastapi import FastAPI
-from fastapi.responses import FileResponse, JSONResponse
-import requests
-from requests.auth import HTTPBasicAuth
-from datetime import datetime, timedelta
-import pytz
-import os
+from fastapi import FastAPI
+from fastapi.responses import FileResponse, JSONResponse
+import requests
+from requests.auth import HTTPBasicAuth
+from datetime import datetime, timedelta, date
+import pytz
+import os
+
+# -----------------------
+# App & configuration
+# -----------------------
 
 app = FastAPI()
 
-# ---------- Config ----------
-API_KEY = os.getenv("OCTOPUS_API_KEY")
-
-ELEC_MPAN   = os.getenv("ELEC_MPAN")
-ELEC_SERIAL = os.getenv("ELEC_SERIAL")
-
-GAS_MPRN    = os.getenv("GAS_MPRN")
-GAS_SERIAL  = os.getenv("GAS_SERIAL")
-GAS_UNIT_RATE   = float(os.getenv("GAS_UNIT_RATE", 0))       # p/kWh
-GAS_STANDING    = float(os.getenv("GAS_STANDING_CHARGE", 0)) # p/day
-
-TZ = pytz.timezone("Europe/London")
-
-TARIFF_URL = (
-    "https://api.octopus.energy/v1/products/AGILE-24-10-01/"
-    "electricity-tariffs/E-1R-AGILE-24-10-01-A/"
-    "standard-unit-rates/"
-)
+# --------- Secrets & Env ---------
+API_KEY = os.getenv("OCTOPUS_API_KEY")
+
+ELEC_MPAN   = os.getenv("ELEC_MPAN")
+ELEC_SERIAL = os.getenv("ELEC_SERIAL")
+ELEC_STANDING = float(os.getenv("ELEC_STANDING_CHARGE", 0))  # p/day
+
+GAS_MPRN    = os.getenv("GAS_MPRN")
+GAS_SERIAL  = os.getenv("GAS_SERIAL")
+GAS_UNIT_RATE   = float(os.getenv("GAS_UNIT_RATE", 0))       # p/kWh
+GAS_STANDING    = float(os.getenv("GAS_STANDING_CHARGE", 0)) # p/day
+
+# Agile product/tariff configurable (defaults kept to current values)
+AGILE_PRODUCT_CODE = os.getenv("AGILE_PRODUCT_CODE", "AGILE-24-10-01")
+AGILE_TARIFF_CODE  = os.getenv("AGILE_TARIFF_CODE",  "E-1R-AGILE-24-10-01-A")
+
+TZ = pytz.timezone("Europe/London")
+UTC = pytz.UTC
+
+def agile_tariff_url() -> str:
+    return (
+        f"https://api.octopus.energy/v1/products/{AGILE_PRODUCT_CODE}/"
+        f"electricity-tariffs/{AGILE_TARIFF_CODE}/"
+        f"standard-unit-rates/"
+    )
+
+# Simple in-memory cache for today’s prices (resets daily)
+PRICES_CACHE: dict[str, list[dict]] = {}
+
+# -----------------------
+# Helpers
+# -----------------------
+def _parse_ts(ts: str) -> datetime:
+    """Parse ISO8601 string to timezone-aware UTC datetime.
+    Octopus often returns 'Z' suffix; normalize that then convert to UTC.
+    """
+    if ts.endswith("Z"):
+        ts = ts[:-1] + "+00:00"
+    dt = datetime.fromisoformat(ts)
+    # Ensure awareness & normalize to UTC
+    if dt.tzinfo is None:
+        dt = dt.replace(tzinfo=UTC)
+    return dt.astimezone(UTC)
+
+def _fetch_agile_prices_for_day(day: date) -> list[dict]:
+    """Get the 48 half-hour Agile price slots for a given local day.
+    Cached for the day to reduce API calls."""
+    key = day.isoformat()
+    if key in PRICES_CACHE:
+        return PRICES_CACHE[key]
+
+    start = TZ.localize(datetime.combine(day, datetime.min.time()))
+    end   = start + timedelta(days=1)
+    r = requests.get(
+        agile_tariff_url(),
+        auth=HTTPBasicAuth(API_KEY, ""),
+        params={"period_from": start.isoformat(), "period_to": end.isoformat(), "page_size": 48},
+        timeout=15,
+    )
+    r.raise_for_status()
+    results = r.json()["results"]
+    PRICES_CACHE[key] = results
+    return results
 
-# ---------- Startup logs ----------
-print("🔑 OCTOPUS_API_KEY set:", bool(API_KEY))
-print("⚡ ELEC_MPAN:", ELEC_MPAN)
-print("🔥 GAS_MPRN:", GAS_MPRN)
+# ---------- Startup logs ----------
+print("🔑 OCTOPUS_API_KEY set:", bool(API_KEY))
+print("⚡ ELEC_MPAN:", ELEC_MPAN)
+print("🔥 GAS_MPRN:", GAS_MPRN)
 
 # ---------- Health ----------
 @app.get("/api/health")
 def health():
     return {"status": "ok"}
 
 # ---------- Electricity ----------
 @app.get("/api/electricity/cheapest")
 def cheapest(slots: int = 4):
-    if not API_KEY:
+    if not API_KEY:
         return JSONResponse(status_code=500, content={"error": "API key missing"})
 
-    start = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
-    end = start + timedelta(days=1)
-    r = requests.get(
-        TARIFF_URL,
-        auth=HTTPBasicAuth(API_KEY, ""),
-        params={"period_from": start.isoformat(), "period_to": end.isoformat()},
-    )
-    r.raise_for_status()
-    prices = sorted(r.json()["results"], key=lambda x: x["value_inc_vat"])[:slots]
-    return prices
+    today_local = datetime.now(TZ).date()
+    prices = sorted(_fetch_agile_prices_for_day(today_local), key=lambda x: x["value_inc_vat"])[:slots]
+    return prices
 
 @app.get("/api/electricity/cost")
 def electricity_cost(days: int = 1):
-    if not all([API_KEY, ELEC_MPAN, ELEC_SERIAL]):
+    if not all([API_KEY, ELEC_MPAN, ELEC_SERIAL]):
         return JSONResponse(status_code=500, content={"error": "Electricity config missing"})
 
     end = datetime.utcnow()
     start = end - timedelta(days=days)
 
     usage_url = (
         f"https://api.octopus.energy/v1/electricity-meter-points/"
         f"{ELEC_MPAN}/meters/{ELEC_SERIAL}/consumption/"
     )
-    usage = requests.get(
+    usage = requests.get(
         usage_url,
         auth=HTTPBasicAuth(API_KEY, ""),
-        params={"period_from": start.isoformat(), "period_to": end.isoformat()},
-    ).json()["results"]
+        params={"period_from": start.isoformat(), "period_to": end.isoformat(), "page_size": 25000},
+        timeout=30,
+    ).json()["results"]
 
-    prices = requests.get(
-        TARIFF_URL,
-        auth=HTTPBasicAuth(API_KEY, ""),
-        params={"period_from": start.isoformat(), "period_to": end.isoformat()},
-    ).json()["results"]
+    # Build a UTC-aware map of half-hour consumption by slot start
+    usage_map = {_parse_ts(u["interval_start"]): u["consumption"] for u in usage}
+
+    # Aggregate cost: iterate days; for each day pull cached prices, match by UTC slot
+    total_kwh = 0.0
+    total_cost_gbp = 0.0
+    for d in range(days):
+        day_dt_local = (datetime.utcnow() - timedelta(days=d)).astimezone(TZ).date()
+        day_prices = _fetch_agile_prices_for_day(day_dt_local)
+        for p in day_prices:
+            slot_start = _parse_ts(p["valid_from"])
+            kwh = usage_map.get(slot_start)
+            if kwh is not None:
+                total_kwh += kwh
+                # value_inc_vat is in pence/kWh → convert to GBP
+                total_cost_gbp += (kwh * p["value_inc_vat"]) / 100.0
+
+    # Add standing charge (p/day → GBP)
+    if ELEC_STANDING > 0:
+        total_cost_gbp += (days * ELEC_STANDING) / 100.0
 
-    usage_map = {u["interval_start"]: u["consumption"] for u in usage}
-    total_kwh = 0
-    total_cost = 0
-    for p in prices:
-        kwh = usage_map.get(p["valid_from"])
-        if kwh is not None:
-            total_kwh += kwh
-            total_cost += kwh * p["value_inc_vat"] / 100
-    return {"days": days, "kwh": round(total_kwh, 2), "cost": round(total_cost, 2)}
+    return {"days": days, "kwh": round(total_kwh, 2), "cost": round(total_cost_gbp, 2)}
 
 # ---------- Gas ----------
 @app.get("/api/gas/usage")
 def gas_usage(days: int = 7):
-    if not all([API_KEY, GAS_MPRN, GAS_SERIAL]):
+    if not all([API_KEY, GAS_MPRN, GAS_SERIAL]):
         return JSONResponse(status_code=500, content={"error": "Gas config missing"})
 
     end = datetime.utcnow()
     start = end - timedelta(days=days)
 
     url = (
         f"https://api.octopus.energy/v1/gas-meter-points/"
         f"{GAS_MPRN}/meters/{GAS_SERIAL}/consumption/"
     )
-    r = requests.get(
+    r = requests.get(
         url,
         auth=HTTPBasicAuth(API_KEY, ""),
-        params={"period_from": start.isoformat(), "period_to": end.isoformat(), "group_by": "day"},
-    )
-    r.raise_for_status()
-    return r.json()["results"]
+        params={"period_from": start.isoformat(), "period_to": end.isoformat(), "group_by": "day"},
+        timeout=30,
+    )
+    r.raise_for_status()
+    return r.json()["results"]
 
 @app.get("/api/gas/cost")
 def gas_cost(days: int = 7):
-    usage = gas_usage(days)
-    if isinstance(usage, dict) and "error" in usage:
-        return usage
-    total_kwh = sum(d["consumption"] for d in usage)
-    total_cost = (total_kwh * GAS_UNIT_RATE + len(usage) * GAS_STANDING) / 100
-    return {"days": len(usage), "kwh": round(total_kwh, 2), "cost": round(total_cost, 2)}
+    usage = gas_usage(days)
+    if isinstance(usage, dict) and "error" in usage:
+        return usage
+    total_kwh = sum(d["consumption"] for d in usage)
+    total_cost_gbp = (total_kwh * GAS_UNIT_RATE + len(usage) * GAS_STANDING) / 100.0
+    return {"days": len(usage), "kwh": round(total_kwh, 2), "cost": round(total_cost_gbp, 2)}
 
# ---------- Debug (temporary) ----------
from fastapi.responses import JSONResponse
import os

@app.get("/api/debug/env")
def debug_env():
    """Temporary endpoint to verify Fly secrets (masked for safety)."""
    def mask(val):
        if val is None:
            return None
        v = str(val)
        return "*" * (len(v) - 4) + v[-4:] if len(v) > 4 else "*" * len(v)

    data = {
        "OCTOPUS_API_KEY": mask(os.getenv("OCTOPUS_API_KEY")),
        "ELEC_MPAN": os.getenv("ELEC_MPAN"),
        "ELEC_SERIAL": os.getenv("ELEC_SERIAL"),
        "ELEC_STANDING_CHARGE": os.getenv("ELEC_STANDING_CHARGE"),
        "GAS_MPRN": os.getenv("GAS_MPRN"),
        "GAS_SERIAL": os.getenv("GAS_SERIAL"),
        "GAS_UNIT_RATE": os.getenv("GAS_UNIT_RATE"),
        "GAS_STANDING_CHARGE": os.getenv("GAS_STANDING_CHARGE"),
        "AGILE_PRODUCT_CODE": os.getenv("AGILE_PRODUCT_CODE"),
        "AGILE_TARIFF_CODE": os.getenv("AGILE_TARIFF_CODE"),
    }
    return JSONResponse(content=data)
 # ---------- UI ----------
 @app.get("/")
 def root():
     return FileResponse("static/index.html")

