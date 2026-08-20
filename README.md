# Food Truck Finder

A production-ready web application that helps you find food trucks in San Francisco near any location, built for the **KJBN Labs Python Backend Developer assignment**.

**Live data, no keys required.** The backend queries San Francisco's public Open Data portal (DataSF) for permitted mobile food facilities and serves them through a clean, documented API. A React + TypeScript frontend renders them on an interactive map.

---

## Problem Statement

> Build a web app that finds food trucks near a given location. The data is sourced from the public SF Food Truck dataset (DataSF).

The app must:
- Let users search by **location** (GPS or manual), **radius**, **food type**, and **free-text** query.
- Show results as a **list and on a map**, with truck details (name, food served, address, distance).
- Handle **errors gracefully** (bad input, upstream outage, timeouts) with a consistent error contract.
- Be **testable**, **documented**, **containerized**, and **deployable** to a simple cloud platform.

---

## Features

- **Geolocation search** — one click uses your current position as the search center (with graceful fallback when denied/unsupported).
- **Radius filtering** — 0.5–50 km around the center (default 2 km).
- **Food-type filter + autocomplete** — suggestions are mined live from the food keywords in the current results.
- **Free-text search** — matches truck names and food descriptions (case-insensitive).
- **Dual results view** — synchronized list and map:
  - Click a result card → map flies to the truck's pin and opens its popup.
  - Click a pin → the matching card highlights and scrolls into view.
- **Popular SF spots** — one-click search around Union Square, Ferry Building, Civic Center, Mission District, and Fisherman's Wharf (great for demos without GPS).
- **Responsive layout** — side-by-side panels on desktop, stacked (map on top) on mobile.
- **Resilient API** — upstream caching, timeouts, structured error envelopes, no stack traces leaked.

---

## Architecture

```
┌──────────────┐   HTTPS   ┌──────────────────┐   HTTPS    ┌────────────────────────────┐
│  React SPA   │ ────────▶ │  FastAPI backend │ ────────▶  │  DataSF Open Data portal  │
│  (Vite/TS)   │   JSON    │   (Python 3.12)  │   SODA     │  rqzj-sfat.json           │
└──────────────┘           └──────────────────┘            └────────────────────────────┘
      │                        │  ┌─────────────────┐
      │                        ├──│ TTL cache       │  (in-process, keyed by status)
      │                        │  └─────────────────┘
      │                        ├── Validation (Pydantic)
      │                        └── Error envelope  {"error": {code, message}}
```

- The browser **never talks to DataSF directly** — all requests flow through the backend, so the API contract, validation, caching, and error handling are enforced server-side.
- The backend fetches the approved-truck dataset from DataSF (SoQL `$where=status='APPROVED'`), caches it in-process for a configurable TTL, then filters by radius (Haversine), food type, and text **in-process** — so repeat searches are fast and cheap.
- In Docker Compose, nginx serves the SPA and **proxies `/api/` to the backend** (same-origin for the browser); standalone, the SPA calls `VITE_API_BASE_URL` directly with CORS enabled.

---

## Tech Stack

| Layer      | Technology |
|------------|-----------|
| Backend    | Python 3.12+, FastAPI, Pydantic v2, Pydantic Settings, httpx |
| Frontend   | React 18, TypeScript, Vite 8, Leaflet + react-leaflet 4 |
| Data       | DataSF Socrata SODA API (`rqzj-sfat.json`) |
| Testing    | pytest, pytest-asyncio, respx (126 backend tests) |
| Infra      | Docker + Docker Compose (nginx for the SPA) |
| Deploy     | Render (backend, Docker blueprint), Vercel (frontend) |

---

## Technology Decisions

