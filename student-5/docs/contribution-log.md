# Contribution Log - Student 5

Alex Chen, feature **Travel Logistics & Advisory Service**, Release 0.

Derived from `git log --all --author="alexanderschen08@gmail.com"` across my
`AC/*` branches and `main`. 25 commits between 1 and 6 September 2026, of which
15 are work commits and 10 are the squash/merge commits that landed them on
`main` via pull request. Both are listed, because the merge commit is what makes
the PR number traceable.

## Work delivered, by commit

| Date | Commit | Landed as | What it delivered |
|---|---|---|---|
| 2026-09-01 | `167b2f6` | PR #25 (`c9a3ae3`) | **Database microservice, complete.** `schema.sql` with three tables and cascade deletes; `seed.sql` with 12 destinations, 14 weather notes and 14 transit options; `app.py` with the application factory, generic CRUD handlers shared by all three resources, validation (required fields, non-empty strings, `destination_id` existence checks), partial-merge `PUT`, and `PRAGMA foreign_keys = ON` per connection; 26 pytest tests each against its own `tmp_path` database; Dockerfile with a `urllib`-based healthcheck. 9 files, ~860 lines. |
| 2026-09-01 | `4543fae` | PR #26 (`46bdc8e`) | **Shared agentic-loop tooling fix.** Added `.py` and `.sql` to the loop's accepted `--context` extensions and raised the token limits so larger source files fit in a run. A group-infrastructure change, not a Student 5 one - without it no Python service in the repo could be used as loop context. |
| 2026-09-03 | `319f13b` | (on `AC/agenticloop-work-01-country-filter`) | **`[OBSERVE]` heading regex fix** in the agentic loop's reviewer-output parser - made while investigating why the country-filter run (attempt (a) in `prompt-log.md`) recorded no `[OBSERVE]` header. |
| 2026-09-03 | `5df2930` | PR #34 (`617443d`) | **Backend/API microservice, first half.** `db_client.py` - the only route from the backend to data, returning `DatabaseResponse(status, payload)` rather than raising on 4xx, and raising `DatabaseUnavailable` only on transport failure; `relay()` as the single response chokepoint; the `api` blueprint mirroring the database service's shapes across all three resources; the initial test suite. 6 files, ~680 lines. |
| 2026-09-03 | `b6fb921` | PR #36 (`0d7805b`) | **AI advisory endpoint and HTMX fragment endpoints.** `ollama_client.py` (non-streaming `/api/generate`, 120s timeout, every failure collapsing to `OllamaUnavailable`); `advisory.py` with the four `describe_*` grounding helpers, `build_prompt`, and both the JSON and shared generation paths; `ui.py` plus seven Jinja fragment templates; `parse_destination_id` coercion at the untrusted boundary. Suite grown to 68 tests, all offline. Includes the notes-clearing fix found against a live database - an emptied notes box now sends JSON `null` rather than `""`, because the database accepts null but rejects an empty string. 16 files, ~1837 lines. |
| 2026-09-03 | `9ec2aa1` | PR #37 (`73362b8`) | **Frontend microservice.** Single-page `index.html` with no build step; HTMX 1.9.12 pinned and locked with Subresource Integrity; the destination `<select>` as the single source of truth with the panels `hx-include`ing it; the `htmx:responseError` listener that replaces stale placeholders when the backend itself is unreachable; `nginx.conf` proxying `/ui/` and `/api/` same-origin with `resolver 127.0.0.11` and 180s read timeouts; `style.css`; Dockerfile. 4 files, ~901 lines. |
| 2026-09-04 | `fa948af` | PR #39 (`f514400`) | **Docker Compose integration and the shared home page entry.** All three Student 5 services added to root `docker-compose.yml` on 5105/5205/5305 with healthchecks, dependency ordering behind `student5-database` and `ollama-model-setup`, environment-driven configuration, and the database bind mount. |
| 2026-09-04 | `9adae81` | PR #39 (`f514400`) | Removed duplicated shared home page content. |
| 2026-09-04 | `fc00e4a` | PR #40 (`8351004`) | **CI workflow `.github/workflows/student-5.yml`.** Path-filtered triggers; pip caching against both requirements files; the two pytest suites as **separate** steps (they collide if combined); `docker compose config --quiet`; build of all three images. No live model required. |
| 2026-09-04 | `9e894c9` | PR #40 (`8351004`) | **CI regression fix.** Removed the `/shared/style.css` link and the nginx/Dockerfile plumbing behind it - the file was not present in the Student 5 image and broke the page under CI. Student 5 now ships its own stylesheet. 5 files, 41 deletions. |
| 2026-09-04 | `6058327` | PR #42 (`6215c8c`) | **UX/UI uplift, first pass.** Page restructured onto Student 2's app shell so the five feature frontends read as one product: header, collapsible trip composer, sidebar+main planner grid, admin section tucked into a `<details>`. ~995 lines added. |
| 2026-09-04 | `546c2a4` | PR #42 (`6215c8c`) | **UX/UI uplift, second pass.** Print sheet (`@media print` plus the print-only dateline), accessible naming preserved across HTMX swaps - the advisory heading moved outside the swap target so the section keeps its accessible name after the first generation - and the `hx-indicator` / `hx-disabled-elt` overrides on the destination select that stop it inheriting the advisory form's pair. |
| 2026-09-04 | `3286e20` | PR #44 (`7acd2e4`) | Aligned the shared home page label with the feature's own product name. |
| 2026-09-06 | `6dd3fd2` | PR #50 (`dbbb3e6`) | **`formatElapsed` elapsed-time readout, built through the agentic loop.** The function itself, its timer wiring (`htmx:beforeRequest` / `htmx:afterRequest` with the `isAdvisoryRequest` guard, so the page-load options fetch cannot start a timer nothing stops), and my custom reviewer prompt `docs/prompt-library/reviewer-llama32-v2.md`. Produced through a full Plan -> Act -> Observe -> Adapt cycle with a recorded human decision; record `20260906T053024Z-ad4b32c67df446e8af9e1fca8cc22044.json`. 3 files, 143 lines. |
| 2026-09-06 | `cdf8942` | (on `AC/complete-documentation`) | **Agentic-loop evidence captured.** Three terminal screenshots, the finalised record JSON, and three supporting text captures, into `student-5/docs/evidence/`. 7 files. |
| 2026-09-06 | `a0f5ae0` | (on `AC/complete-documentation`) | **Release 0 documentation pack.** Context, requirements, feature plan, risk plan, sprint backlog, data design, architecture, prompt log, review record, prompt engineering, testing evidence, known issues and contribution log, plus the README rewrite; and the pytest, build and `compose ps` captures into `docs/evidence/`. 18 files, 1669 insertions. |
| 2026-09-06 | `5adfd3f` | (on `AC/complete-documentation`) | **Evidence index reconciled and the three required diagrams added.** Every pytest / Compose TODO replaced by a reference to the committed capture with its result line quoted; Mermaid diagrams for the Compose architecture, the DevOps pipeline and the Plan/Act/Observe/Adapt workflow in `architecture.md`; the `student-5.yml` step-by-step description in `testing-evidence.md`. 5 files, 281 insertions. |
| 2026-09-06 | (working tree) | (on `AC/complete-documentation`) | **Final evidence capture and documentation close-out.** The green CI run (`ci-run-green.png`) and four application screenshots (`ui-filled-panels.png`, `ui-advisory-output.png`, `ui-advisory-loading.png`, `ui-manage-table.png`) into `docs/evidence/`; the last two TODOs replaced across `testing-evidence.md`, `requirements.md`, `feature-plan.md` and `sprint-backlog.md`; evidence-completeness mapping added. No documentation item is outstanding. |

