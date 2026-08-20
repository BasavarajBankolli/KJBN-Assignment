# Demo Recording Script — Food Truck Finder

**Duration target:** 2–4 minutes. **Recommended tools:** OBS or Loom; 1080p, window capture of the browser + terminal side-by-side where noted.

---

## Script

### 0:00 – 0:20 · Intro & architecture (browser + terminal)

> "Hi, I'm Basavaraj Bankolli. This is Food Truck Finder — a web app that finds food trucks anywhere in San Francisco. The stack: a FastAPI Python backend that talks to the public DataSF Open Data portal, and a React + TypeScript frontend with a Leaflet map. No API keys needed — the data is live."

- Show `http://localhost:5173` loading, then briefly the backend terminal with request logs scrolling.

### 0:20 – 0:50 · Location-aware search

> "The app uses your GPS position to find nearby trucks. It gracefully handles denied location permission — here, we use a popular spot from the dropdown instead: Union Square."

- Click **Use my location** (allow), or select **Union Square** from the dropdown → Search.
- Call out the results list and map markers appearing **instantly** — "thanks to a 5-minute server-side cache, repeat searches are instant."

### 0:50 – 1:20 · Radius + food-type filtering with autocomplete

> "Narrow it down. I'll shrink the radius to 1 kilometer, and type 'taco' — notice the autocomplete suggestions are mined from the actual results, not hard-coded."

- Change radius to **1 km**, type `taco` in Food type, pick the suggestion → Search.
- Show the filtered list + markers updating together.

### 1:20 – 1:45 · List ↔ map synchronization

> "The two views are fully synchronized. Clicking a result card flies the map to that truck and opens its popup — and clicking a marker on the map highlights the matching card and scrolls it into view."

- Click a card → map flies, popup opens.
- Click a pin → card highlights.

### 1:45 – 2:05 · Resilience: error states

> "Let's see what happens when things break. I'll stop the backend — the app shows a friendly error with a Retry button, and no internal details leak. When the backend is back, Retry recovers instantly."

- Stop backend (Ctrl+C in terminal), click **Search** → error state.
- Restart backend, click **Retry** → results return.

### 2:05 – 2:25 · Mobile / responsive layout

> "The layout adapts: on a phone-width window, the map stacks on top and the search panel scrolls below."

- Narrow the browser window (DevTools device mode) → show stacked layout, map on top, tap a card.

### 2:25 – 2:50 · Tests + Docker (terminal)

> "Quality checks: 126 backend tests — unit tests, API tests, and mocked upstream integration tests — all green. And the whole stack is containerized: one command brings up the nginx frontend proxying to the FastAPI backend."

- `pytest -q` → "126 passed".
- `docker compose up --build` → show both containers healthy, open `http://localhost:8080`.

### 2:50 – 3:05 · Wrap-up

> "Docs: the README covers the API contract, architecture decisions, and deployment — the backend deploys to Render via the included blueprint, the frontend to Vercel. Thank you!"

- Briefly scroll the README (API table + deployment section).

---

## Tips

- Rehearse once against the real app; DataSF latency varies, so keep the first load (cache miss) early in the demo.
- If GPS permission popups are awkward on the recording, use the **Popular spots** dropdown — it is a designed feature, not a workaround.
- Keep the browser DevTools visible when resizing (2:05) to make the responsive claim obvious.
- Demo with the frontend dev server (`npm run dev`) and backend via `uvicorn`; the Retry demo needs the terminal within reach.