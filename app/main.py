from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.alerts import alert_store
from app.auth import issue_token, resolve_token
from app.config import DOMAINS, ROLES, ZONES, ZONE_IDS
from app.predictive import forecast
from app.schemas import LoginRequest, LoginResponse
from app.sensors import simulator
from app.store import store
from app.websocket_manager import stream_for_role


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(simulator.run_forever())
    yield
    simulator.stop()
    task.cancel()


app = FastAPI(title="Smart City Operations Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — restrict this for a real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_domain_access(role: str, domain: str) -> None:
    if domain not in ROLES[role]["domains"]:
        raise HTTPException(status_code=403, detail=f"role '{role}' cannot access domain '{domain}'")


def _require_role(role: str | None) -> str:
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="unknown or missing role")
    return role


# ---------------------------------------------------------------------------
# Auth / roles
# ---------------------------------------------------------------------------
@app.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"unknown role '{body.role}'")
    token = issue_token(body.role)
    role_cfg = ROLES[body.role]
    return LoginResponse(token=token, role=body.role, label=role_cfg["label"], domains=role_cfg["domains"])


@app.get("/roles")
def list_roles():
    return [{"id": rid, **cfg} for rid, cfg in ROLES.items()]


# ---------------------------------------------------------------------------
# City reference data
# ---------------------------------------------------------------------------
@app.get("/zones")
def list_zones():
    return ZONES


@app.get("/domains")
def list_domains():
    return [{"id": did, "label": cfg["label"], "metrics": cfg["metrics"]} for did, cfg in DOMAINS.items()]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@app.get("/metrics/{domain}/latest")
def metrics_latest(domain: str, role: str = Query(...), zone: str | None = Query(None)):
    _require_role(role)
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail="unknown domain")
    _require_domain_access(role, domain)

    zones = [zone] if zone else ZONE_IDS
    metric_names = list(DOMAINS[domain]["metrics"].keys())
    result = {}
    for z in zones:
        latest = store.latest_all_metrics(domain, z, metric_names)
        result[z] = {
            m: (None if r is None else {"value": r.value, "timestamp": r.timestamp})
            for m, r in latest.items()
        }
    return result


@app.get("/metrics/{domain}/history")
def metrics_history(
    domain: str,
    metric: str = Query(...),
    zone: str = Query(...),
    role: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
):
    _require_role(role)
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail="unknown domain")
    _require_domain_access(role, domain)
    if metric not in DOMAINS[domain]["metrics"]:
        raise HTTPException(status_code=404, detail="unknown metric")

    readings = store.history(domain, zone, metric, limit=limit)
    return [{"value": r.value, "timestamp": r.timestamp} for r in readings]


# ---------------------------------------------------------------------------
# Predictive analytics
# ---------------------------------------------------------------------------
@app.get("/predict/{domain}")
def predict(
    domain: str,
    metric: str = Query(...),
    zone: str = Query(...),
    role: str = Query(...),
    horizon: int = Query(6, ge=1, le=24),
):
    _require_role(role)
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail="unknown domain")
    _require_domain_access(role, domain)
    if metric not in DOMAINS[domain]["metrics"]:
        raise HTTPException(status_code=404, detail="unknown metric")

    result = forecast(domain, zone, metric, horizon=horizon)
    if result is None:
        raise HTTPException(status_code=409, detail="not enough history yet — try again shortly")
    return result


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
@app.get("/alerts")
def list_alerts(
    role: str = Query(...),
    domain: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    _require_role(role)
    if domain:
        _require_domain_access(role, domain)
        return alert_store.list(domain=domain, severity=severity, limit=limit)

    # No domain filter: restrict results to whatever the role can see.
    allowed = set(ROLES[role]["domains"])
    items = alert_store.list(domain=None, severity=severity, limit=limit * 2)
    return [a for a in items if a["domain"] in allowed][:limit]


# ---------------------------------------------------------------------------
# Real-time stream
# ---------------------------------------------------------------------------
@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket, token: str = Query(...)):
    role = resolve_token(token)
    if role is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        await stream_for_role(websocket, role)
    except WebSocketDisconnect:
        pass
