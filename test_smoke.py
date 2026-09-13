"""
Exercises every REST endpoint and the WebSocket stream through FastAPI's
TestClient, printing results as it goes. Run with:

    python test_smoke.py

Before hitting the predictive endpoints we manually drive the sensor
simulator a few dozen ticks (bypassing its normal 3-second cadence) so
there's enough history for a forecast without the test taking a minute.
"""
import asyncio
import json

from fastapi.testclient import TestClient

from app.config import DOMAINS, ROLES, ZONE_IDS
from app.main import app
from app.sensors import simulator


def seed_history(ticks: int = 30) -> None:
    async def _run():
        for _ in range(ticks):
            await simulator._tick_once()

    asyncio.run(_run())
    print(f"[seed] drove the simulator through {ticks} ticks")


def main() -> None:
    seed_history()

    with TestClient(app) as client:
        print("\n[1] GET /roles")
        r = client.get("/roles")
        assert r.status_code == 200
        print(json.dumps(r.json(), indent=2)[:400], "...")

        print("\n[2] GET /zones")
        r = client.get("/zones")
        assert r.status_code == 200
        assert len(r.json()) == len(ZONE_IDS)

        print("\n[3] GET /domains")
        r = client.get("/domains")
        assert r.status_code == 200
        assert {d["id"] for d in r.json()} == set(DOMAINS.keys())

        print("\n[4] POST /auth/login for every role")
        tokens = {}
        for role_id in ROLES:
            r = client.post("/auth/login", json={"role": role_id})
            assert r.status_code == 200, r.text
            tokens[role_id] = r.json()["token"]
            print(f"  {role_id}: token issued, domains={r.json()['domains']}")

        print("\n[5] Role scoping: traffic_operator cannot read the energy domain")
        r = client.get(
            "/metrics/energy/latest",
            params={"role": "traffic_operator"},
        )
        assert r.status_code == 403, r.text
        print("  got expected 403")

        print("\n[6] GET /metrics/{domain}/latest for city_admin across all domains")
        for domain in DOMAINS:
            r = client.get(f"/metrics/{domain}/latest", params={"role": "city_admin"})
            assert r.status_code == 200, r.text
            zone0 = ZONE_IDS[0]
            print(f"  {domain} @ {zone0}: {r.json()[zone0]}")

        print("\n[7] GET /metrics/traffic/history")
        r = client.get(
            "/metrics/traffic/history",
            params={"role": "traffic_operator", "zone": ZONE_IDS[0], "metric": "congestion_index", "limit": 10},
        )
        assert r.status_code == 200, r.text
        assert len(r.json()) > 0
        print(f"  got {len(r.json())} points")

        print("\n[8] GET /predict/traffic (forecast)")
        r = client.get(
            "/predict/traffic",
            params={"role": "traffic_operator", "zone": ZONE_IDS[0], "metric": "congestion_index", "horizon": 6},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["forecast"]) == 6
        print(f"  trend={body['trend']} forecast={body['forecast']}")

        print("\n[9] GET /alerts (city_admin sees all domains)")
        r = client.get("/alerts", params={"role": "city_admin"})
        assert r.status_code == 200, r.text
        print(f"  {len(r.json())} alerts recorded so far")

        print("\n[10] WebSocket /ws/stream for environment_officer")
        token = tokens["environment_officer"]
        with client.websocket_connect(f"/ws/stream?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["domain"] == "pollution", f"expected pollution-only stream, got {msg}"
            print(f"  received live message: {msg}")

        print("\n[11] WebSocket rejects an invalid token")
        try:
            with client.websocket_connect("/ws/stream?token=not-a-real-token"):
                raise AssertionError("expected the connection to be rejected")
        except Exception as e:  # starlette raises WebSocketDisconnect on close(4401)
            print(f"  rejected as expected ({type(e).__name__})")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
