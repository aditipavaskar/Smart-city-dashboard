"""
Predictive analytics layer.

Two independent, explainable techniques — deliberately simple ones, so a
reviewer can see exactly why a number was produced instead of trusting an
opaque model:

  - forecast(): ordinary least-squares linear trend over the last
    FORECAST_LOOKBACK readings, projected `horizon` steps ahead, with a
    naive confidence band derived from residual std-dev. Good enough for
    "is this metric trending up or down over the next few minutes" — the
    actual use case for an ops dashboard — without pulling in a heavier
    forecasting library.

  - detect_anomaly(): flags a reading when EITHER (a) it crosses the
    domain's configured warn/critical threshold, or (b) it's a statistical
    outlier (z-score) versus the recent rolling window. Two independent
    checks catch both "slow drift past a known-bad line" and "sudden
    one-off spike still inside normal range".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

import numpy as np

from app.config import ANOMALY_LOOKBACK, DOMAINS, FORECAST_LOOKBACK
from app.store import store


class ForecastResult(TypedDict):
    domain: str
    zone: str
    metric: str
    history: list[float]
    forecast: list[float]
    trend: str  # "rising" | "falling" | "stable"
    confidence_band: float


def forecast(domain: str, zone: str, metric: str, horizon: int = 6) -> ForecastResult | None:
    values = store.values_only(domain, zone, metric, limit=FORECAST_LOOKBACK)
    if len(values) < 5:
        return None

    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)

    # Ordinary least squares: y = slope * x + intercept
    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (slope * x + intercept)
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    future_x = np.arange(len(values), len(values) + horizon, dtype=float)
    predicted = slope * future_x + intercept

    meta = DOMAINS[domain]["metrics"][metric]
    lower_bound = {"renewable_pct": 0, "avg_speed_kmh": 0, "water_pressure_psi": 0}.get(metric, 0)
    predicted = np.clip(predicted, lower_bound, None)

    if abs(slope) < 0.05:
        trend = "stable"
    elif (slope > 0) == meta["higher_is_worse"]:
        trend = "worsening"
    else:
        trend = "improving"

    return {
        "domain": domain,
        "zone": zone,
        "metric": metric,
        "history": [round(v, 2) for v in values],
        "forecast": [round(v, 2) for v in predicted.tolist()],
        "trend": trend,
        "confidence_band": round(residual_std * 1.96, 2),  # ~95% band
    }


class Alert(TypedDict):
    domain: str
    zone: str
    metric: str
    value: float
    severity: str  # "warning" | "critical"
    reason: str
    timestamp: str


def detect_anomaly(domain: str, zone: str, metric: str) -> Alert | None:
    meta = DOMAINS[domain]["metrics"][metric]
    latest = store.latest(domain, zone, metric)
    if latest is None:
        return None
    value = latest.value

    # --- Rule-based threshold check -------------------------------------
    severity = None
    reason = None
    worse = meta["higher_is_worse"]
    if worse and value >= meta["critical"] or (not worse and value <= meta["critical"]):
        severity, reason = "critical", f"{metric.replace('_', ' ')} crossed the critical threshold"
    elif worse and value >= meta["warn"] or (not worse and value <= meta["warn"]):
        severity, reason = "warning", f"{metric.replace('_', ' ')} crossed the warning threshold"

    # --- Statistical outlier check ---------------------------------------
    window = store.values_only(domain, zone, metric, limit=ANOMALY_LOOKBACK)
    if len(window) >= 8 and severity is None:
        arr = np.array(window[:-1], dtype=float)  # exclude current reading
        mean, std = float(np.mean(arr)), float(np.std(arr))
        if std > 1e-6:
            z = (value - mean) / std
            if abs(z) >= 3.0:
                severity = "critical" if abs(z) >= 4.0 else "warning"
                reason = f"statistical spike (z={z:.1f}) versus recent trend"

    if severity is None:
        return None

    return {
        "domain": domain,
        "zone": zone,
        "metric": metric,
        "value": value,
        "severity": severity,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
