# Local Experience & Attraction Recommender Requirements

## 1. Purpose and Scope

The Local Experience & Attraction Recommender helps a traveller browse local attractions (sights, restaurants, activities), read and leave reviews, and receive an AI-suggested attraction matched to a free-text description of their interests. Recommendations are grounded in the seeded attraction catalogue only — the model is instructed to recommend exclusively from attractions actually returned by the database, never to invent places.

Release 0 delivers one integrated, containerised feature through the required path:

`HTMX + HTML/CSS frontend -> Flask backend/API -> Flask database API -> SQLite`

Full RAG-based grounding over a curated destination knowledge base is explicitly **Release 1 scope** per the Group 45 registration form; Release 0 uses closed-context prompting only (the backend limits the model to attractions its own query returned).

The feature must run from the team's shared `docker-compose.yml`, be reachable from the unified home page, use the shared CSS theme, and provide demonstrable Create, Read, Update, and Delete operations through both the frontend and the backend/database APIs.

### 1.1 Release 0 In Scope

- Browse and filter attractions by category (sight / restaurant / activity).
- Full CRUD on attractions through the frontend (browse/filter, add, edit, delete) and backend/API.
- Review submission per attraction (create), with reviews readable via the attraction detail response.
- AI-Mode recommendation endpoint driven by a free-text interest description, using Ollama and an approved LLM (Qwen), implementing an explicit Plan → Act → Observe → Adapt loop with a deterministic fallback.
- At least 10 seeded attraction records (12 seeded) and at least 10 seeded reviews (14 seeded).
- Independently containerised frontend, backend, and database services.
- Integration with the shared Ollama service, home page, theme, Compose stack, and `student-3.yml` workflow.
- Tests, logs, diagrams, and evidence required by the Release 0 rubric.

### 1.2 Release 0 Out of Scope