1. **No API keys.** DataSF's SODA endpoint is public — no credentials, no rate-limit keys, zero setup friction.
2. **Server-side radius filtering with a status-keyed cache.** Fetch the ~500 approved trucks once per TTL, then filter in-process. This keeps DataSF traffic at ~1 request/TTL regardless of user volume while staying correct (the cache is invalidated by TTL, never by request).
3. **TTL over Redis/Memcached.** For a single-node assignment deployment, an in-process TTL cache (thread-safe, injectable clock, `CACHE_TTL_SECONDS=0` disables) avoids external infrastructure. A Redis swap is a clean one-file change if the app ever scales out.
4. **Haversine distance.** Accurate-enough great-circle distance for city-scale radii; pure-Python and unit-tested against known reference values.
5. **Pydantic v2 everywhere.** Query validation (`lat/lng/radius/foodType/search/limit/offset`) and response serialization happen at the boundary; internal state is plain, validated models.
6. **DataSF quirks handled explicitly.** All SODA fields arrive as strings; `latitude`/`longitude` may be missing; `locationdescription` is optional; `fooditems` is a colon-separated string; internal-only fields (`permit`, `status`, `schedule`) are never exposed.
7. **react-leaflet + custom SVG pins.** No heavyweight map SDKs or API keys (OSM tiles); markers are inline SVG with a highlighted/selected state, fly-to behavior, and popups.
8. **Strict TypeScript build.** `tsc` runs as part of `npm run build`, so the bundle never ships with type errors.
9. **Non-root containers.** Both images run as unprivileged users; the backend Dockerfile uses multi-stage-friendly layer caching and honors `$PORT` for platform injection.

---

## DataSF Integration

**Endpoint:** `https://data.sfgov.org/resource/rqzj-sfat.json` (Socrata SODA).

- Queried with SoQL `$where=status='APPROVED'` and `$limit=50000` (server-side filtering).
- Raw fields used: `objectid`, `applicant`, `facilitytype`, `locationdescription`, `address`, `latitude`, `longitude`, `fooditems`, `permit`, `status`, `schedule`.
- The client normalizes records into `FoodTruck` models; malformed records (missing coordinates, etc.) are **skipped, not fatal** — one bad row must not take down the feed.
- Upstream failures map to a stable error contract:
  - `DATASF_UNAVAILABLE` (502) — connection refused / non-2xx / empty payload.
  - `DATASF_TIMEOUT` (504) — upstream exceeds the configured timeout (default 10 s).
  - `DATASF_INVALID_RESPONSE` (502) — unexpected payload shape.

---

## API Documentation

Interactive docs at `http://localhost:8000/docs` (Swagger UI) or `/redoc`.

### `GET /api/v1/health`
Liveness probe.

```json
{ "status": "ok", "app": "Food Truck Finder API", "version": "1.0.0", "environment": "development" }
```

### `GET /api/v1/food-trucks`
Finds permitted food trucks near a location.

**Query parameters**

| Parameter   | Type    | Required | Default | Bounds          | Description |
|-------------|---------|----------|---------|-----------------|-------------|
| `lat`       | float   | **yes**  | —       | -90 … 90        | Center latitude |
| `lng`       | float   | **yes**  | —       | -180 … 180      | Center longitude |
| `radiusKm`  | float   | no       | `2`     | 0.1 … 50        | Search radius |
| `foodType`  | string  | no       | —       | ≤ 64 chars      | Case-insensitive keyword in food items |
| `search`    | string  | no       | —       | ≤ 64 chars      | Case-insensitive match on name/food |
| `limit`     | int     | no       | `20`    | 1 … 100         | Max results |
| `offset`    | int     | no       | `0`     | ≥ 0             | Pagination offset |

**Success response — `200 OK`**

```json
{
  "total": 36,
  "limit": 20,
  "offset": 0,
  "radius_km": 2.0,
  "center": { "latitude": 37.7879, "longitude": -122.4075 },
  "trucks": [
    {
      "id": "1500074",
      "applicant": "San Francisco's Hometown Creamery",
      "facility_type": "Truck",
      "location_description": "MISSION ST: ...",
      "address": "1 MISSION ST",
      "latitude": 37.79325,
      "longitude": -122.39412,
      "food_items": "Ice cream: frozen custard: ...",
      "distance_m": 174.3
    }
  ]
}
```

