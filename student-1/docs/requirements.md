# AI Accommodation Recommender Requirements

## 1. Purpose and Scope

The AI Accommodation Recommender helps a traveller rank accommodation options from a local SQLite catalogue according to destination, travel dates, guest count, and nightly budget. Programmatic ranking is the default, and the traveller may explicitly opt in to additional AI ranking and provide free-text preferences. When a destination has no cached catalogue records, the backend may populate that catalogue from LiteAPI sandbox rates before ranking.

Release 0 must deliver one integrated, containerised feature through the required path:

`Vue 3 + TypeScript frontend -> ASP.NET Core backend/API -> ASP.NET Core database API -> EF Core -> SQLite`

The tutor has confirmed that teams may choose their frontend and backend technologies; this feature retains the existing Vue 3/TypeScript and ASP.NET Core design. The application backend calls exactly one configured accommodation-ranking model through the shared Ollama runtime.

The feature must run from the team's shared `docker-compose.yml`, be reachable from the unified home page, use the shared CSS theme, and provide demonstrable Create, Read, Update, and Delete operations.

### 1.1 Release 0 In Scope

- Search criteria entry and validation.
- Default deterministic programmatic ranking with optional AI ranking per search.
- Ranking at least 10 seeded accommodation records with Ollama.
- Deterministic fallback ranking if opted-in Ollama ranking is unavailable or invalid.
- Persisted search history with create, read, rename, and delete actions.
- Accommodation catalogue CRUD in the database API.
- Backend-only LiteAPI sandbox import when a searched destination is not yet cached.
- Three independently containerised student services.
- Integration with the shared Ollama service, home page, theme, and Compose stack.
- A terminal-runnable Plan -> Act -> Observe -> Adapt development loop using two distinct local Ollama models with separate implementation and review responsibilities.
- Tests, logs, diagrams, and evidence required by the Release 0 rubric.

### 1.2 Release 0 Out of Scope

- Live booking, payments, accounts, authentication, maps, reviews, and price guarantees.
- Production hotel availability, date-specific price guarantees, and booking-provider service levels. LiteAPI data is a demonstration cache, not a production quote.
- MCP, RAG, multi-agent systems, cloud deployment, and production-scale availability. These belong to later releases.
- Scraping accommodation websites.

## 2. Actors and System Boundaries

| Actor or system | Responsibility |
|---|---|
| Traveller | Submits criteria, views recommendations, and manages search history. |
| Vue frontend service | Renders the typed user interface and sends browser requests only to the backend/API service. |
| ASP.NET Core backend/API service | Validates input, retrieves candidates, ranks programmatically, optionally calls the single application model, validates ranking output, persists searches, and exposes the frontend-facing API. |
| ASP.NET Core database API service | Owns EF Core and the SQLite file and exposes accommodation and search-history CRUD over HTTP. |
| SQLite | Stores the accommodation catalogue and persisted search history. No other service may open its file. |
| Shared Ollama service | Hosts all locally required model tags for team application microservices and the two distinct development-loop roles. No feature owns a separate Ollama runtime. |
| LiteAPI sandbox | Optionally supplies accommodation rates to the backend when the requested destination has no local catalogue records. The browser never receives the provider credential. |
| Shared home page | Provides the integrated entry point to this feature. |

## 3. Functional Requirements

Each requirement is mandatory for Release 0 unless marked otherwise.

### 3.1 Search and Validation

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | The traveller can submit destination, check-in date, check-out date, guest count, minimum nightly price, maximum nightly price, and whether to use AI ranking. AI searches may also include free-text preferences. | The Vue frontend leaves AI ranking unchecked and hides the preferences control by default. Selecting AI reveals preferences. Unselecting AI hides the control and sends an empty preference value. |
| FR-02 | The backend validates all search input before calling the database or Ollama. | Destination is 2-100 characters; check-in is not before the current local date; check-out is after check-in; guests is an integer from 1-20; prices are numbers from 0-100000; minimum price is not greater than maximum price; preferences is at most 500 characters. |
| FR-03 | Invalid input produces field-specific feedback without creating history or calling Ollama. | The backend returns HTTP `400` with a stable error object; the frontend displays the message beside or above the form; database and Ollama test doubles receive no call. |
| FR-04 | The backend retrieves eligible accommodation candidates only through the database API. | Candidates match the requested destination case-insensitively, support at least the requested guest count, fall within the nightly price range, and are active. The backend never opens SQLite directly. |
| FR-04a | When the database API has no cached accommodation for a destination, the backend may import LiteAPI sandbox results before retrieving eligible candidates again. | The backend sends validated criteria using LiteAPI's `aiSearch` location method, requests at most 10 AUD results, validates provider IDs, metadata, occupancy, URLs, and price data, converts total-stay prices to nightly prices, and creates catalogue records only through the database API. Existing destination data skips LiteAPI. |
| FR-05 | A valid search with no eligible candidates returns an explicit empty state. | The frontend displays that no matching accommodation is available; the backend returns HTTP `200` with an empty result list and does not call Ollama. |

