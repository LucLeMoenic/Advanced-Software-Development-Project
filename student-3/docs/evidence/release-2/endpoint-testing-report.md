# Student 3 — Post-Commit CI/CD Endpoint Testing Report (Release 2)

Workflow: `.github/workflows/student-3.yml` · Service: Student 3 backend/API (`student3-backend`, port 5203)

## Endpoints under test

| # | Endpoint function | What is verified |
|---|---|---|
| 1 | `GET /api/attractions` | Empty catalogue → `[]`; all rows in id order with the full field shape; `?category=` filter for sight / restaurant / activity; unknown category → `200 []` (not an error); database down → `502 database_unavailable` |
| 2 | `POST /api/attractions` | Valid create → `201` with generated id and echoed fields; row persisted and visible through `GET /api/attractions` and `GET /api/attractions/<id>`; whitespace trimmed, optional fields default to `null`; empty body / missing / blank `name` or `category` → `400 validation_error` and nothing stored; non-JSON body → `400`; database down → `502` |

## How the workflow runs them (after every push / PR touching Student 3)

| Workflow step | Tests | Output |
|---|---|---|
| Post-commit endpoint tests (GET and POST /api/attractions) | `student-3/tests/test_endpoints_cicd.py`: 17 tests, real backend app → real database app (no mocks), fresh temp SQLite per test | `endpoint-tests-junit.xml` |
| Publish endpoint test report | `scripts/test/junit_summary.py` renders the JUnit file as a table in the run's job summary; fails if the XML is missing or has failures | Job summary |
| Upload endpoint test results | `student-3-endpoint-test-results` artifact | Downloadable JUnit XML |
| Post-commit endpoint tests against running containers | `student-3/tests/live_endpoint_check.py`: 11 checks over HTTP against the Compose containers (create → list → filter → validation errors → cleanup) | Job summary |

The existing unit suite, Compose validation, image builds and smoke test still run in the same job. `workflow_dispatch` was added so the run can be repeated on demand.

## Results

| Evidence | Result |
|---|---|
| `ci/01-local-pytest-endpoint-tests.txt` | 17/17 endpoint tests pass |
| `ci/02-local-live-container-endpoint-check.txt` | 11/11 live checks pass against the built, healthy containers |
| `ci/03-mutation-check.txt` | Three deliberately introduced bugs (filter ignored, trim removed, wrong status code) each make the tests fail, so they are not vacuous |
| Whole Student 3 suite | 81 passed (64 existing + 17 new) |
| **GitHub Actions run** | **TODO: add run URL and screenshot after the first push** (`ci/04-github-actions-run.md`) |

## Findings recorded, not hidden

The database service validates only that `name` and `category` are present. It does not restrict `category` to sight / restaurant / activity, nor `rating` to 0-5; the frontend form does. A direct API caller can therefore store `category: "nightclub"`. The tests assert the actual behaviour and do not claim server-side enum validation. Logged in `knownissues.md`; a possible follow-up.
