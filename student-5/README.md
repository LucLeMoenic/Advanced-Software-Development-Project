# Student 5 - Travel Logistics & Advisory Service

Alex Chen. Weather, entry requirements, transit options and grounded AI packing
advisories for a destination.

Three microservices:

| Service | Stack | Container : host | Role |
| --- | --- | --- | --- |
| `student5-frontend` | nginx + static HTML + HTMX | `80` : `5105` | The page, and a same-origin proxy for `/ui/` and `/api/` |
| `student5-backend` | Python 3.11, Flask | `8080` : `5205` | JSON passthrough, HTMX fragments, the AI advisory workflow |
| `student5-database` | Python 3.11, Flask, SQLite | `8080` : `5305` | The only service that opens `logistics.db` |

```text
Browser -> student5-frontend -> student5-backend -> student5-database -> SQLite
                                      \-> ollama (:11434) -> tag from APPLICATION_MODEL
```

**The rule that shapes the design: no service opens another service's SQLite
file.** The backend has no `sqlite3` import; every read and write travels over
HTTP.

## Documentation

Start with [`docs/context.md`](docs/context.md) - a one-page orientation for
anyone working on this feature.

| Document | Contents |
| --- | --- |
| [context.md](docs/context.md) | Orientation: goal, scope, contracts, code boundaries, where things live |
| [requirements.md](docs/requirements.md) | 10 functional requirements mapped to real endpoints and UI elements, 5 testable non-functional requirements |
| [feature-plan.md](docs/feature-plan.md) | The build as executed, status per deliverable, decisions and why |
| [architecture.md](docs/architecture.md) | Runtime topology diagram, one paragraph per service, the AI workflow path |
| [data-design.md](docs/data-design.md) | Conceptual model, ER diagram, logical design, physical notes and seeding |
| [risk-plan.md](docs/risk-plan.md) | Six risks with likelihood, impact, mitigation and status |
| [sprint-backlog.md](docs/sprint-backlog.md) | Backlog items with requirement links and status |
| [prompt-log.md](docs/prompt-log.md) | All four agentic-loop attempts, three of which failed |
| [review-record.md](docs/review-record.md) | The completed Plan/Act/Observe/Adapt run and the human decision |
| [prompt-engineering.md](docs/prompt-engineering.md) | The reviewer-prompt defect, the fix, the residual limitation, context management |
| [testing-evidence.md](docs/testing-evidence.md) | Every evidence file, what it proves, exact reproduction commands |
| [known-issues.md](docs/known-issues.md) | Honest limitations of the delivered feature |
| [contribution-log.md](docs/contribution-log.md) | Commits and pull requests, by date |

Supporting material: [`docs/evidence/`](docs/evidence) - seventeen artefacts
covering the agentic-loop run, both pytest suites, the image build, the healthy
Compose stack, the green CI run and four screenshots of the running application,
each one indexed in [testing-evidence.md](docs/testing-evidence.md) - and
[`docs/prompt-library/reviewer-llama32-v2.md`](docs/prompt-library/reviewer-llama32-v2.md)
(the custom reviewer prompt).

## Run it

From the repository root:

```bash
docker compose up --build student5-database student5-backend student5-frontend ollama ollama-model-setup
```

Then open **<http://localhost:5105/>**.

`ollama` and `ollama-model-setup` are only needed for the **Generate advisory**
button. The weather, visa and transit panels and all destination CRUD work
without them:

```bash
docker compose up --build student5-database student5-backend student5-frontend
```

Health checks (use `curl.exe` on Windows PowerShell):

```bash
curl http://localhost:5305/health && curl http://localhost:5205/health && curl http://localhost:5105/health
```

## Run the tests

**Run the two suites separately.** Both services have a module named `app`, so a
single combined invocation collides on import.

```bash
cd student-5/database && python -m pytest tests
```

```bash
cd student-5/backend && python -m pytest tests
```

Expected: 26 and 68 tests respectively. Both run offline - the database suite
gives each test its own `tmp_path` database, and the backend suite mocks the
database service and Ollama with `responses`.

Dependencies:

```bash
pip install -r student-5/database/requirements.txt -r student-5/backend/requirements.txt
```

CI runs both suites, `docker compose config --quiet`, and a build of all three
images on every push touching `student-5/**` - see
[`.github/workflows/student-5.yml`](../.github/workflows/student-5.yml).

## Configuration

Everything environment-driven; nothing secret is committed.

| Service | Variable | Default | Purpose |
| --- | --- | --- | --- |
| backend | `DATABASE_API_URL` | `http://student5-database:8080` | Database service base URL |
| backend | `OLLAMA_URL` | `http://ollama:11434` | Shared Ollama runtime |
| backend | `APPLICATION_MODEL` | `llama3.2:3b` | Model tag for advisories. No model name is a literal in calling code |
| database | `DATABASE_PATH` | `/data/logistics.db` | SQLite file, bind-mounted from `database/storage` |
| database / backend | `PORT` | `8080` | Listen port |