### 3.2 AI Recommendation

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-06 | When the traveller explicitly opts in, the backend sends eligible candidates and validated search criteria to the shared Ollama service using an approved Release 0 model. | `useAi: true` follows frontend -> backend -> Ollama -> model; omitted or false `useAi` never calls Ollama. The request is visible in backend logs without secrets or full free-text preferences. |
| FR-06a | Without AI opt-in, the backend returns deterministic programmatic ranking. | Candidates are ordered by absolute distance from the traveller's budget midpoint, then nightly price, then accommodation ID; the saved ranking mode is `programmatic`; no AI-unavailable notice is shown. |
| FR-07 | Ollama must return one ranking entry for every supplied candidate. | Each entry contains an existing integer accommodation ID, a unique rank from 1 through candidate count, and a reason of 1-200 characters. No unknown, duplicate, omitted, or extra IDs are accepted. |
| FR-08 | The backend validates model output before returning or storing it. | JSON parsing, schema validation, ID set equality, rank uniqueness/range, and reason length are tested. Invalid output is never treated as a successful AI ranking. |
| FR-09 | The backend provides a deterministic fallback when opted-in Ollama ranking times out, is unavailable, or returns invalid output. | Candidates are ordered by absolute distance from the traveller's budget midpoint, then nightly price, then accommodation ID; each result is labelled as fallback-ranked; the user receives results with a non-blocking notice. |
| FR-10 | Each result identifies the accommodation, nightly price, location, capacity, rank, and concise explanation. | Results are ordered by ascending rank and all displayed values come from validated database/API or ranking data. |

### 3.3 Search History CRUD

Search history is the user-facing CRUD resource used for the rubric demonstration.

| ID | CRUD | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-11 | Create | A completed search is persisted through the database API. | One history record contains the validated criteria, ranked result snapshot, ranking mode (`programmatic`, `ai`, or `fallback`), title, and UTC creation/update timestamps. Empty-candidate searches may also be stored with an empty snapshot. |
| FR-12 | Read | The traveller can list and reopen persisted searches. | History is ordered newest first; reopening renders the stored snapshot and never calls Ollama again. |
| FR-13 | Update | The traveller can rename a search. | A title trimmed to 1-80 characters is persisted; invalid titles return `400`; missing records return `404`; the updated title appears without a full-page reload. |
| FR-14 | Delete | The traveller can delete a search. | The user is asked to confirm; deletion removes the record; repeated deletion returns `404`; the item disappears from the interface. |

### 3.4 Accommodation Catalogue CRUD

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-15 | The database API exposes create, list, get, update, and delete operations for accommodations. | Integration tests cover valid requests plus `400`, `404`, and duplicate/constraint failures. |
| FR-16 | The catalogue contains at least 10 valid accommodation records for local execution, CI, and demonstration. | A repeatable seed operation creates at least 10 records without duplicates and can be run against an empty database. |
| FR-17 | Deleting an accommodation does not corrupt stored history. | Search history stores a result snapshot, so an old search remains readable after its source accommodation changes or is deleted. |

### 3.5 Integrated Application

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-18 | The feature is reachable from the unified home page and uses the shared theme. | The home-page link opens the feature in the integrated Compose application; shared typography, colours, spacing, and controls are visibly reused. |
| FR-19 | All three assigned services use the one shared Ollama runtime in the shared Compose application. | `docker compose up --build` starts healthy frontend, backend, database, and shared Ollama services; every AI consumer uses `http://ollama:11434` through Compose DNS; one shared setup job checks configured model tags and pulls only missing models into the persistent Ollama volume. |
| FR-20 | The frontend communicates only with the backend/API service. | Browser/network evidence and source review show no direct frontend call to the database API or Ollama. |

## 4. API Contracts

Exact JSON schemas belong beside the implementation and tests. These endpoint behaviours are the minimum stable contract.

