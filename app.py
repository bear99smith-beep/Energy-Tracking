
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import pytz
import os

app = FastAPI()

# ---------- Config ----------
API_KEY = os.getenv("OCTOPUS_API_KEY")

ELEC_MPAN = os.getenv("ELEC_MPAN")
ELEC_SERIAL = os.getenv("ELEC_SERIAL")

GAS_MPRN = os.getenv("GAS_MPRN")
GAS_SERIAL = os.getenv("GAS_SERIAL")
GAS_UNIT_RATE = float(os.getenv("GAS_UNIT_RATE", 0))      # p/kWh
GAS_STANDING = float(os.getenv("GAS_STANDING_CHARGE", 0)) # p/day

TZ = pytz.timezone("Europe/London")

TARIFF_URL = (
    "https://api.octopus.energy/v1/products/AGILE-24-10-01/"
    "electricity-tariffs/E-1R-AGILE-24-10-01-A/"
    "standard-unit-rates/"
)

# ---------- Health ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}

# ---------- Electricity ----------
@app.get("/api/electricity/cheapest")
def cheapest(slots: int = 4):
    start = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    r = requests.get(
        TARIFF_URL,
        auth=HTTPBasicAuth(API_KEY, ""),
        params={"period_from": start.isoformat(), "period_to": end.isoformat()}
    )

    prices = sorted(r.json()["results"], key=lambda x: x["value_inc_vat"])[:slots]
    return prices


@app.get("/api/electricity/cost")
def electricity_cost(days: int = 1):
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    usage_url = (
        f"https://api.octopus.energy/v1/electricity-meter-points/"
        f"{ELEC_MPAN}/meters/{ELEC_SERIAL}/consumption/"
    )

    usage = requests.get(
        usage_url,
        auth=HTTPBasicAuth(API_KEY, ""),
        params={"period_from": start.isoformat(), "period_to": end.isoformat()}
    ).json()["results"]

    prices = requests.get(
        TARIFF_URL,
        auth=HTTPBasicAuth(API_KEY, ""),
        params={"period_from": start.isoformat(), "period_to": end.isoformat()}
    ).json()["results"]

    usage_map = {u["interval_start"]: u["consumption"] for u in usage}

    total_kwh = 0
    total_cost = 0

    for p in prices:
        kwh = usage_map.get(p["valid_from"])
        if kwh:
            total_kwh += kwh
            total_cost += kwh * p["value_inc_vat"] / 100

    return {
        "days": days,
        "kwh": round(total_kwh, 2),
        "cost": round(total_cost, 2)
    }

# ---------- Gas ----------
@app.get("/api/gas/usage")
def gas_usage(days: int = 7):
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    url = (
        f"https://api.octopus.energy/v1/gas-meter-points/"
        f"{GAS_MPRN}/meters/{GAS_SERIAL}/consumption/"
    )

    r = requests.get(
        url,
        auth=HTTPBasicAuth(API_KEY, ""),
        params={"period_from": start.isoformat(), "period_to": end.isoformat(), "group_by": "day"}
    )

    return r.json()["results"]


@app.get("/api/gas/cost")
def gas_cost(days: int = 7):
    data = gas_usage(days)
    total_kwh = sum(d["consumption"] for d in data)
    total_cost = (
        total_kwh * GAS_UNIT_RATE +
        len(data) * GAS_STANDING
    ) / 100

    return {
        "days": len(data),
        "kwh": round(total_kwh, 2),
        "cost": round(total_cost, 2)
    }

# ---------- Static UI ----------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
