# Student 3 Review Record

## 2026-09-03 — Frontend CRUD UI Review (PR #38)

**Scope:** `student-3/frontend/app.js`, `index.html`, and `style.css` changes in PR #38, which add create/edit/delete UI for attractions and a review-submission form. Reviewed against `requirements.md` FR-03–FR-08 and the existing `escapeHtml`/HTMX conventions in the pre-existing code. Reviewed by reading the actual PR diff (`git fetch origin pull/38/head`), not just the author's summary of it.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Resolved | Backend and database had full attraction CRUD and review create/list, but the frontend only supported Read — no UI existed to create, edit, or delete an attraction, or to submit a review, despite the spec requiring CRUD "through the frontend and backend microservices." | Resolved by PR #38: create form (`#manage`), inline edit-form swap per card, delete with confirmation, and a collapsible review form per card. |
| Resolved | HTMX forms submit as `x-www-form-urlencoded` by default; `create_attraction`/`update_attraction`/`create_review` only accept a JSON body (`request.get_json(silent=True)`, no form-data fallback, unlike `/api/recommend` and `/api/itinerary`) — new forms would silently receive an empty payload and 400. | Resolved with an inline `json-body` htmx extension serialising parameters as JSON and coercing `rating`/`attraction_id` to numbers. Confirmed against the live containers with curl: the same request without the extension returns a validation error; with it, the record is created correctly. |
| Resolved | Interpolating `escapeHtml(attraction.name)` directly into an HTML attribute (e.g. `value="..."`) would be unsafe — `escapeHtml()` only escapes `&`/`<`/`>` for text-content use, not `"`, so a name containing a double quote could break out of the attribute. | Resolved: edit-form inputs are populated via the `.value` DOM property after the form is in the document, which treats the string as data regardless of content — no attribute-escaping path exists to exploit. |
| Resolved | `refreshAttractions()` tried to preserve the active category filter via `currentCategory = event.detail.requestConfig.parameters.category`, but the filter buttons are plain `<button>` elements outside any `<form>`, with the category baked directly into each button's `hx-get` URL rather than submitted as a named parameter, so `.category` was always `undefined`. | **Confirmed broken in a real browser** (filtered to "Restaurants," deleted a card, list reset to "All" — `evidence/01-currentCategory-bug-confirmed-reset-to-all.png`), then fixed by setting `currentCategory` at each filter button's own `hx-on:click` instead of reading it back from the request, and re-verified: filtered to "Restaurants," deleted every remaining restaurant one at a time, list stayed filtered throughout including the empty state after the last one — `evidence/02-currentCategory-bug-fixed-empty-state-stays-filtered.png`. See `riskplan.md` R-06 for the full trace. |
| No action needed | Review CRUD is create/list only (no update/delete). | Confirmed as an intentional Release 0 scope decision, not an oversight — documented in `requirements.md` §1.2. Attractions are the primary CRUD resource per the Group 45 registration form. |

### Automated Evidence

- `python -m pytest tests` (from `student-3/`) — 29/29 pass, unmodified by this PR (the backend/database contract was not changed).
- `docker compose up -d --build student3-frontend` — all three student-3 containers plus their dependencies came up healthy.
- Live curl round-trip: create → appears in list → update → create review → delete → confirmed 404 after delete. Both validation-error paths (missing `name`; string `attraction_id`) returned the expected 400s.
- Browser-based visual verification was **not yet performed at the time of this review** (no browser available in the environment that produced it). See the 2026-09-04 entry below — that gap is now closed.

**Verdict (as of 2026-09-03):** The frontend CRUD gap identified for Release 0 is functionally resolved and the backend contract remains untouched and passing. One UX detail (filter preservation across mutations) is plausibly broken and needs a two-minute manual check; everything else checked out against the real diff and live containers. Recommend merging after the manual browser pass in `known-issues.md`'s evidence checklist, and after `student-3.yml` shows a green run on this branch.

