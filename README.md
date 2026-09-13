# AI-Driven Smart City Operations Dashboard

A full-stack, real-time operations platform for a city: a FastAPI backend
(simulated IoT sensor streams over a Kafka-style pub/sub, WebSocket push,
explainable predictive analytics) paired with a React + Vite frontend that
renders **role-based dashboards** — a traffic operator, an energy manager,
an environment officer, a public-works officer, and a city admin all see a
different slice of the same live city.

## Objective

Centralize monitoring of traffic, energy usage, pollution, and public
services into one platform, with real-time data streams, predictive
analytics, and dashboards scoped to who's looking at them.

## Why it's built this way

| Requirement (from the brief)      | Where it lives                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| Real-time data streams             | `app/broker.py` (Kafka-shaped pub/sub) + `app/sensors.py` (simulated producers) |
| Predictive analytics               | `app/predictive.py` — linear-trend forecast + z-score/threshold anomaly alerts  |
| Role-based dashboards              | `app/config.py: ROLES` + `app/websocket_manager.py` + `app/main.py` guards      |
| FastAPI                            | `app/main.py`                                                                   |
| WebSockets                         | `/ws/stream` endpoint, fanned in per-topic in `app/websocket_manager.py`        |
| React + Map UI                     | `src/components/CityMapView.jsx`, `src/components/DomainPanel.jsx`             |

Each concern is its own module with a narrow interface, the same principle
as the reference project this was modeled on:

- `app/broker.py` exposes exactly two methods — `produce()` / `subscribe()`
  — shaped like `aiokafka`'s producer/consumer API. Swapping the in-memory
  broker for a real Kafka cluster later means rewriting this one file;
  `sensors.py`, `websocket_manager.py`, and `main.py` never change.
- `app/store.py` exposes `append()` / `latest()` / `history()`. Swapping
  in-memory deques for TimescaleDB/InfluxDB is the same kind of one-file
  change.
- `app/config.py` is the single source of truth for domains, metrics,
  thresholds, zones, and role→domain permissions — nothing else hard-codes
  a metric name or a role's access list.

## Architecture

```
 IoT-style sensors           Kafka-shaped broker          Consumers
 (simulated per zone)   -->  (topic pub/sub)         -->  - TimeSeriesStore (REST history)
 app/sensors.py              app/broker.py                - Predictive engine (forecasts + alerts)
                                                            - WebSocket fan-out -> React dashboard
```

Every sensor tick is written to the in-memory store (so REST history /
predict endpoints have data immediately) **and** published onto the
broker's domain topic (so connected WebSocket clients get it live). The
anomaly detector runs on every tick and publishes to a shared alerts topic,
filtered per-connection to the domains a role can see.

## Backend setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: <http://127.0.0.1:8000/docs>

The sensor simulator starts automatically with the app (FastAPI lifespan
hook) and begins publishing readings for every zone/domain every few
seconds — no external Kafka broker or hardware needed to see live data.

## Verify the backend works

```bash
python test_smoke.py
```

Drives the simulator through 30 ticks (so there's enough history for a
forecast without waiting), then exercises every REST endpoint plus the
WebSocket stream through FastAPI's `TestClient`, including a check that a
`traffic_operator` token is rejected (403) when it tries to read the
energy domain.

## Frontend setup

```bash
npm install
npm run dev
```

Runs on <http://localhost:5173> by default and expects the backend at
`http://127.0.0.1:8000` (override with `VITE_API_BASE_URL` in a `.env`
file — see `.env.example`). `npm run build` produces a production bundle.

The frontend has three kinds of views, reachable from the left rail (which
only lists domains the signed-in role can see):

- **City Overview** — SVG map of all zones, each colored by the worst live
  severity across the role's visible domains
- **Per-domain dashboards** (Traffic / Energy / Pollution / Public
  Services) — a live stat grid per zone/metric; click a tile to load its
  predictive forecast chart below
- **Alerts** — live + historical predictive alerts, filterable by severity

Signing in is a role picker, not a real login (see `app/auth.py` — this is
a deliberately fake token issuer meant only to demonstrate role-scoped
data access; swap it for real JWT/SSO verification before deploying).

## Deploying the frontend to GitHub Pages

This repo includes `.github/workflows/deploy-pages.yml`, which builds the
frontend and publishes it to GitHub Pages automatically on every push to
`main`. GitHub Pages only serves static files, so this deploys the
**frontend only** — the FastAPI backend needs to run somewhere else (see
below) for the live dashboard to actually show data.

1. Push this repo to GitHub.
2. In the repo, go to **Settings → Pages** and set **Source** to
   **GitHub Actions** (not "Deploy from a branch").
3. **Deploy the backend somewhere that runs a persistent process** —
   GitHub Pages can't run `uvicorn`. Render, Railway, and Fly.io all have
   free tiers that work for a demo. Start command:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. In the backend's `app/main.py`, change the CORS `allow_origins` from
   `"*"` to your Pages URL (`https://<user>.github.io`) once you know it.
5. Back in the frontend repo, go to **Settings → Secrets and variables →
   Actions → Variables** and add a repository variable named
   `VITE_API_BASE_URL` set to your deployed backend's HTTPS URL (e.g.
   `https://your-backend.onrender.com`). The workflow bakes this into the
   build — without it, the deployed site falls back to
   `http://127.0.0.1:8000`, which doesn't exist for a visitor.
6. Push to `main` (or re-run the workflow from the **Actions** tab). Once
   it finishes, your site is live at
   `https://<user>.github.io/<repo-name>/`.

