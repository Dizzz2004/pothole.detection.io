# Road Guardian Dashboard (React + TypeScript)

A small React + TypeScript rewrite of the Road Guardian dashboard's stats
view, talking to your real Flask backend (`/api/stats` and `/api/history`).
Built as a scoped, one-evening project to add real React/TypeScript
experience alongside the original Flask app.

The API types in `src/types.ts` are matched field-for-field against the
actual `app.py` (not guessed) — confirmed against:
- `GET /api/stats` → `images_processed`, `total_potholes_detected`,
  `severity_totals` (`Low`/`Medium`/`High`), `map_points`
- `GET /api/history` → `{ history: ScanRecord[] }`, where each record is
  one uploaded image (`filename`, `timestamp`, `total_detections`,
  `severity_counts`, nested `detections[]`)

## ⚠️ One thing I still couldn't verify

I built and typed this without network access, so **I haven't run
`npm install` or started this app myself.** Do that first and fix any
install hiccups before relying on it or demoing it.

## Setup

Needs the Flask backend running separately first.

```bash
# Terminal 1 — your existing Flask backend
cd pothole-detection-app/backend
python app.py          # runs on http://127.0.0.1:5000

# Terminal 2 — this React app
cd road-guardian-dashboard
npm install
npm run dev             # runs on http://localhost:5173
```

Open **http://localhost:5173**. Vite's dev server proxies `/api/*`
requests to Flask automatically (see `vite.config.ts`) — no CORS setup
needed on the Flask side (and your `app.py` doesn't have flask-cors
installed, so this matters).

## What this demonstrates

- React function components with hooks (`useState`, `useEffect`)
- TypeScript interfaces modeling a real backend's exact REST response
  shape, including nested objects and arrays
- Async data fetching with loading/error states (not just the happy path)
- Component composition (`StatCard`, `ScanRow` as typed, reusable
  children)
- A dev proxy config connecting a React frontend to a separately-running
  backend — the same pattern used when frontend and backend are
  genuinely different deployed services

## Extending further (optional, if you have more time)

- Add a route to drill into one scan and show its individual
  `detections[]` (lat/lng/severity/confidence) — good for a small
  "detail view" component
- Add a "clear history" button wired to `DELETE /api/history`
- Add the map view using `stats.map_points`
- Replace the plain CSS with Tailwind if the internship's stack uses it