**Error responses** — always `{"error": {"code": "...", "message": "..."}}`:

| HTTP | Code | Meaning |
|------|------|---------|
| 422  | `INVALID_LOCATION` | Missing/out-of-range `lat` or `lng` |
| 422  | `INVALID_RADIUS` | `radiusKm` outside 0.1–50 |
| 422  | `INVALID_PAGINATION` | `limit` outside 1–100 or negative `offset` |
| 502  | `DATASF_UNAVAILABLE` | DataSF unreachable or returned garbage |
| 504  | `DATASF_TIMEOUT` | DataSF exceeded the timeout |
| 500  | `INTERNAL_ERROR` | Unexpected server error (details logged, never leaked) |

### cURL examples

```bash
# Health
curl http://localhost:8000/api/v1/health

# Trucks within 1 km of Union Square
curl "http://localhost:8000/api/v1/food-trucks?lat=37.7879&lng=-122.4075&radiusKm=1&limit=10"

# Tacos within 2 km of the Ferry Building, page 2
curl "http://localhost:8000/api/v1/food-trucks?lat=37.7955&lng=-122.3937&foodType=taco&search=&limit=20&offset=20"

# Validation error envelope
curl -i "http://localhost:8000/api/v1/food-trucks?lat=999&lng=0"
# HTTP/1.1 422
# {"error":{"code":"INVALID_LOCATION","message":"Latitude must be between -90 and 90."}}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Runtime environment label |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `DATASF_BASE_URL` | `https://data.sfgov.org/resource/rqzj-sfat.json` | Upstream SODA dataset URL |
| `DATASF_TIMEOUT_SECONDS` | `10` | Upstream request timeout |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL; `0` disables caching |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins (docker-compose overrides this to include `http://localhost:8080`) |
| `VITE_API_BASE_URL` *(frontend)* | `http://localhost:8000` | Backend URL baked in at build time; empty = same-origin |

All backend variables have sane defaults (see `backend/.env.example`); the app runs without any configuration.

---

## Local Setup

### Prerequisites
Python 3.12+, Node 20+, npm (Vite 8).

### Backend

```bash
cd backend
python -m venv .venv                 # or reuse the repo-root .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
# macOS/Linux: .venv/bin/python -m pip install -e ".[dev]"
.venv\Scripts\python -m uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Testing

```bash
cd backend
.venv\Scripts\python -m pytest -q        # 126 tests
.venv\Scripts\python -m pytest -q -m "not integration"   # offline-safe subset
```

---

## Docker

```bash
docker compose up --build
# Frontend  → http://localhost:8080  (nginx, proxies /api/ to the backend)
# Backend   → http://localhost:8000  (FastAPI, healthcheck-gated startup)
docker compose down
```

- The backend image is Python 3.12-slim, runs as a non-root user, and honors `$PORT` (Render/Railway/Fly).
- The frontend image is a two-stage build: `node:22-alpine` compiles, `nginx:1.27-alpine` serves the SPA with a `/api/` reverse proxy — browsers never hit CORS in the Docker setup.

---

## Deployment

### Backend → Render (blueprint included)

`render.yaml` at the repo root defines the `food-truck-finder-backend` service (Docker runtime, `rootDir: backend`, health check on `/api/v1/health`).

1. Push the repo to GitHub.
2. In Render: **New → Blueprint** → select the repo.
3. Set `CORS_ORIGINS` to your deployed frontend origin (the blueprint already points at `https://food-truck-finder.vercel.app`).

Alternatives: Railway or Fly.io both accept the same `backend/Dockerfile` directly (Fly: `fly launch` and set `PORT`).

