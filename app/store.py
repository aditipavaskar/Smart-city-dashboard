"""
TimeSeriesStore — in-memory ring-buffer storage for sensor readings.

Narrow interface (append / latest / history) so this can be swapped for
TimescaleDB, InfluxDB, or a Kafka-topic-backed materialized view later
without touching sensors.py, predictive.py, or main.py — they only ever
call these three methods.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import HISTORY_MAXLEN


@dataclass
class Reading:
    domain: str
    zone: str
    metric: str
    value: float
    timestamp: str


class TimeSeriesStore:
    def __init__(self, maxlen: int = HISTORY_MAXLEN) -> None:
        self._maxlen = maxlen
        # (domain, zone, metric) -> deque[Reading]
        self._series: dict[tuple[str, str, str], deque[Reading]] = {}

    def append(self, domain: str, zone: str, metric: str, value: float) -> Reading:
        key = (domain, zone, metric)
        if key not in self._series:
            self._series[key] = deque(maxlen=self._maxlen)
        reading = Reading(
            domain=domain,
            zone=zone,
            metric=metric,
            value=round(value, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._series[key].append(reading)
        return reading

    def latest(self, domain: str, zone: str, metric: str) -> Reading | None:
        key = (domain, zone, metric)
        series = self._series.get(key)
        return series[-1] if series else None

    def latest_all_metrics(self, domain: str, zone: str, metric_names: list[str]) -> dict[str, Reading | None]:
        return {m: self.latest(domain, zone, m) for m in metric_names}

    def history(self, domain: str, zone: str, metric: str, limit: int = 50) -> list[Reading]:
        key = (domain, zone, metric)
        series = self._series.get(key)
        if not series:
            return []
        return list(series)[-limit:]

    def values_only(self, domain: str, zone: str, metric: str, limit: int = 50) -> list[float]:
        return [r.value for r in self.history(domain, zone, metric, limit)]


# Process-wide singleton store shared by the sensor simulator, REST routes,
# and the predictive engine.
store = TimeSeriesStore()
