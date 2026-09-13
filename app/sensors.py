"""
SensorSimulator — the "real-time data stream" source.

In a real deployment this module is replaced by actual IoT gateways /
Kafka producers pushing readings from traffic cameras, smart meters, and
air-quality stations. Here it synthesizes plausible, mildly-correlated
readings per zone so the rest of the pipeline (broker -> store ->
predictive -> websocket) can be built and demoed without real hardware.

Each tick:
  1. generates a new value per (domain, metric, zone)
  2. appends it to the TimeSeriesStore (so REST history/predict endpoints
     have data immediately)
  3. publishes it to the broker's domain topic (so WebSocket subscribers
     get it live)
  4. runs the anomaly detector and publishes any resulting alert
"""
from __future__ import annotations

import asyncio
import math
import random
import time
from dataclasses import dataclass

from app.alerts import alert_store
from app.broker import broker
from app.config import ALERTS_TOPIC, DOMAINS, SENSOR_INTERVAL_SECONDS, ZONE_IDS
from app.predictive import detect_anomaly
from app.store import store


@dataclass
class _MetricState:
    value: float
    phase: float


class SensorSimulator:
    def __init__(self) -> None:
        self._state: dict[tuple[str, str, str], _MetricState] = {}
        self._t0 = time.time()
        self._running = False
        self._seed_initial_state()

    def _seed_initial_state(self) -> None:
        seeds = {
            "congestion_index": 35.0, "avg_speed_kmh": 42.0, "incident_count": 0.0,
            "load_mw": 55.0, "renewable_pct": 40.0, "grid_stress_index": 30.0,
            "aqi": 80.0, "pm25": 30.0, "co2_ppm": 420.0,
            "waste_bin_fill_pct": 40.0, "water_pressure_psi": 55.0, "streetlight_fault_count": 1.0,
        }
        for domain, cfg in DOMAINS.items():
            for metric in cfg["metrics"]:
                for zone in ZONE_IDS:
                    key = (domain, zone, metric)
                    jitter = random.uniform(-8, 8)
                    self._state[key] = _MetricState(
                        value=max(0.0, seeds[metric] + jitter),
                        phase=random.uniform(0, math.tau),
                    )

    def _next_value(self, key: tuple[str, str, str]) -> float:
        """Random-walk + diurnal wave + occasional spike, clamped sensibly."""
        domain, zone, metric = key
        st = self._state[key]
        elapsed_minutes = (time.time() - self._t0) / 60.0

        # Diurnal-style wave so charts look alive rather than pure noise.
        wave = 6 * math.sin((elapsed_minutes / 12.0) + st.phase)
        drift = random.uniform(-2.5, 2.5)

        # Rare spike event to give the anomaly detector something to catch.
        spike = 0.0
        if random.random() < 0.02:
            spike = random.uniform(15, 40) * (1 if "count" not in metric else 3)

        new_value = st.value + drift + spike * 0.3 + wave * 0.1
        # Mean-reversion so series don't wander off forever
        target = {
            "congestion_index": 40, "avg_speed_kmh": 40, "incident_count": 1,
            "load_mw": 60, "renewable_pct": 38, "grid_stress_index": 35,
            "aqi": 85, "pm25": 32, "co2_ppm": 430,
            "waste_bin_fill_pct": 45, "water_pressure_psi": 55, "streetlight_fault_count": 1.5,
        }[metric]
        new_value += (target - new_value) * 0.05

        lower_bound = {"renewable_pct": 0, "avg_speed_kmh": 2, "water_pressure_psi": 5}.get(metric, 0)
        upper_bound = {"renewable_pct": 100, "congestion_index": 100, "aqi": 400}.get(metric, None)
        new_value = max(lower_bound, new_value)
        if upper_bound is not None:
            new_value = min(upper_bound, new_value)

        st.value = new_value
        return new_value

    async def _tick_once(self) -> None:
        for domain, cfg in DOMAINS.items():
            for metric, meta in cfg["metrics"].items():
                for zone in ZONE_IDS:
                    key = (domain, zone, metric)
                    value = self._next_value(key)
                    reading = store.append(domain, zone, metric, value)

                    await broker.produce(
                        cfg["topic"],
                        {
                            "domain": domain,
                            "zone": zone,
                            "metric": metric,
                            "value": reading.value,
                            "unit": meta["unit"],
                            "timestamp": reading.timestamp,
                        },
                        key=f"{zone}:{metric}",
                    )

                    alert = detect_anomaly(domain, zone, metric)
                    if alert is not None:
                        alert_store.add(alert)
                        await broker.produce(ALERTS_TOPIC, alert, key=zone)

    async def run_forever(self) -> None:
        self._running = True
        while self._running:
            await self._tick_once()
            await asyncio.sleep(SENSOR_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False


simulator = SensorSimulator()