### Frontend → Vercel

`frontend/vercel.json` provides the SPA fallback rewrite.

1. In Vercel: **Add New → Project** → import the repo, set **Root Directory** to `frontend`.
2. Framework preset: **Vite** (build `npm run build`, output `dist`).
3. Environment variable: `VITE_API_BASE_URL=https://<your-backend>.onrender.com`.
4. Deploy. The React app calls the backend cross-origin; CORS must list the Vercel origin.

---

## Logging, Errors & Caching

- **Logging** — structlog-style key-value records (`app.core.logging`): timestamp, level, event, extra context; request logs include method, path, status, duration. Logs go to stdout (container-friendly).
- **Errors** — every failure path returns the `{"error": {code, message}}` envelope. Validation errors carry the offending field name; upstream errors are mapped to 502/504; the last-resort handler logs the traceback server-side and returns a generic message — **no internals ever leak to clients**.
- **Caching** — in-process `TTLCache` (thread-safe, clock-injectable) keyed by dataset+status, e.g. `datasf:food_trucks:status=APPROVED`. Expiry is exact (`set_time + ttl`); `CACHE_TTL_SECONDS=0` bypasses. Filters (radius/food/text/pagination) run per-request over the cached snapshot, so results are always consistent within a TTL window.

---

## Project Structure

```
backend/
  app/
    api/            routes (health, food-trucks), router, dependencies
    clients/        DataSF SODA client (httpx)
    core/           config (Pydantic Settings), logging, TTL cache
    exceptions/     error taxonomy
    schemas/        Pydantic models (query, api, food truck, health)
    services/       food-truck service: caching, Haversine, filter + pagination
    main.py         app factory, lifespan, error handlers
  tests/            126 tests (unit + respx-mocked integration)
  Dockerfile, pyproject.toml, requirements.txt
frontend/
  src/
    api/            typed HTTP client
    components/     Header, SearchPanel, TruckList, MapView
    config/         env access (VITE_API_BASE_URL, defaults)
    hooks/          useGeolocation
    types/          API types
    App.tsx         state orchestration (query, fetch, map/list sync)
  Dockerfile, nginx.conf, vercel.json
docker-compose.yml   full stack (backend + nginx-frontend)
render.yaml          Render blueprint for the backend
```

---

## Trade-offs & Limitations

- **Cache granularity** — one cached snapshot for the whole approved dataset: correct and simple, but a fresh DataSF pull is needed for the newest permits; TTL trades freshness for cost (acceptable for this dataset's cadence).
- **No database** — the dataset (~500 rows) fits comfortably in memory; no persistence layer is required by the assignment. State is ephemeral per container.
- **Single-node assumption** — the in-process cache is per-instance; horizontal scaling would need a shared cache (one-file swap to Redis).
- **No authentication** — the API is intentionally public/read-only, consistent with the assignment scope.
- **Free-tier deployment limits** — cold starts and sleep policies on Render free tier; OSM tile usage depends on the provider's terms.
- **Data is as-is from DataSF** — some records lack coordinates or have sparse food descriptions; those are skipped or surface as limited result cards.

---

## Future Improvements

- Vegetarian/vegan and allergen-aware filters (needs structured food metadata).
- Opening-hours awareness using the `schedule` field (currently excluded from the API).
- Server-side result pagination with "load more" and radius-aware sorting UI.
- Shared Redis cache + multi-instance backend behind a load balancer.
- Health-score metric endpoint (cache hit rate, upstream latency percentiles).
- PWA: installable, offline tile cache, periodic refresh notifications.
- Rate limiting and API-key auth if the API is exposed beyond the demo.

---

## Developer

**Basavaraj Bankolli** — Python Backend Developer

- GitHub: https://github.com/BasavarajBankolli
- LinkedIn: https://www.linkedin.com/in/basavaraj-bankolli/
- Portfolio: https://basavarajp.vercel.app/