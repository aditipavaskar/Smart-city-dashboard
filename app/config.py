"""
Central configuration for the Smart City Operations Dashboard.

Keeping domains/roles/thresholds here (instead of scattered through the
codebase) means adding a new city domain or role is a one-file change —
nothing in main.py, streaming, or the frontend routing has to know about it
beyond reading this config.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# City zones (used by the map view and as the partition key for every metric)
# ---------------------------------------------------------------------------
with open(DATA_DIR / "zones.json") as f:
    ZONES = json.load(f)

ZONE_IDS = [z["id"] for z in ZONES]

# ---------------------------------------------------------------------------
# Domains: the four operational areas the dashboard monitors.
# Each domain declares its own metrics + the "bad direction" for anomaly
# scoring (higher_is_worse vs lower_is_worse) so predictive.py can stay
# generic instead of hard-coding per-metric logic.
# ---------------------------------------------------------------------------
DOMAINS = {
    "traffic": {
        "label": "Traffic",
        "topic": "traffic.readings",
        "metrics": {
            "congestion_index": {"unit": "%", "higher_is_worse": True, "warn": 70, "critical": 88},
            "avg_speed_kmh": {"unit": "km/h", "higher_is_worse": False, "warn": 18, "critical": 8},
            "incident_count": {"unit": "count", "higher_is_worse": True, "warn": 3, "critical": 6},
        },
    },
    "energy": {
        "label": "Energy",
        "topic": "energy.readings",
        "metrics": {
            "load_mw": {"unit": "MW", "higher_is_worse": True, "warn": 82, "critical": 95},
            "renewable_pct": {"unit": "%", "higher_is_worse": False, "warn": 25, "critical": 10},
            "grid_stress_index": {"unit": "%", "higher_is_worse": True, "warn": 65, "critical": 85},
        },
    },
    "pollution": {
        "label": "Pollution",
        "topic": "pollution.readings",
        "metrics": {
            "aqi": {"unit": "AQI", "higher_is_worse": True, "warn": 150, "critical": 200},
            "pm25": {"unit": "ug/m3", "higher_is_worse": True, "warn": 55, "critical": 90},
            "co2_ppm": {"unit": "ppm", "higher_is_worse": True, "warn": 900, "critical": 1200},
        },
    },
    "public_services": {
        "label": "Public Services",
        "topic": "public_services.readings",
        "metrics": {
            "waste_bin_fill_pct": {"unit": "%", "higher_is_worse": True, "warn": 80, "critical": 95},
            "water_pressure_psi": {"unit": "psi", "higher_is_worse": False, "warn": 35, "critical": 20},
            "streetlight_fault_count": {"unit": "count", "higher_is_worse": True, "warn": 4, "critical": 10},
        },
    },
}

DOMAIN_IDS = list(DOMAINS.keys())
ALERTS_TOPIC = "city.alerts"

# ---------------------------------------------------------------------------
# Role-based access: which domains (dashboards) + topics each role may read.
# "city_admin" is the only role wired to every domain; every other role is
# scoped to the one operational area it owns. websocket_manager.py and the
# REST routes both check against this table, so permissions live in exactly
# one place.
# ---------------------------------------------------------------------------
ROLES = {
    "city_admin": {
        "label": "City Administrator",
        "domains": DOMAIN_IDS,
        "description": "Full visibility across all city systems and predictive alerts.",
    },
    "traffic_operator": {
        "label": "Traffic Operator",
        "domains": ["traffic"],
        "description": "Live congestion, incidents, and short-term traffic forecasts.",
    },
    "energy_manager": {
        "label": "Energy Manager",
        "domains": ["energy"],
        "description": "Grid load, renewable mix, and demand forecasting.",
    },
    "environment_officer": {
        "label": "Environment Officer",
        "domains": ["pollution"],
        "description": "Air quality monitoring and pollution anomaly alerts.",
    },
    "public_works_officer": {
        "label": "Public Works Officer",
        "domains": ["public_services"],
        "description": "Waste, water, and street infrastructure status.",
    },
}

# Simulator cadence (seconds between synthetic sensor ticks per zone/domain)
SENSOR_INTERVAL_SECONDS = 3
# How many historical points each in-memory series keeps
HISTORY_MAXLEN = 500
# Points of history the forecaster looks back on
FORECAST_LOOKBACK = 24
# Points of history the anomaly detector looks back on
ANOMALY_LOOKBACK = 20