### 4.1 Frontend-Facing Backend API

| Method and path | Success | Purpose |
|---|---:|---|
| `POST /api/searches` | `201` | Validate criteria, rank candidates, persist the search, and return the saved result. |
| `GET /api/searches` | `200` | List search-history summaries newest first. |
| `GET /api/searches/{id}` | `200` | Return one stored search and its result snapshot without reranking. |
| `PATCH /api/searches/{id}` | `200` | Rename one stored search. |
| `DELETE /api/searches/{id}` | `204` | Delete one stored search. |
| `GET /health` | `200` | Report backend process health. |

### 4.2 Backend-Facing Database API

| Method and path | Success | Purpose |
|---|---:|---|
| `GET /api/data/accommodations` | `200` | Filter/list candidate accommodations. |
| `POST /api/data/accommodations` | `201` | Create a catalogue record. |
| `GET /api/data/accommodations/{id}` | `200` | Read one catalogue record. |
| `PUT /api/data/accommodations/{id}` | `200` | Replace one catalogue record. |
| `DELETE /api/data/accommodations/{id}` | `204` | Delete one catalogue record. |
| `GET /api/data/searches` | `200` | List persisted search summaries. |
| `POST /api/data/searches` | `201` | Persist a completed search. |
| `GET /api/data/searches/{id}` | `200` | Read one persisted search. |
| `PATCH /api/data/searches/{id}` | `200` | Rename one persisted search. |
| `DELETE /api/data/searches/{id}` | `204` | Delete one persisted search. |
| `GET /health` | `200` | Report database API process and SQLite connectivity health. |

### 4.3 Error Shape