## 2026-09-04 — Browser Verification Pass (Playwright, integrated app)

**Scope:** The manual browser click-through this review record's 2026-09-03 entry and `known-issues.md` both flagged as outstanding, run against the real containers (`docker compose up -d --build student3-frontend`, plus `shared-frontend`/`student1-frontend`/`student2-frontend` so the walk-through went through the integrated home page at `:5100`, not the standalone `:5103` dev port). Screenshots saved to `docs/evidence/`.

### Results

| Check | Result | Evidence |
|---|---|---|
| `currentCategory` filter-preservation bug | **Confirmed broken, then fixed and re-verified** — see `riskplan.md` R-06 for the full trace. | `evidence/01-*.png`, `evidence/02-*.png` |
| Create an attraction via `#manage` | Pass — new card ("Harbour Bridge Climb") appeared in the list without a full page reload, form cleared, success message shown. | `evidence/03-create-attraction-success.png` |
| Edit an attraction | Pass — clicking Edit swapped the card for an inline form correctly pre-filled with the current name/category/description/rating; Save updated the card in place (new name, ★5) without a reload. | `evidence/04-edit-attraction-success.png` |
| Delete an attraction | Pass — `hx-confirm` native dialog appeared with the expected message ("Delete this attraction?"); accepting it removed the card from the list. (The dialog itself isn't screenshot-able — native browser dialogs aren't part of the page's render surface — confirmed instead via the automation tool's own modal-state report.) | `evidence/06-delete-attraction-success.png` |
| Submit a review via the per-card toggle | Pass — toggle expanded a rating/comment form on the Sydney Opera House card; submitting showed "Review added.", cleared the form, and the review was confirmed present via a follow-up `GET /api/attractions/1` (id 15, correct attraction_id/rating/comment). | `evidence/07-review-submit-success.png` |
| Invalid input: empty name | Pass — native HTML5 `required` validation blocks submission client-side with a visible "Please fill in this field." bubble; no request is sent. Matches `requirements.md` FR-03's "validates ... required client-side and server-side" wording. | `evidence/08-invalid-empty-name-blocked.png` |
| Invalid input: rating outside 0–5 (tried 6) | Pass — native `max="5"` constraint blocks submission client-side (`validity.rangeOverflow`, message "Value must be less than or equal to 5."); no request is sent. (A separate, unplanned finding during create testing: entering `4.9` was also blocked, correctly, by the `step="0.5"` constraint — a testing mistake on my part, not a defect.) | `evidence/09-invalid-rating-out-of-range-blocked.png` |
| Narrow viewport (375×800) | Pass — filter buttons and each card's Add-to-itinerary/Edit/Delete row wrap onto a second line via the existing `flex-wrap`, no horizontal overflow (`document.documentElement.scrollWidth === clientWidth === 375`), the `#manage` form fields stack full-width. | `evidence/10-narrow-viewport-375px.png` |

### Process notes (kept for anyone repeating this verification)

- **The test browser itself introduced a false negative.** After rebuilding the `student3-frontend` image with the R-06 fix, the first re-test still appeared to fail — the list still reset to "All" after a delete. The cause was the test browser's HTTP cache: nginx sends `Last-Modified`/`ETag` for static files but no `Cache-Control`, so Chromium heuristically cached both `index.html` and `app.js` from the very first (pre-fix) page load, and successive `page.goto()` calls to the bare URL kept re-serving that stale copy without revalidating. Confirmed via `document.querySelector(...).outerHTML` showing the DOM lacked the new `hx-on:click` attributes despite the served-over-curl HTML containing them. Resolved for testing purposes with a cache-busting query string on every navigation (`?v=N`) — no application code was changed to work around this; it is purely a test-environment artifact, not a product bug.
- Two accidental deletions of real seeded attractions ("Chat Thai Sydney CBD" during the initial bug-confirmation pass, and "Great Ocean Road Day Trip" from clicking a stale element reference after a list re-render) happened during testing. Both times the database was reset and reseeded (`docker compose stop student3-database && rm student-3/database/storage/attractions.db && docker compose run --rm --no-deps student3-db-init && docker compose start student3-database`) to restore the canonical 12 attractions / 14 reviews before continuing. The final state after this session is the pristine reseeded set, confirmed via `GET /api/attractions` returning 12 rows and `python -m pytest tests` passing 29/29 afterward.
- Not covered in this pass: the "Ask the AI" recommendation flow (success and fallback cases) and a live GitHub Actions run for this branch — both remain open in `known-issues.md`.

