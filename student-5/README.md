# Student 5 Microservices

Travel Logistics & Advisory Service.

- frontend: static files
- backend: Flask API
- database: Flask + SQLite JSON API (see below)

## Database service

Owns the SQLite database for the travel logistics service and exposes it over
HTTP. It is the only service that talks to SQLite directly - the backend
consumes these endpoints rather than opening the database file itself.

Stack: Python 3.11, Flask, SQLite (`sqlite3` from the standard library), pytest.

### Layout

| File | Purpose |
| --- | --- |
| `database/app.py` | Flask application factory and all routes |
| `database/schema.sql` | `destinations`, `weather_notes`, `transit_options` |
| `database/seed.sql` | 12 destinations, 14 weather notes, 14 transit options |
| `database/tests/` | pytest suite using the Flask test client |

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_PATH` | `/data/logistics.db` | SQLite file location |
| `PORT` | `8080` | Port the service listens on (host `0.0.0.0`) |

On startup the service creates the schema if it is missing and runs the seed
**only when the `destinations` table is empty**, so restarting the container
against an existing volume never duplicates rows.

### Run locally

```bash
cd student-5/database
pip install -r requirements.txt
DATABASE_PATH=./storage/logistics.db python app.py
```

Then, from another terminal:

```bash
curl localhost:8080/health              # {"status":"ok","service":"student5-database"}
curl localhost:8080/api/destinations    # 12 rows
```

If port 8080 is already taken on your machine, start it on another port with
`PORT=8085 DATABASE_PATH=./storage/logistics.db python app.py`.

### Run the tests

From the repository root:

```bash
pytest student-5/database/tests -q
```

Each test gets its own SQLite file via pytest's `tmp_path` fixture, so the
suite never touches `/data` or your local `storage/` directory.

### Run in Docker

```bash
docker build -t student5-database student-5/database
docker run --rm -p 5305:8080 -v student5_db:/data student5-database
```

The image is based on `python:3.11-slim`, which ships without `curl` or `wget`,
so the `HEALTHCHECK` uses Python's `urllib` to poll `/health`.

### API

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
curl -X PUT localhost:8080/api/destinations/12 \
  -H "Content-Type: application/json" \
  -d '{"visa_requirement":"eVisa"}'
```

Supplied values are still validated, and `destination_id` is checked against
`destinations` on both `POST` and `PUT` (`400` if it does not exist).

> The advisory text in `seed.sql` is illustrative sample data for the
> assignment. Real visa and border requirements change frequently and must be
> checked against Smartraveller and the destination government before travel.
