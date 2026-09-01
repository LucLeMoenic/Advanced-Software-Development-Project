# Itinerary Planner Requirements

## Scope

Release 0 provides an integrated itinerary planner through:

`Browser -> shared frontend -> Student 2 frontend -> Student 2 backend -> database API -> SQLite`

For AI generation, the backend calls the team's shared Ollama runtime using one configured approved model. The frontend never calls SQLite or Ollama directly.

## Functional Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| IT-FR-01 | Create a trip from traveller, destination, dates, budget, and interests. | Backend validates all fields and returns a persisted day-by-day itinerary. |
| IT-FR-02 | Generate an itinerary with AI Mode. | A frontend request reaches the backend, shared Ollama, and configured approved model; output contains exactly two valid stops per trip day. |
| IT-FR-03 | Remain usable when AI fails. | Invalid, unavailable, or timed-out model output produces a visible deterministic fallback itinerary. |
| IT-FR-04 | Read saved trips. | The traveller can list and reopen persisted trips without another model call. |
| IT-FR-05 | Update trip details and stops. | Trip records and individual stop day, activity, and notes can be updated through the backend. |
| IT-FR-06 | Delete trips and stops. | Confirmed deletion removes the selected resource; deleting a trip cascades to its stops. |
| IT-FR-07 | Add and regenerate stops. | The traveller can add a stop, regenerate one stop, or atomically regenerate the whole itinerary. |
| IT-FR-08 | Persist complete state safely. | New and regenerated itineraries are committed atomically by the database API; failed validation does not delete valid existing stops. |
| IT-FR-09 | Expose database CRUD only over HTTP. | Only the database service opens SQLite; the backend uses the database API. |
| IT-FR-10 | Integrate with the team application. | The shared home page opens `/itinerary/`, and the feature uses the shared visual system. |
| IT-FR-11 | Demonstrate Plan, Act, Observe, Adapt. | The shared development agentic loop produces a finalised record using distinct implementer and reviewer models; application trace text is not used as substitute evidence. |

## Data Requirements

### trips

`id`, `user_name`, `destination`, `start_date`, `end_date`, `budget`, `interests`, `created_at`, `updated_at`.

### trip_stops

`id`, `trip_id`, `day`, `activity`, `notes`, `sort_order`, `created_at`, `updated_at`.

`trip_stops.trip_id` references `trips.id` with cascade delete. Every submitted database table must contain at least ten records; a fresh database seeds ten trips and twenty stops.

## Non-Functional Requirements

| ID | Requirement |
|---|---|
| IT-NFR-01 | Frontend, backend, and database services are independently containerised and health checked. |
| IT-NFR-02 | Database calls time out within 3 seconds and Ollama calls within 20 seconds. |
| IT-NFR-03 | User and model values are validated server-side and rendered as text. |
| IT-NFR-04 | The interface is keyboard operable, visibly focused, and usable at 320px, 768px, and 1280px without horizontal scrolling. |
| IT-NFR-05 | Configuration uses environment variables and Compose DNS names; no secret is committed. |
| IT-NFR-06 | Student 2 CI runs frontend, backend, and database tests, validates Compose, and builds integrated images without requiring a live model. |
| IT-NFR-07 | The feature runs locally from the unified application at `http://localhost:5100/itinerary/`. |

## Evidence Required

- Frontend, backend, and database automated-test output.
- Successful Student 2 GitHub Actions run URL or screenshot.
- Clean Docker Compose build/start and health evidence.
- Browser screenshots for create/read/update/delete, AI success, forced fallback, shared home integration, and responsive widths.
- A genuine finalised shared Plan/Act/Observe/Adapt record.
- Architecture/data-design diagrams, prompt log, review record, contribution/commit logs, known limitations, attendance checkpoint, and showcase video URL.