All API errors must use:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Check-out must be after check-in.",
    "fields": {
      "checkOut": "Must be after check-in."
    },
    "correlationId": "..."
  }
}
```

`fields` may be empty for non-validation errors. Expected statuses are `400` for invalid input, `404` for missing resources, `409` for a data conflict, `502` for an unusable dependency response, and `503` for an unavailable dependency when no functional fallback exists.

## 5. Data Requirements

### 5.1 Accommodation

| Field | Rule |
|---|---|
| `id` | Positive integer primary key. |
| `name` | Required, trimmed, 1-120 characters. |
| `destination` | Required, trimmed, 2-100 characters; indexed with `is_active`. |
| `description` | Required, trimmed, 1-1000 characters. |
| `nightly_price` | Required decimal, 0-100000, stored with two-decimal precision. |
| `max_guests` | Required integer, 1-20. |
| `amenities` | Required JSON array of unique non-empty strings; maximum 30 values. |
| `image_url` | Optional HTTP(S) URL, maximum 2048 characters. |
| `booking_url` | Optional HTTP(S) URL, maximum 2048 characters. |
| `is_active` | Required boolean; defaults to true. |
| `created_at`, `updated_at` | Required UTC timestamps. |

### 5.2 Search

| Field | Rule |
|---|---|
| `id` | Positive integer primary key. |
| `title` | Required, trimmed, 1-80 characters. |
| `destination` | Same normalised value accepted by FR-02. |
| `check_in`, `check_out` | ISO `YYYY-MM-DD`; check-out after check-in. |
| `guests` | Integer, 1-20. |
| `min_price`, `max_price` | Decimal, 0-100000; minimum not greater than maximum. |
| `preferences` | String, 0-500 characters. |
| `ranking_mode` | Enum-like value: `programmatic`, `ai`, or `fallback`. |
| `results_json` | Valid JSON array containing the immutable ranked-result snapshot. |
| `created_at`, `updated_at` | Required UTC timestamps. |

At least 10 records must exist in every table used in the submitted demonstration database. Seed data must contain no secrets or personal data.

## 6. Non-Functional Requirements

| ID | Category | Requirement and measurable acceptance target |
|---|---|---|
| NFR-01 | Performance | With local seeded data and a responsive local Ollama model, 95% of search requests complete within 15 seconds across 20 sequential manual/test requests. Non-AI history operations complete within 2 seconds. Record the device and model used with the evidence. |
| NFR-02 | Timeout | Database API calls time out within 3 seconds, LiteAPI calls within 10 seconds, and the Ollama call within 12 seconds. A timeout follows the explicit provider-error or ranking-fallback behaviour. |
| NFR-03 | Reliability | A malformed or unavailable Ollama response cannot crash the request process, create invalid ranks, or lose an otherwise valid search. |
| NFR-04 | Accessibility | Search, history, dialogs, notices, and results are keyboard operable; controls have programmatic labels; focus is visible; status changes use an appropriate live region; images have meaningful or empty alt text. |
| NFR-05 | Responsive UI | At viewport widths of 320px, 768px, and 1280px, all controls and results remain usable without horizontal page scrolling. |
| NFR-06 | Security | Secrets are supplied by environment variables and excluded from source control and logs. User input is validated server-side, rendered as text rather than trusted HTML, and never interpolated into SQL. |
| NFR-07 | Privacy | The feature requires no account or personal identity data. Free-text preferences are requested and stored only for AI-selected searches; the UI states that saved history retains them and deletion removes the whole history record. |
| NFR-08 | Observability | Every search has a correlation ID across backend logs. Logs identify stage, outcome, duration, candidate count, ranking mode, and dependency failure category without logging secrets or full preference text. |
| NFR-09 | Maintainability | NuGet and npm dependencies use committed lock/restore metadata; TypeScript strict mode and nullable C# reference types are enabled; configuration is environment-driven; public API payloads use explicit DTOs and are covered by automated tests. |
| NFR-10 | Container health | Each service has a health check. A service reports healthy only when it can perform its own responsibility; database health includes opening SQLite. |
| NFR-11 | Portability | The integrated application starts on a clean supported machine using documented prerequisites and `docker compose up --build`; no absolute paths or developer-specific values are required. |

## 7. AI Prompt and Validation Contract

The backend supplies only validated criteria and eligible candidates. The prompt must:

- state that candidate data and traveller preferences are untrusted data, not instructions;
- require JSON only, with no Markdown;
- define the exact output fields and constraints from FR-07;
- prohibit adding candidates or inventing facts;
- ask for concise reasons based only on supplied fields.

The model is advisory. The backend, not the model, owns validation, fallback, persistence, and HTTP responses.

## 8. Test and Evidence Requirements

| ID | Required evidence |
|---|---|
| EV-01 | Unit tests for input validation, prompt/output validation, and deterministic fallback ordering. |
| EV-02 | Database API integration tests covering CRUD, filtering, seed idempotency, and constraints. |
| EV-03 | Backend integration tests with fake database and Ollama responses covering success, empty candidates, timeout, malformed JSON, missing/duplicate IDs, and history CRUD. |
| EV-04 | Frontend tests or a documented repeatable browser checklist covering submission, errors, loading state, results, history reopen, rename, delete, keyboard use, and responsive widths. |
| EV-07 | `docker compose up --build` evidence showing all feature services and the shared AI service healthy. |
| EV-09 | Screenshots of the unified home page, search form with AI opt-in, programmatic results, AI-ranked results, fallback notice, history CRUD, and shared visual theme. |
| EV-10 | Architecture diagrams for the individual services, integrated Release 0 app, and Docker Compose deployment. |
| EV-11 | Prompt log, AI review record, commit log, contribution log, known issues, attendance checkpoints, and demonstration video URL. |

## 9. Full-Marks Traceability

| Release 0 criterion | Feature obligation |
|---|---|
| Project Setup | Correct standard folder placement, populated tables, shared home/theme, Dockerfiles, Compose wiring, Ollama configuration, and workflow. |
| Service Implementation | Independently containerised Vue frontend, ASP.NET Core backend, and ASP.NET Core/EF Core/SQLite database API communicate over HTTP and expose health checks. |
| AI-Mode Integration | An explicitly opted-in frontend request reaches Ollama through the backend and produces visible recommendations; the default request remains programmatic. |
| Prompt Engineering and Context | The application prompt, prompt log, context file, and validation/review records are maintained. |
| Docker Compose Integration | The feature runs inside the single team Compose file using service DNS, health checks, and shared Ollama. |
| Working Software | The frontend demonstrates create, read, update, and delete through both API layers and SQLite. |
| Technical Report | EV-05 through EV-11 provide the required diagrams, logs, screenshots, execution evidence, and contribution records. |
| Project Demonstration | Mitchell attends and demonstrates the integrated feature, AI path, and CRUD within the group video. |

## 10. Definition of Done

Release 0 is done only when every mandatory FR, NFR, and EV item above is satisfied in the integrated group application. A standalone feature, placeholder service, unpopulated table, direct SQLite access from the backend, or feature absent from the unified home page is not done and risks zero for the affected criterion.