- RAG-based grounding over a curated destination knowledge base (Release 1).
- MCP tool calls, multi-agent review, and cloud deployment (Release 1/2).
- Review update/delete (only create/list are required for Release 0; the feature's primary CRUD resource is the attraction, not the review).
- Real itinerary persistence — the "Add to itinerary" action is an intentional Release 0 stub that logs the request; full itinerary wiring is Student 1's feature and a later-release integration point.

## 2. Actors and System Boundaries

| Actor or system | Responsibility |
|---|---|
| Traveller | Browses/filters attractions, manages attraction records, leaves reviews, and requests an AI recommendation. |
| HTMX frontend service (`student3-frontend`) | Renders the browse/filter UI, the manage (create/edit/delete) UI, the review form, and the AI recommendation form. Sends browser requests only to the backend service. |
| Flask backend/API service (`student3-backend`) | Validates and proxies attraction/review CRUD to the database service, and owns the `/api/recommend` Plan → Act → Observe → Adapt loop against Ollama. Never opens SQLite directly. |
| Flask database API service (`student3-database`) | Owns `attractions.db`, the `attractions`/`reviews` schema, and exposes CRUD over HTTP at `/api/data/*`. |
| SQLite (`attractions.db`) | Stores the attraction catalogue and reviews. No other service may open the file directly. |
| Shared Ollama service | Hosts the approved LLM tag (`qwen2.5:3b`, configurable via `STUDENT3_MODEL`) used by the recommendation loop. |
| Shared home page | Provides the integrated entry point to this feature. |

## 3. Functional Requirements

### 3.1 Attraction Browse and Filter

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | The traveller can list all attractions or filter by category. | `GET /api/attractions` and `GET /api/attractions?category=<sight\|restaurant\|activity>` both return the matching set; the frontend's All/Sights/Restaurants/Activities buttons drive this without a page reload. |
| FR-02 | The traveller can view a single attraction, including its reviews. | `GET /api/attractions/{id}` returns 404 for a missing ID; the database API additionally embeds the attraction's reviews in `GET /api/data/attractions/{id}`. |

### 3.2 Attraction CRUD (frontend + backend + database)

| ID | CRUD | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-03 | Create | The traveller can add a new attraction through the UI. | The "Add an Attraction" form validates name and category as required client-side and server-side; `POST /api/attractions` returns 201 with the created record; a missing name/category returns 400 with `{"error":"validation_error", ...}`; the new attraction appears in the list without a full page reload. |
| FR-04 | Read | Covered by FR-01/FR-02. | — |
| FR-05 | Update | The traveller can edit an existing attraction through the UI. | Clicking "Edit" swaps the card for an inline form pre-filled with current values; `PUT /api/attractions/{id}` returns 200 with the updated record or 404 for a missing ID; the card reflects the change without a full reload. |
| FR-06 | Delete | The traveller can delete an attraction through the UI. | Clicking "Delete" prompts for confirmation; `DELETE /api/attractions/{id}` returns 204, or 404 if already deleted; the card is removed from the list; deleting an attraction also removes its reviews (enforced at the database layer). |

### 3.3 Reviews

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-07 | The traveller can submit a review against an attraction. | The per-card "Leave a review" form accepts an optional rating (0–5) and comment; `POST /api/reviews` requires a valid integer `attraction_id` that references an existing attraction, returning 400 otherwise; a successful submission (201) shows a confirmation and clears the form. |
| FR-08 | Reviews can be listed, optionally filtered by attraction. | `GET /api/reviews?attraction_id={id}` returns only that attraction's reviews. |

### 3.4 AI Recommendation

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-09 | The traveller can request a recommendation from a free-text interest description. | `POST /api/recommend` with `{"interest": "..."}` (min 3, max 200 characters client-side) runs the Plan → Act → Observe → Adapt loop in `recommend.py` and returns a recommendation with a `source` of `ai`, `ai_retry`, or `fallback`. |
| FR-10 | The recommendation is grounded only in attractions the database actually returned for the inferred category. | `_build_prompt()` supplies at most 6 candidate attractions and instructs the model to recommend only from that list; `_is_response_usable()` rejects a response that does not name a supplied attraction's `name` or `category`. |
| FR-11 | An empty, too-short, or off-topic model response triggers one retry with a narrower prompt before falling back. | `_build_narrow_prompt()` retries with the top 2 candidates and a one-sentence instruction; if the retry also fails validation, a deterministic templated response is returned instead (`source: "fallback"`), so the feature never surfaces a raw model failure to the user. |
| FR-12 | The AI loop's stages are printed to the terminal for live demonstration. | `PLAN:`, `ACT:`, `OBSERVE:`, and `ADAPT:` lines are printed for every request, per the Release 0 rubric's requirement that the loop be "demonstrated in the terminal." |

### 3.5 Integrated Application

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-13 | The feature is reachable from the unified home page and uses the shared theme. | The shared `index.html` links to the student-3 frontend; `student-3/frontend/style.css` uses the same visual language as the shared theme (to be reconciled with `shared/style.css` before final integration if the team consolidates themes). |
| FR-14 | The three assigned services run from the shared Compose file and the shared Ollama runtime. | `student3-frontend` (`:5103`), `student3-backend` (`:5203`), `student3-database` (`:5303`), and the one-shot `student3-db-init` job are all defined in the root `docker-compose.yml`; the backend calls `http://ollama:11434` via Compose DNS, model pulled by the shared `ollama-model-setup` job. |
| FR-15 | The frontend communicates only with the backend/API service. | `student-3/frontend/nginx.conf` reverse-proxies `/api/` to `student3-backend`; the frontend never calls `student3-database` or Ollama directly. |

## 4. API Contracts

### 4.1 Frontend-Facing Backend API (`student3-backend`)

| Method and path | Success | Purpose |
|---|---:|---|
| `GET /api/attractions?category=` | `200` | List/filter attractions. |
| `GET /api/attractions/{id}` | `200` / `404` | Read one attraction. |
| `POST /api/attractions` | `201` / `400` | Create an attraction. |
| `PUT /api/attractions/{id}` | `200` / `400` / `404` | Update an attraction. |
| `DELETE /api/attractions/{id}` | `204` / `404` | Delete an attraction. |
| `GET /api/reviews?attraction_id=` | `200` | List/filter reviews. |
| `POST /api/reviews` | `201` / `400` | Create a review. |
| `POST /api/recommend` | `200` / `400` | Run the Plan → Act → Observe → Adapt recommendation loop. |
| `POST /api/itinerary` | `202` | Release 0 stub — logs the request only. |
| `GET /health` | `200` | Process health. |

### 4.2 Backend-Facing Database API (`student3-database`)

| Method and path | Success | Purpose |
|---|---:|---|
| `GET /api/data/attractions?category=` | `200` | List/filter attractions. |
| `GET /api/data/attractions/{id}` | `200` / `404` | Read one attraction plus its reviews. |
| `POST /api/data/attractions` | `201` / `400` | Create (requires `name`, `category`). |
| `PUT /api/data/attractions/{id}` | `200` / `400` / `404` | Replace (requires `name`, `category`). |
| `DELETE /api/data/attractions/{id}` | `204` / `404` | Delete (cascades to that attraction's reviews). |
| `GET /api/data/reviews?attraction_id=` | `200` | List/filter reviews. |
| `POST /api/data/reviews` | `201` / `400` | Create (requires integer `attraction_id` referencing an existing attraction). |
| `GET /health` | `200` / `503` | Process + SQLite connectivity health. |

### 4.3 Error Shape

```json
{
  "error": "validation_error",
  "message": "name and category are required."
}
```

`error` values in use: `validation_error` (400), `not_found` (404), `database_unavailable` (502, backend-to-database connectivity failure).

## 5. Data Requirements

### 5.1 `attractions`

| Field | Rule |
|---|---|
| `id` | Integer primary key, autoincrement. |
| `name` | Required, non-empty string. |
| `category` | Required, non-empty string (`sight`, `restaurant`, or `activity` in seed/UI data; the database does not enforce an enum). |
| `description` | Optional string. |
| `rating` | Optional number, 0–5 (UI-enforced; not DB-enforced). |

### 5.2 `reviews`

| Field | Rule |
|---|---|
| `id` | Integer primary key, autoincrement. |
| `attraction_id` | Required integer, foreign key to `attractions.id`; the database API rejects an `attraction_id` that is not an existing attraction. |
| `rating` | Optional number, 0–5 (UI-enforced). |
| `comment` | Optional string. |

Seed data provides 12 attractions and 14 reviews (`student-3/database/seed.py`), exceeding the 10-record minimum for the primary table. Seeding is idempotent — it only runs when the `attractions` table is empty.

## 6. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Reliability | An unavailable or malformed Ollama response never crashes the request or blocks the user — `_call_ollama()` catches request exceptions and returns an empty string, which the Observe/Adapt stages turn into a retry and then a deterministic fallback. |
| NFR-02 | Timeout | `OLLAMA_TIMEOUT` defaults to 120s (not the more typical 30s), because a local model's first call after container start pays a one-off load cost that regularly exceeds 30s on CPU-only hosts (observed directly during development). |
| NFR-03 | Security | All attraction/review/recommendation text is treated as untrusted before it reaches the DOM — `escapeHtml()` is applied to every API- or model-sourced string before `innerHTML` insertion; only numeric IDs are ever interpolated into `hx-vals`/URLs. |
| NFR-04 | Portability | `docker compose up -d --build student3-frontend` brings up the full slice (frontend, backend, database, db-init, and the shared `ollama`/`ollama-model-setup` dependency) on a clean checkout. |
| NFR-05 | CI isolation | `student-3.yml` runs `pytest` with the real database/backend code but does not require live Ollama for the unit-test stage; the recommend tests mock `_call_ollama`. The workflow's later Compose/smoke stage does start the real containers, including Ollama, so it exercises the live model. |
| NFR-06 | Observability | Every recommendation call prints a labelled `PLAN`/`ACT`/`OBSERVE`/`ADAPT` line, so the loop can be shown live in a terminal per the marking rubric. |

## 7. AI Prompt and Validation Contract

The backend supplies only attractions its own query returned (max 6). The prompt must:
- instruct the model to recommend **only** from the supplied list, never to invent attractions;
- keep the response to 2–3 sentences;
- be followed by a narrower one-attraction retry prompt on a bad first response;
- fall back to a deterministic templated response if both attempts fail validation.

The model is advisory only. `_is_response_usable()` — not the model — decides whether a response is usable, based on non-empty length and whether it names a supplied candidate's `name` or `category`.

## 8. Test and Evidence Requirements

| ID | Required evidence |
|---|---|
| EV-01 | `pytest tests` from `student-3/` — 29 tests covering backend attraction/review routes (`test_backend_attractions.py`), the database API (`test_database_api.py`), and the recommend loop with mocked Ollama (`test_recommend.py`). All 29 passing as of this document. |
| EV-02 | `docker compose config --quiet` and `docker compose build ...` succeed (exercised in `student-3.yml`). |
| EV-03 | CI smoke test: `student-3.yml` starts the real containers and curls `/health` on all three services plus `/api/attractions` to assert at least 10 seeded records. |
| EV-04 | Manual browser evidence: create/edit/delete an attraction, submit a review, and request an AI recommendation, all against the integrated app (not the standalone `student-3/frontend`). |
| EV-05 | A finalised agentic-loop development record under `docs/agentic-loop-records/` referencing real student-3 work (see `known-issues.md` — outstanding as of this document). |

## 9. Definition of Done

Release 0 is done for this feature only when it is demonstrated inside the integrated group application (a standalone feature is worth zero per the rubric), full attraction CRUD is exercised through the frontend (not only the API), the AI recommendation loop is shown live with real terminal output, and the evidence in Section 8 exists and is linked from the technical report.
