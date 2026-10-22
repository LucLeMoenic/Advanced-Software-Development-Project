# Student 5 - Post-Commit CI/CD Endpoint Testing Report (Release 2)

Workflow: `.github/workflows/student-5.yml` · Service: Student 5 backend/API
(`student5-backend`, port 5205) · Requirement: TL-NFR-11 in
[`release-2-plan.md`](../../release-2-plan.md)

## Endpoints under test, and why these two

| # | Endpoint function | What is verified |
|---|---|---|
| 1 | `POST /api/destinations` | Valid create returns `201` with the stored row. Exactly one `POST` reaches the database API at `/api/destinations`, carrying the client's JSON unchanged. Empty body, missing `visa_requirement` and blank `country` return the database's `400` and message unchanged. A non-JSON body is forwarded as no body (never as form text), and the database's `400` comes back. Database unreachable returns `503 {"error": "database service unavailable"}`. |
| 2 | `PUT /api/destinations/<id>` | Valid update returns `200`. The body forwarded to the database holds **only** the fields the client sent, because the database `PUT` is a partial merge and padding would overwrite stored values. A blank `visa_requirement` or a non-string `country` returns the database's `400`. An unknown id returns the database's `404`. A non-integer id gets a `404` from the backend's own router with **no** database call. Connection refused and read timeout both return `503`. |

These are the two write paths every Student 5 feature depends on:

- the Manage panel creates and edits destinations through them;
- the advisory and the Multi-Agent readiness review read the rows they write.

The backend is a passthrough (`relay()` in `student-5/backend/app.py`). The
database service owns validation and existence checks. So the tests check what
the backend is responsible for:

- it forwards the exact request;
- it relays status and body unchanged;
- it makes up only one status of its own, the `503` for an unreachable database.

The mocked `400`/`404` bodies are copied from the real messages in
`student-5/database/app.py`.

## How the workflow runs them (every push / PR touching Student 5)

All four AI flags (`AI_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED`,
`MULTI_AGENT_ENABLED`) are `"false"` on the endpoint-test step and on the step
that starts the containers. This matches the cloud baseline. The mocked tests also
use the `ai_off_client` fixture, which pins all four off whatever the environment
says.

| Workflow step | Tests | Output |
|---|---|---|
| Post-commit endpoint tests (POST and PUT /api/destinations) | `student-5/backend/tests/test_endpoints_cicd.py`: 13 tests, database API mocked with `responses` | `student-5/endpoint-tests-junit.xml` |
| Publish endpoint test report | `scripts/test/junit_summary.py` renders the JUnit file as a table in the job summary. It fails if the XML is missing, empty or has failures. | Job summary |
| Upload endpoint test results | `student-5-endpoint-test-results` artifact (runs even if the tests failed) | Downloadable JUnit XML |
| Smoke test Student 5 integration | Release 1 checks, plus `POST /api/advisory` returning `503 ai_disabled`. This proves `AI_ENABLED=false` reached the container. | Step log |
| Post-commit endpoint tests against running containers (POST and PUT /api/destinations) | `student-5/backend/tests/live_endpoint_check.py`: 12 checks over HTTP against the Compose containers, with nothing mocked (backend -> database API -> SQLite). It creates a destination with a unique country (`CI Endpoint Check <8 hex>`), rejects an invalid create, updates it, reads it back, rejects an invalid update, gets `404` for an unknown id, then deletes it and confirms the delete. The delete runs in a `finally`, so the row is removed even if a check fails part-way. | Job summary table |
| Show Student 5 container logs on failure | `docker compose logs` for the three Student 5 services | Step log |

The Release 1 steps are kept unchanged and run in the same job:

- `student-5.ps1` (all four Student 5 suites, which now include the 13 new tests);
- Compose validation;
- the image builds;
- the MCP/RAG fail-closed smoke checks.

`scripts/test/junit_summary.py` was added to the workflow's path triggers. The new
test files are under `student-5/**`, which was already a trigger.

## Local results (22 October 2026)