**Verdict (as of 2026-09-04):** Every item this review record and `known-issues.md` listed as "unverified" or "not yet confirmed in a browser" has now been checked against the integrated app and passes, including the R-06 fix. Remaining before this feature is fully release-ready: merge this branch, capture a green `student-3.yml` Actions run on it, produce the agentic-loop record, and capture AI-recommendation screenshots (success + fallback) — none of which this pass was scoped to do.

## 2026-09-25 — Agentic Loop Record Review (record `20260906T104055Z`, PR #55)

**Scope:** The finalised shared agentic-loop record `docs/agentic-loop-records/20260906T104055Z-f52cc6be69164e07b0502a263671ee67.json`, produced with `docker compose exec agentic-loop dotnet /app/AgenticLoop.dll run` and `finalise` to implement `formatElapsed(seconds)` for the "Get Recommendation" wait indicator, and the code merged from it in PR #55 (`eb40659`). Reviewed by reading the record's fields directly and comparing them against `student-3/frontend/index.html` on `main`, not against the prompt-log summary alone. Written up after the fact because the record existed but this file, `architecture.md`, and `knownissues.md` still said it did not.

### Run configuration

| Field | Value |
|---|---|
| Record file | `20260906T104055Z-f52cc6be69164e07b0502a263671ee67.json` |
| Created / finalised | 2026-09-06T10:40:55Z / 2026-09-06T10:43:50Z |
| Task | Implement `formatElapsed(seconds)` in `student-3/frontend/index.html` at the `TODO(you)` marker (empty for < 2s, `'14s'` form from 2s, `'still working - 52s'` form from 45s), plus a commented-out `node -e` assertion snippet |
| Context files | `student-3/frontend/index.html` only |
| Implementer | `qwen2.5:3b`, prompt `shared-implementer-v1` |
| Reviewer | `llama3.2:3b`, prompt `student5-reviewer-llama32-v2` (borrowed from `student-5/docs/prompt-library/`) |
| Ollama / options | 0.33.2; temperature 0, context 16,384, max output 4,096 |
| Pre-test | `grep -n 'TODO(you)' student-3/frontend/index.html` — stub present, returns empty string |
| Post-test | `node -e` with 6 assertions (0, 1, 2, 14, 45, 52) — all passed |

`qwen2.5:3b` replaced the default `qwen2.5-coder:7b` implementer because the 7B model cannot load on this 8GB host (see `prompt-log.md`, "Operational note"). The two models are still distinct, which the loop enforces.

### Phase-by-phase