## Pull requests

| PR | Branch | Merge commit | Scope |
|---|---|---|---|
| #25 | `AC/student5-release-0` | `c9a3ae3` | Database microservice |
| #26 | `AC/agentic-loop-ext-fix` | `46bdc8e` | Agentic-loop context-extension and token-limit fix |
| #34 | `AC/backend-api` | `617443d` | Backend CRUD passthrough and database client |
| #36 | `AC/ai-advisory-endpoint` | `0d7805b` | Advisory endpoint and HTMX fragments |
| #37 | `AC/frontend-HTMX-microservice` | `73362b8` | Frontend microservice |
| #39 | `AC/docker-integration-and-shared-home-page` | `f514400` | Compose integration, shared home entry |
| #40 | `AC/ci-workflow-implementation` | `8351004` | CI workflow and the shared-stylesheet regression fix |
| #42 | `AC/UX-UI-uplift` | `6215c8c` | Design-system uplift |
| #44 | `AC/shared-home-page-tweak` | `7acd2e4` | Naming alignment |
| #50 | `AC/agenticloop-work-elapsed-timer` | `dbbb3e6` | Agentic-loop deliverable and reviewer prompt |

## Summary by area

| Area | Contribution |
|---|---|
| Database service | Schema, seed, full CRUD API, validation, cascade deletes, idempotent seeding, 26 tests, container |
| Backend service | HTTP database client, JSON passthrough, Ollama client, grounded advisory workflow, HTMX fragment blueprint with 7 templates, 68 tests |
| Frontend service | Single-page HTMX application, nginx edge with same-origin proxying, own stylesheet, print sheet, client-side failure handling |
| Integration | Three Compose services with healthchecks and dependency ordering; shared home page entry |
| CI | `student-5.yml` - two test suites, Compose validation, three image builds; green run captured (`ci-run-green.png`) |
| Group infrastructure | Agentic-loop context-extension fix, token-limit increase, `[OBSERVE]` regex fix |
| AI workflow evidence | One completed and finalised Plan/Act/Observe/Adapt record, custom reviewer prompt, six artefacts covering the run |
| Documentation | This `docs/` folder - 13 documents, three architecture diagrams, and 17 indexed evidence artefacts with nothing outstanding |

## Note on the record

Three agentic-loop attempts before the successful one produced no artefacts and
therefore no commits; they are documented in `prompt-log.md` from the working
session rather than from the repository history.