| Evidence | Result |
|---|---|
| [`endpoint-tests/01-local-pytest-endpoint-tests.txt`](endpoint-tests/01-local-pytest-endpoint-tests.txt) | 13/13 endpoint tests pass (the workflow's command, repo `.venv`, Python 3.13.2) |
| [`endpoint-tests/02-local-junit-summary.md`](endpoint-tests/02-local-junit-summary.md) | `junit_summary.py` output from the same JUnit file: **13 of 13 passed** |
| [`endpoint-tests/03-local-live-container-endpoint-check.txt`](endpoint-tests/03-local-live-container-endpoint-check.txt) | 12/12 live checks pass against the local Compose containers, backend recreated with all four flags `false`. Afterwards no `CI Endpoint Check` row remained (12 seed rows). |
| [`endpoint-tests/04-local-live-check-step-summary.md`](endpoint-tests/04-local-live-check-step-summary.md) | The Markdown table the live check writes to `$GITHUB_STEP_SUMMARY` |
| [`endpoint-tests/05-mutation-check.txt`](endpoint-tests/05-mutation-check.txt) | Four deliberate bugs in `app.py`, each caught (1, 3, 7 and 3 failures): a non-JSON POST forwarded as `{}`, a padded PUT body, database 4xx masked as `502`, an unreachable database reported as `500`. So the tests are not vacuous. `app.py` was restored afterwards. |
| Live check failure paths | Unreachable backend: exit 1, and a `FAIL` row still reaches the step summary. A create reply with no usable id: the row is found by its unique country and deleted. |
| Smoke step from `student-5.yml`, run locally with `bash` | Passed, including the new `ai_disabled` advisory check |
| Workflow YAML | Parses with `yaml.safe_load` (13 steps; push and PR path lists identical); `docker compose config --quiet` passes |
| Whole Student 5 suites | database 26, backend 199 (186 existing + 13 new), MCP logistics 34, RAG student-5 retrieval 17 passed |

## GitHub Actions run (to be completed after push)

> Fill in after the first push of this branch, and again for the merge to `main`.

| Item | Value |
|---|---|
| Branch / commit | `AC/student5-r2-endpoint-ci` @ `<sha>` |
| Run URL | `<https://github.com/<org>/<repo>/actions/runs/<id>>` |
| Run result | `<success / failure>` |
| Step "Post-commit endpoint tests (POST and PUT /api/destinations)" | `<success>`, `<13 passed in N s>` |
| Step "Post-commit endpoint tests against running containers (POST and PUT /api/destinations)" | `<success>`, `<12/12 checks passed>` |
| Artifact `student-5-endpoint-test-results` | `<present, size>` |
| Merge to `main` run | `<run URL, result>` |

Screenshots to add under `endpoint-tests/` (names suggested):

- `06-ci-run-overview.png`: the run page with the green check, commit sha and the
  **Artifacts** section showing `student-5-endpoint-test-results`.
- `07-ci-job-summary.png`: the job **Summary**, showing both tables: "Student 5
  post-commit endpoint tests (POST and PUT /api/destinations)" with **13 of 13
  passed**, and "Student 5 live endpoint check" with every row `pass`.
- `08-ci-endpoint-step-log.png`: the expanded "Post-commit endpoint tests (POST and
  PUT /api/destinations)" step, showing the `env:` block with the four flags
  `false` and the `13 passed` line.
- `09-ci-live-check-step-log.png`: the expanded live-check step, ending
  `12/12 checks passed`.

Also save the downloaded artifact's `endpoint-tests-junit.xml` as
`endpoint-tests/10-ci-endpoint-tests-junit.xml`.

## Findings recorded, not hidden

- The database validates only that `country` and `visa_requirement` are non-empty
  strings. It does not restrict `visa_requirement` to the values the UI offers, and
  it does not prevent duplicate countries. The tests assert the actual behaviour and
  make no claim about enum or uniqueness checks. This is why the live check uses a
  unique country name: it avoids confusion with seed rows, not a conflict.
- The mocked tests prove the backend's own contract. The real database path is
  proved by the live container check, which needs the Compose stack and therefore
  runs only in the workflow, not in `student-5.ps1`.