| Phase | What the model produced | Assessment |
|---|---|---|
| Plan | Restated the goal, requirements, the one file, two steps, two risks, and validation against the six required inputs. | Accurate but mostly a paraphrase of the task. Step 2 ("call the function ... once per second") describes the existing caller, which the task said not to change. Harmless here, because nothing in Act touched the caller. |
| Act | A three-branch `formatElapsed` with the right thresholds but wrong arithmetic: `seconds - 2` in the compact branch and `seconds - 45` in the reassurance branch. Its "Unresolved" section claimed the function met every target and did not include the required assertion snippet. | **Defective.** `formatElapsed(14)` returns `'12s'` and `formatElapsed(52)` returns `'still working - 7s'`, contradicting the targets the Plan itself restated. The self-report is also false: the snippet is missing. |
| Observe (1st pass) | Per `prompt-log.md`, the first reviewer output was `ACCEPT` with one SUGGESTION (negative input), but the loop rejected it as malformed (two `[OBSERVE]` sections). The format-correction retry recorded as `observe` is `REVISE` with one REQUIRED finding: "divides by `count` without a zero check". | **Hallucinated.** The proposal has no division, no list and no `count`. The finding is the worked REVISE example from the reviewer prompt, reproduced verbatim. The reviewer also missed the real arithmetic defect. |
| Adapt (machine) | `adaptedProposal` is **byte-identical to `planAct`**. `adaptedProposalReview` is byte-identical to `observe`, apart from a stray trailing `END_GOAL` token. Final verdict `REVISE`. | Checked by direct string comparison of the record fields on 2026-09-25. The implementer could not act on a finding about code that does not exist, so it resubmitted unchanged, and the reviewer repeated itself. The single bounded machine revision added nothing. |
| Adapt (human) | Decision `changed`. Removed both stray subtractions. Added the missing six-case assertion snippet. Rejected both REQUIRED findings as hallucinated after confirming there is no division, list or `count` in the file. Kept the genuine first-pass SUGGESTION (negative `seconds`) as a documented non-issue, because the caller computes `Math.floor((Date.now() - startedAt) / 1000)`, which cannot go negative. | **Correct.** The merged function on `main` (`index.html`, `formatElapsed`) shows `seconds` unchanged in both branches, with the assertion comments below it. |

### Findings

| Severity | Finding | Status |
|---|---|---|
| Resolved | `architecture.md`, `knownissues.md` and `featureplan.md` all stated that no student-3 record existed, although this record had been finalised and merged on 2026-09-06. | Corrected on 2026-09-25 in all three files. The record is also added to `contributionlog.md`. |
| Resolved | The implementer's arithmetic did not match its own stated targets. | Fixed in the human Adapt phase before merge. Re-verified on 2026-09-25: the six assertions against the merged function pass 6/6 under `node -e`. |
| No action needed | Both reviewer REQUIRED findings describe code that does not exist. | Correctly rejected in the human Adapt phase. This is the known failure mode documented in the borrowed reviewer prompt's header, where a 3B reviewer echoes the prompt's example. |
| Open | The reviewer prompt was Student 5's (`student5-reviewer-llama32-v2`), tuned for Student 5's code, not a student-3 prompt. | Release 1 action: write and version a student-3 reviewer prompt under `student-3/docs/prompt-library/` and use it for every Release 1 loop run. |
| Open | No terminal screenshots of the `run` or `finalise` invocations were captured, so the JSON record and `prompt-log.md` are the only evidence of the run itself. | Release 1 action: capture terminal output for every loop run under `student-3/docs/evidence/`. |
| Open | The loop's context allowlist excludes `.js`, which is why this function lives in an inline `<script>` in `index.html` and not in `app.js`. | Logged in `prompt-log.md`. Raise with the group as part of the Release 1 loop extension. |

### Automated Evidence

- Record fields read and compared directly (Python `json` load): `adaptedProposal == planAct` → `True`; `observe` equals `adaptedProposalReview` with the trailing `END_GOAL` removed → `True`.
- `node -e` against the merged `formatElapsed` (inputs 0, 1, 2, 14, 45, 52) — 6/6 assertions pass.

**Verdict (as of 2026-09-25):** The record is complete and finalised, and it satisfies every field the `docs/agentic-loop-records/README.md` checklist requires. It shows the loop working as designed: the gates caught a malformed reviewer output, the loop refused to apply its own verdict, and the human Adapt phase fixed a real defect the reviewer missed while rejecting two findings that were not real. The gaps are around the record, not in it: stale docs (fixed here), no screenshots, and a borrowed reviewer prompt. The last two carry into Release 1 as actions.