`vite.config.js` already sets `base: "./"` so the built asset paths resolve
correctly under that `/<repo-name>/` subpath — a hard-coded `base: "/"`
(Vite's default) is the most common reason a Pages deploy shows a blank
white page.

If you just want to see the UI without standing up a backend yet, it'll
still deploy and render the role-picker screen — it'll just show a "can't
reach the API" message until `VITE_API_BASE_URL` points at something real.

## API overview

- `POST /auth/login` — `{role}` → issues a demo token scoped to that role
- `GET /roles` — role catalog (label, description, visible domains)
- `GET /zones` — city zones with lat/lng (feeds the map view)
- `GET /domains` — domain catalog with each metric's unit + thresholds
- `GET /metrics/{domain}/latest?role=&zone=` — latest reading per metric
- `GET /metrics/{domain}/history?role=&zone=&metric=&limit=` — historical series
- `GET /predict/{domain}?role=&zone=&metric=&horizon=` — forecast + trend + confidence band
- `GET /alerts?role=&domain=&severity=` — recent predictive alerts
- `WS /ws/stream?token=` — live readings + alerts, scoped to the token's role

Every domain-scoped route checks the role against `app/config.py: ROLES`
and returns `403` if the role can't see that domain — this is enforced
server-side, not just hidden in the UI.

## Predictive analytics model

Two independent, explainable techniques (no opaque black-box model, so a
reviewer can see exactly why a number was produced):

1. **Forecast** (`app/predictive.py: forecast`) — ordinary least-squares
   linear trend over the last 24 readings, projected `horizon` steps
   ahead. Trend is labeled `worsening` / `improving` / `stable` by
   comparing the fitted slope's direction against whether that metric is
   configured as "higher is worse" (e.g. congestion) or "lower is worse"
   (e.g. water pressure). A ~95% confidence band comes from the residual
   standard deviation.
2. **Anomaly detection** (`app/predictive.py: detect_anomaly`) — fires on
   *either* a configured warn/critical threshold breach *or* a z-score
   outlier (|z| ≥ 3) against the recent rolling window, so both slow drift
   past a known-bad line and a sudden one-off spike get caught.

## Role matrix

| Role                    | Sees                          |
| ------------------------ | ------------------------------ |
| `city_admin`             | Traffic, Energy, Pollution, Public Services — everything |
| `traffic_operator`       | Traffic only |
| `energy_manager`         | Energy only |
| `environment_officer`    | Pollution only |
| `public_works_officer`   | Public Services only |

## Project layout

```
app/
  main.py                 FastAPI routes + WebSocket endpoint + lifespan startup
  config.py               Domains, metrics, thresholds, zones, role->domain permissions
  broker.py               In-memory Kafka-shaped pub/sub (produce/subscribe)
  sensors.py              Async simulator: generates readings, publishes to broker + store
  store.py                In-memory time-series ring buffer (append/latest/history)
  predictive.py           Linear-trend forecasting + z-score/threshold anomaly detection
  alerts.py               Rolling alert log, queryable by domain/severity
  auth.py                 Demo role-token issuance (NOT real auth — see docstring)
  websocket_manager.py    Fans broker topics into a client's WebSocket, scoped by role
  schemas.py              Pydantic request/response models
  data/zones.json         City zone definitions (id, name, lat/lng, population)
test_smoke.py             End-to-end backend test via FastAPI TestClient
requirements.txt

src/
  main.jsx                 React entry point
  App.jsx                  Auth gate, layout, view routing
  api.js                   REST fetch wrapper
  useCityStream.js          WebSocket hook: live readings/alerts + auto-reconnect
  index.css                 Design tokens (dark ops-room theme)
  components/
    RoleLogin.jsx            Role picker / demo sign-in
    Sidebar.jsx              Left nav, scoped to the signed-in role's domains
    CityMapView.jsx          SVG city map, zones colored by worst live severity
    DomainPanel.jsx          Per-domain live stat grid + forecast chart
    StatCard.jsx             Metric tile with severity badge
    PredictiveChart.jsx      Recharts line chart: history + forecast + confidence band
    AlertsFeed.jsx           Live + historical alert list, filterable by severity
package.json, vite.config.js, tailwind.config.js, postcss.config.js, index.html
```

## Extending this for a real deployment

- Swap `app/broker.py`'s `InMemoryBroker` for `aiokafka` (or another real
  Kafka client) behind the same `produce()`/`subscribe()` interface —
  see the docstring in that file for the exact mapping.
- Swap `app/store.py`'s in-memory deques for TimescaleDB/InfluxDB (same
  three-method interface: `append` / `latest` / `history`).
- Replace `app/auth.py`'s demo token issuer with real JWT verification
  against your identity provider (SSO, OAuth), keeping the same
  `issue_token` / `resolve_token` shape so nothing else changes.
- Replace `src/components/CityMapView.jsx`'s SVG projection with a real
  map SDK (react-leaflet, Google Maps, Mapbox GL) — the zone data shape
  (`id, name, lat, lng`) is already what those SDKs expect.
- Replace `app/sensors.py`'s synthetic generator with real ingestion from
  traffic cameras / smart meters / air-quality stations, publishing onto
  the same broker topics.
- Add rate limiting and restrict CORS `allow_origins` (currently `*` for
  local dev against the Vite dev server).
- Swap the linear-trend forecaster for a heavier time-series model
  (Prophet, ARIMA, or an LSTM) behind the same `forecast()` signature if
  longer-horizon accuracy matters more than explainability.
