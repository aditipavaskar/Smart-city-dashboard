"""
AlertStore — keeps a rolling log of predictive-engine alerts so the REST
API and newly-connecting WebSocket clients can see recent history, not
just alerts that happen to fire after they connect.
"""
from __future__ import annotations

from collections import deque

from app.predictive import Alert

_MAX_ALERTS = 200


class AlertStore:
    def __init__(self) -> None:
        self._alerts: deque[Alert] = deque(maxlen=_MAX_ALERTS)

    def add(self, alert: Alert) -> None:
        self._alerts.append(alert)

    def list(self, domain: str | None = None, severity: str | None = None, limit: int = 50) -> list[Alert]:
        items = list(self._alerts)
        if domain:
            items = [a for a in items if a["domain"] == domain]
        if severity:
            items = [a for a in items if a["severity"] == severity]
        return items[-limit:][::-1]  # most recent first


alert_store = AlertStore()
