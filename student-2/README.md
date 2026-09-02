# Student 2 - Itinerary Planner

The Itinerary Planner turns a traveller's destination, dates, total budget, and interests into an editable day-by-day itinerary. It implements the Release 0 frontend -> backend -> Ollama -> approved LLM flow and falls back to a deterministic starter itinerary when the model is unavailable or invalid.

## Architecture

```text
Browser
	-> frontend (nginx, HTML/CSS/JavaScript)
  -> backend (Flask orchestration API)
	  -> shared Ollama / llama3.2:3b
	  -> database API (Flask)
		  -> SQLite /data/itinerary.db
```

Only the database API opens SQLite. The frontend calls only the backend through the same-origin `/itinerary-api/` proxy.

Release 0 planning, architecture, data design, risks, and evidence status are indexed in [`docs/README.md`](docs/README.md).

## Services

Open the feature through the unified application at `http://localhost:5100/itinerary/`. The shared home page at `http://localhost:5100` is the supported user entry point.

| Service | Host port | Health |
|---|---:|---|
| `student2-frontend` | 5102 | `http://localhost:5102/health` |
| `student2-backend` | 5202 | `http://localhost:5202/health` |
| `student2-database` | 5302 | `http://localhost:5302/health` |

These direct host ports are retained for service diagnostics and are not the normal browser route.

## APIs

- Trips: `GET/POST /api/trips`, `GET/PUT/DELETE /api/trips/{id}`
- Stops: `POST /api/trips/{id}/stops`, `PUT/DELETE /api/stops/{id}`
- AI adaptation: `POST /api/trips/{id}/regenerate`, `POST /api/stops/{id}/regenerate`
- Database CRUD mirrors these resources under `/api/data/`
- Atomic database operations: `POST /api/data/itineraries`, `PUT /api/data/trips/{id}/stops`

The SQLite schema contains `trips` and `trip_stops`. Startup initialization inserts 10 demonstration trips and 20 stops only when the trips table is empty.

## Run and Test

```powershell
docker compose up --build student2-database student2-backend student2-frontend shared-frontend
cd student-2/frontend; npm ci; npm test; cd ../..
cd student-2/backend; python -m pytest tests; cd ../..
cd student-2/database; python -m pytest tests; cd ../..
docker compose build student2-database student2-backend student2-frontend
```

CI installs Node 22 and Python 3.11 dependencies, runs the frontend Vitest suite and both pytest suites, validates Compose, builds all Student 2 plus shared frontend images, and smoke-tests the three Student 2 services without requiring a live model.