## The AI advisory workflow

The marked path is `Frontend -> Backend/API -> Ollama -> LLM`. The browser never
calls Ollama. Before the model is asked anything, `backend/advisory.py` pulls the
destination row, its weather notes and its transit options from the database
service and pastes them into the prompt verbatim; the model's job is to turn
stored facts into advice, not to recall them.

```bash
curl -X POST http://localhost:5205/api/advisory -H "Content-Type: application/json" -d "{\"destination_id\":1,\"month\":\"October\",\"interests\":\"hiking, street food\"}"
```

A cold 3B model on CPU can take well over a minute on the first call.

## Database API

Owns the SQLite database and exposes it over HTTP. It is the only service that
talks to SQLite directly. The backend mirrors these shapes at
`http://localhost:5205/api/...`, so the frontend could be pointed at either.

### Layout

| File | Purpose |
| --- | --- |
| `database/app.py` | Flask application factory and all routes |
| `database/schema.sql` | `destinations`, `weather_notes`, `transit_options` |
| `database/seed.sql` | 12 destinations, 14 weather notes, 14 transit options |
| `database/tests/` | pytest suite using the Flask test client |

On startup the service creates the schema if it is missing and runs the seed
**only when the `destinations` table is empty**, so restarting the container
against an existing volume never duplicates rows.

### Endpoints

All requests and responses are JSON. Errors are `{"error": "<message>"}` with an
appropriate status code.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | Liveness probe |
| GET | `/api/destinations` | List all destinations |
| POST | `/api/destinations` | `201` + created row; `400` if required fields are missing |
| GET | `/api/destinations/<id>` | `404` if absent |
| PUT | `/api/destinations/<id>` | `200` + updated row; `404` if absent |
| DELETE | `/api/destinations/<id>` | `204`; cascades to weather notes and transit options |
| GET | `/api/weather-notes` | Accepts `?destination_id=<int>` |
| POST | `/api/weather-notes` | `400` if `destination_id` does not exist |
| GET/PUT/DELETE | `/api/weather-notes/<id>` | Same pattern as destinations |
| GET | `/api/transit-options` | Accepts `?destination_id=<int>` |
| POST | `/api/transit-options` | `400` if `destination_id` does not exist |
| GET/PUT/DELETE | `/api/transit-options/<id>` | Same pattern as destinations |

**Fields**

- `destinations`: `country` and `visa_requirement` are required, `notes` is optional.
  `visa_requirement` uses the values `visa-free`, `visa-on-arrival`, `eVisa`,
  `embassy-visa`.
- `weather_notes`: `destination_id`, `season`, `notes` - all required.
- `transit_options`: `destination_id`, `type`, `details` - all required.
  `type` uses the values `metro`, `rail`, `bus`, `rideshare`, `ferry`, `airport-link`.

**`PUT` is a partial merge.** Any writable column left out of the request body
keeps its current value, so the backend can update a single field without
re-sending the whole row:

```bash
curl -X PUT localhost:5305/api/destinations/12 -H "Content-Type: application/json" -d "{\"visa_requirement\":\"eVisa\"}"
```

Supplied values are still validated, and `destination_id` is checked against
`destinations` on both `POST` and `PUT` (`400` if it does not exist).

### Backend fragment endpoints

Server-rendered HTML for the HTMX frontend. These answer `200` even when
something went wrong, because HTMX does not swap a non-2xx response and a silent
no-swap is the worst possible feedback; the JSON API above keeps the honest
status codes.

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/ui/destinations/options` | `<option>` list for the destination `<select>` |
| GET | `/ui/weather?destination_id=N` | Weather notes as a definition list |
| GET | `/ui/visa?destination_id=N` | Visa requirement callout plus entry notes |
| GET | `/ui/transit?destination_id=N` | Transit options as a table |
| GET | `/ui/destinations/table` | Manage table with per-row edit and delete controls |
| POST | `/ui/destinations` | Creates, then returns the refreshed table |
| POST | `/ui/destinations/<id>` | Saves inline edits, then returns the refreshed table |
| POST | `/ui/destinations/<id>/delete` | Deletes, then returns the refreshed table |
| POST | `/ui/advisory` | The advisory as `<article class="advisory-result">` |

## Run a service on its own

```bash
cd student-5/database
pip install -r requirements.txt
DATABASE_PATH=./storage/logistics.db python app.py
```

If port 8080 is taken, add `PORT=8085`.

```bash
docker build -t student5-database student-5/database
docker run --rm -p 5305:8080 -v student5_db:/data student5-database
```

The image is based on `python:3.11-slim`, which ships without `curl` or `wget`,
so the `HEALTHCHECK` uses Python's `urllib` to poll `/health`.

---

> The advisory text in `seed.sql` is illustrative sample data for the
> assignment. Real visa and border requirements change frequently and must be
> checked against Smartraveller and the destination government before travel.
