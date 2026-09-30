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

## 2026-09-25 — Agentic Loop Record Review (record `20260925T085024Z`, Stage 1 `attractions.search`)

**Scope:** The finalised Release 1 agentic-loop record `docs/agentic-loop-records/20260925T085024Z-68a0be4d595440b99e2275569c55786f.json`, produced with the loop's own `run`/`finalise` commands to add a `total_matches` field to the new `attractions.search` MCP tool in `ai-services/mcp-server/tools/attractions.py` (Stage 1, branch `KSS/r1-knowledge-and-tools`). This is the first live run of `reviewer-student3-v1.md` (`student3-reviewer-llama32-v1`) on a real task. Reviewed by reading the record's fields directly and re-running the pre/post-test commands, not from the prompt-log summary alone.

### Run configuration

| Field | Value |
|---|---|
| Record file | `20260925T085024Z-68a0be4d595440b99e2275569c55786f.json` |
| Created / finalised | 2026-09-25T08:50:24Z / 2026-09-25T13:04:06Z |
| Task | Add a `total_matches` field to `attractions.search`'s returned dict, equal to the post-filter, pre-limit match count, at a `TODO(you)` marker |
| Context files | `ai-services/mcp-server/tools/attractions.py` only |
| Implementer | `qwen2.5:3b`, prompt `shared-implementer-v1` |
| Reviewer | `llama3.2:3b`, prompt `student3-reviewer-llama32-v1` (first live use) |
| Ollama / options | 0.34.3; temperature 0, context 16,384, max output 4,096 |
| Pre-test | `python -m pytest tests -v` (`ai-services/mcp-server`) — 2 failed / 13 passed, both failures `KeyError: total_matches` |
| Post-test | Same command — 16 passed |

### Phase-by-phase

| Phase | What the model produced | Assessment |
|---|---|---|
| Plan | Restated the goal, requirements, one file, two steps, two risks, and validation against the stated examples. | Accurate paraphrase of the task; no scope drift. |
| Act (round 1) | `total_matches = len(attractions)`, returned alongside the existing sliced `attractions` list. | **Correct.** Matches both worked examples in the task exactly; `len()` on an empty list is `0`, which is the right value for a zero-match search. |
| Observe (1st pass) | `REVISE`, one BLOCKING finding: "`total_matches = len(attractions)` does not check if `attractions` is empty before calculating the length ... will be 0, which is not the expected behavior." Also a "Validation gaps" note that no test covers a zero-matches count. | **The BLOCKING finding is hallucinated.** `len([])` being `0` is correct Python and is exactly the expected value here — there is nothing to check. Confirmed by direct inspection and by running `python -c "print(len([]))"`. The Validation gaps note is separately genuine: the test suite at that point had no zero-matches case. |
| Adapt (machine) | Implementer added a redundant `if attractions: total_matches = len(attractions) else: total_matches = 0` — functionally identical to round 1. Reviewer's second pass returned the identical BLOCKING finding, verbatim, against the revised code. | **The reviewer did not re-evaluate.** Repeating the same finding word-for-word against code that already "fixes" it (when there was nothing to fix) suggests the reviewer model is pattern-matching on the presence of `len(attractions)` in the diff rather than re-checking the logic. Distinct from the `student5-reviewer-llama32-v2` failure mode in the `20260906T104055Z` record (echoing a worked example from the prompt) — this is a new failure mode: a real but wrong finding repeated unchanged after a targeted revision. |
| Adapt (human) | Decision `changed`. Applied round 1's simpler code, not round 2's redundant `if/else`. Rejected the BLOCKING finding as hallucinated. Kept and acted on the genuine Validation gaps note by adding `test_search_reports_zero_total_matches_when_nothing_matches`. | **Correct.** Re-verified: `python -m pytest tests -v` — 16 passed, including the new zero-matches test. |

### Findings

| Severity | Finding | Status |
|---|---|---|
| No action needed | Reviewer's BLOCKING finding was factually wrong (`len([])` misdescribed as unsafe). | Correctly rejected in the human Adapt phase; not a code defect. |
| Resolved | Test suite had no explicit zero-matches case for `attractions.search`. | Fixed: `test_search_reports_zero_total_matches_when_nothing_matches` added, 16/16 passing. |
| Open | `student3-reviewer-llama32-v1`'s grounding rule (every `Evidence:` line must quote the proposal) does not by itself prevent a technically-quoting-but-substantively-wrong finding, and does not stop the reviewer repeating an unchanged verdict against a revised proposal. | Release 1 action: consider a v2 of the reviewer prompt that also asks the reviewer to state whether the ADAPT-stage code differs from what a BLOCKING finding required, before repeating that finding. Note for `prompt-engineering.md`. |

### Automated Evidence

- Pre-test and post-test re-run directly: `python -m pytest tests -v` from `ai-services/mcp-server` — 2 failed/13 passed before, 16 passed after, matching the record's `preTest`/`postTest` fields exactly.
- `python -c "print(len([]))"` confirms `0`, supporting the rejection of the BLOCKING finding.
- Full terminal transcript: `student-3/docs/evidence/release-1/loop/stage1-attractions-search-total-matches-terminal.txt`.

**Verdict (as of 2026-09-25):** The record is complete and finalised. It is useful negative evidence for the new student-3 reviewer prompt: the grounding-in-evidence rule stopped the reviewer from citing code that doesn't exist (an improvement over the borrowed v2 prompt's behaviour in the earlier record), but did not stop it from being confidently wrong about code that does exist, or from repeating that wrong verdict unchanged after a revision. Both are logged as an open action for a future prompt revision, not silently absorbed.

## 2026-09-27 — Agentic Loop Record Review (record `20260927T151638Z`, Stage 2 `RagResponseError.code`, rejected)

**Scope:** Two agentic-loop attempts on the same Stage 2 task (add a `.code` attribute to `RagResponseError` in `student-3/backend/rag_client.py`), using `reviewer-student3-v1.md`. The first attempt errored with no record written; the second produced `docs/agentic-loop-records/20260927T151638Z-f93383dbd3e04763b10832401dcff520.json`, finalised `rejected`. Reviewed by reading the record's fields directly, reading the actual proposed code line by line, and running the pre/post-test commands, not from the prompt-log summary alone.

### Run configuration

| Field | Value |
|---|---|
| Record file | `20260927T151638Z-f93383dbd3e04763b10832401dcff520.json` (attempt 2; attempt 1 produced no record) |
| Created / finalised | 2026-09-27T15:16:38Z / 2026-09-27T15:23:45Z |
| Task | Add a `.code` attribute to `RagResponseError`, extracted from the RAG server's error body, defaulting to `"unknown"` |
| Context files | `student-3/backend/rag_client.py` only |
| Implementer | `qwen2.5:3b`, prompt `shared-implementer-v1` |
| Reviewer | `llama3.2:3b`, prompt `student3-reviewer-llama32-v1` |
| Ollama / options | 0.34.3; temperature 0, context 16,384, max output 4,096 |
| Pre-test | `python -m pytest tests/test_rag_client.py -v` — 2 failed / 7 passed, both `AttributeError: no attribute 'code'` |
| Post-test | `python -m pytest tests -q` (full suite) — 64 passed |

### Attempt 1 (no record written)

The task description for this attempt was longer and more detailed (two worked examples, explicit constraints on which functions not to touch). The implementer's Act phase degenerated into repeating an identical `def __init__(self, message, code="unknown"): self.code = code` block several hundred times instead of producing a coherent proposal. The reviewer's Observe phase on this malformed input itself came out malformed (failed the loop's own "exactly one Validation gaps: section" check), the loop's single format-correction retry also failed the same check, and the run exited with a `LoopException` before `WriteRecordAsync` — no JSON record exists for this attempt, only the terminal transcript (`stage2-ragresponseerror-code-attempt1-failed-terminal.txt`). Retried with a much shorter task description (561 vs. 1294 characters) covering the same requirement, which is attempt 2 below.

### Phase-by-phase (attempt 2)

| Phase | What the model produced | Assessment |
|---|---|---|
| Plan | Restated the goal, requirements, one file, five steps, two risks, and validation. | Accurate paraphrase; no scope drift. |
| Act | `RagResponseError.__init__(self, message, code="unknown")` does set `self.code = code` — contradicting the reviewer's later finding. But `from_response()`'s branch order checks `isinstance(error.get("message"), str)` and returns `code="message_missing"` **before** ever checking `error.get("code")`, so the real code field is unreachable for any body that also has a message (i.e. almost every real error body). And in `ask()`, `raise response_error(response_error.code)` calls an already-constructed `RagResponseError` **instance** as a function, passing its own `.code` as the argument. | **Defective in two independent ways.** Verified against the task's own Example 1 (`{"error": {"code": "dependency_unavailable", "message": "busy"}}`): the backwards branch order yields `.code == "message_missing"`, not `"dependency_unavailable"` — fails the stated example directly. Separately, `response_error(response_error.code)` is not valid Python for calling an instance's method or re-raising it; it raises `TypeError: 'RagResponseError' object is not callable`, which would fire on every non-200 response with a truthy `error` key — the normal case this code exists to handle. |
| Observe (1st pass) | `REVISE`, one BLOCKING finding: "`RagResponseError` object has no attribute code, which breaks the expected behavior." | **Hallucinated**, and it misses both real defects above. The class plainly has a `.code` attribute in this proposal; verified by inspection. The "Validation gaps" note ("no test covers a count of zero") is also copy-pasted from a different task (Stage 1's `total_matches`, which was about counting attractions, not RAG error codes) — a new failure mode: an entire section reused verbatim from an unrelated prior task rather than describing this one. |
| Adapt (machine) | Implementer's revision is **byte-identical** to its first Act output. Reviewer's second-pass Observe repeats the identical BLOCKING finding and the identical (still unrelated) Validation gaps text, unchanged. | Checked by direct comparison of the record's `planAct`/`adaptedProposal` and `observe`/`adaptedProposalReview` fields. Same non-engagement pattern as the `total_matches` record: a wrong verdict repeated verbatim against unchanged code. |
| Adapt (human) | Decision `rejected`. Neither the implementer's proposal nor the reviewer's assessment of it was usable — the code fails the task's own example and contains a fatal `TypeError`, while the review is both wrong about what exists and reused text from a different task. Implemented by hand: `_error_code()` mirroring `_error_message()`'s existing pattern, wired into `RagResponseError` and `ask()`. | **Correct.** Re-verified: `python -m pytest tests -q` — 64 passed, including two new tests asserting `.code == "dependency_unavailable"` for a well-formed error body and `.code == "unknown"` for a malformed one. |

### Findings

| Severity | Finding | Status |
|---|---|---|
| No action needed | Reviewer's BLOCKING finding ("no `.code` attribute") was factually wrong; the attribute exists in the reviewed proposal. | Correctly rejected in the human Adapt phase; not why the code was rejected. |
| Resolved | The implementer's actual code had two real defects (backwards branch order producing a wrong code value; calling an instance as a function) that the reviewer did not catch. | Both fixed in the hand-written replacement; verified against the task's worked examples and the full test suite. |
| Open | A local implementer model can degenerate into token-repetition on a longer, multi-constraint task description, which then cascades into an unparseable reviewer output and an unrecoverable run (no record, wasted ~5-15 min and a model load cycle). Shortening the task text avoided it here, but this is model behaviour, not something the reviewer prompt controls. | Release 1 action: keep loop task descriptions short and example-light where possible; note in `prompt-engineering.md` as an operational constraint distinct from reviewer-prompt quality. |
| Open | The reviewer's "Validation gaps" text in this record was reused verbatim from an unrelated prior task (`total_matches`, a counting bug, not an error-code extraction task), not just a repeated verdict on the same code. | Widens the known reviewer-repetition failure mode already logged for the `total_matches` record: it can also reuse unrelated boilerplate, not only its own worked example or its own prior verdict. Worth a v2 reviewer-prompt note. |

### Automated Evidence

- Pre-test and post-test re-run directly: `python -m pytest tests -q` from `student-3` — 2 failed/7 passed before (scoped to `test_rag_client.py`), 64 passed after (full suite), matching the record's `preTest`/`postTest` fields.
- Manual inspection of `from_response()`'s branch order and the `response_error(response_error.code)` call against the task's Example 1, confirming both defects independently of the reviewer's (wrong) finding.
- Full terminal transcripts: `student-3/docs/evidence/release-1/loop/stage2-ragresponseerror-code-attempt1-failed-terminal.txt` (degenerate repetition, no record) and `...-attempt2-terminal.txt` (this record).

**Verdict (as of 2026-09-27):** The record is complete and finalised as `rejected`, which is the correct outcome — this is the first Stage 2 case where the reviewer's error wasn't just a false positive on working code (as in the `total_matches` record) but a genuine miss of implementer-introduced bugs that would have shipped a broken `.code` extraction and a crash-on-error-path defect had they been accepted. The loop surfaced a real proposal to evaluate, evaluating it caught what the reviewer didn't, and the human Adapt phase replaced it entirely rather than patching around it.

## 2026-09-28 — Agentic Loop Record Review (record `20260928T014432Z`, Stage 3 `confidenceBadgeClass`, kept)

**Scope:** The finalised Stage 3 agentic-loop record `docs/agentic-loop-records/20260928T014432Z-13e1380479ef49e683dfad24f55d13c1.json`, produced to implement `confidenceBadgeClass(confidence)` in `student-3/frontend/index.html` (the RAG panel's confidence-badge CSS-class mapping), finalised `kept`. Reviewed by reading the record's fields directly and running the exact proposed code through `node` myself, not from the prompt-log summary alone.

### Run configuration

| Field | Value |
|---|---|
| Record file | `20260928T014432Z-13e1380479ef49e683dfad24f55d13c1.json` |
| Created / finalised | 2026-09-28T01:44:32Z / 2026-09-28T01:49:57Z |
| Task | Implement `confidenceBadgeClass(confidence)`: map `"high"/"medium"/"low"/"insufficient"` to `"confidence-<level>"`, anything else to `"confidence-unknown"` |
| Context files | `student-3/frontend/index.html` only |
| Implementer | `qwen2.5:3b`, prompt `shared-implementer-v1` |
| Reviewer | `llama3.2:3b`, prompt `student3-reviewer-llama32-v1` |
| Ollama / options | 0.34.3; temperature 0, context 16,384, max output 4,096 |
| Pre-test | `node -e` assertions against the stub — 5/5 failed (`undefined` returned for every input), expected |
| Post-test | Same assertions plus one extra (`undefined` input) — 6/6 passed |

### Phase-by-phase

| Phase | What the model produced | Assessment |
|---|---|---|
| Plan | Restated the goal, requirements, one file, two steps, two risks, and validation. | Accurate; no scope drift. |
| Act | An if/else-if chain for the four known levels, with a final `else { return 'confidence-unknown'; }` covering every other input. | **Correct.** Verified directly: ran the proposed function through `node` against all four known levels plus `"bogus"` and `undefined` — 6/6 match the task's required outputs exactly, and it never throws. |
| Observe (1st pass) | `REVISE`, one BLOCKING finding: "has no guard for unknown inputs... will throw an error when given an unknown input." | **Hallucinated.** The `else` branch *is* the guard; there is no code path that throws. This is the same "reviewer misdescribes code that plainly contradicts the finding" pattern as the `total_matches` record (§2026-09-25) — not the `RagResponseError` record's pattern (§2026-09-27), where the reviewer's finding was wrong but the code underneath actually was broken for other reasons. |
| Adapt (machine) | Implementer's revision is **byte-identical** to its first Act output (confirmed by comparing `planAct`/`adaptedProposal` directly). Reviewer's second pass repeats the identical BLOCKING finding verbatim, plus the identical "Validation gaps" text. | Same non-engagement pattern as both prior records. |
| Adapt (human) | Decision `kept`. The proposal already satisfied the task; no code change was needed. Rejected the BLOCKING finding as hallucinated. | **Correct.** Re-verified post-finalise: 6/6 `node` assertions pass. |

### Findings

| Severity | Finding | Status |
|---|---|---|
| No action needed | Reviewer's BLOCKING finding ("no guard, will throw") was factually wrong; the proposal's `else` branch is the guard and the function cannot throw for any string or `undefined` input. | Correctly rejected; no code was defective. |
| Open | The reviewer's "Validation gaps" text ("no test covers a count of zero") is, again, boilerplate copied verbatim from the unrelated Stage 1 `total_matches` task — third record in a row where this exact phrase appears regardless of what the actual task was. | This is now a confirmed, repeatable failure mode of `reviewer-student3-v1.md` across three independent tasks (2026-09-25, 2026-09-27, 2026-09-28), not a one-off. Release 1 action: a v2 reviewer prompt should require the Validation gaps line to name a concept that actually appears in the current task's requirements, or say `None identified` rather than reuse fixed text. |
| Open | Across all three finalised student-3 records to date, the reviewer's REVISE verdict was correct in intent (something needed checking) only once (`RagResponseError`), and even then its own stated finding was wrong; twice (`total_matches`, `confidenceBadgeClass`) the code needed no change at all. The reviewer has not yet produced a finding that was both correctly identified *and* accurately described. | Track in `prompt-engineering.md` as the residual limitation of `student3-reviewer-llama32-v1`; a future version should be evaluated specifically for finding *accuracy*, not just format compliance and evidence-quoting (which it already satisfies). |

### Automated Evidence

- Pre-test and post-test re-run directly: `node -e` — 5/5 failed before (stub), 6/6 passed after (implemented), matching the record's `preTest`/`postTest` fields.
- Independent verification of the exact proposed code (before finalising) against 6 inputs including one not in the loop's own assertions (`undefined`) — all correct.
- Full terminal transcript: `student-3/docs/evidence/release-1/loop/stage3-confidence-badge-class-terminal.txt`.

**Verdict (as of 2026-09-28):** The record is complete and finalised as `kept`. Combined with the other two finalised records, this establishes a clear, evidence-backed pattern across Release 1: `reviewer-student3-v1.md`'s grounding-in-evidence rule reliably stops it from citing code that doesn't exist, but it has not yet correctly identified a real defect on its own initiative — the one real defect caught this release (`RagResponseError`) was found by the human re-deriving the code's behaviour against the task's examples, not by trusting the reviewer's stated finding. This is documented, not hidden, and is exactly the kind of evidence the assignment's agentic-loop criterion is asking for.

## 2026-09-28 — Agentic Loop Attempt Review (Stage 4 `docker-compose.yml` validation, failed, no record)

**Scope:** A single agentic-loop attempt to add a `docker compose config --quiet` validation step to `scripts/test/student-3.ps1`, which errored before writing a record. Reviewed by reading the terminal transcript directly (`student-3/docs/evidence/release-1/loop/stage4-compose-validation-failed-terminal.txt`) and by running the implementer's actual proposed code, live, against both a valid and a deliberately-broken `docker-compose.yml`.

### What happened

| Phase | What the model produced | Assessment |
|---|---|---|
| Plan | Restated the goal, requirements, one file, four steps, one risk, one validation line. | Accurate; no scope drift. |
| Act | `Push-Location "$repositoryRoot"` / `Invoke-Checked "docker" @("compose","config","--quiet") "Docker Compose config is invalid."` / `Pop-Location`. | **Substantively correct, one real gap.** This does validate the compose file with the exact command asked for. It does not use `try/finally`, unlike the pytest block immediately above it and unlike what the task explicitly asked for — if `Invoke-Checked` throws, `Pop-Location` is skipped and the working directory stays changed for the rest of the session. A real, minor defect, but not the one the reviewer found. |
| Observe (1st pass) | `REVISE`, BLOCKING: "The script does not invoke the docker-compose config validation command, despite the TODO(you) comment requesting it." | **Hallucinated.** The Act code plainly does invoke it. Same class of error as the `total_matches` and `confidenceBadgeClass` records: a confident, wrong claim about code that contradicts it on inspection. |
| Observe (retry, format-corrected) | `REVISE`, BLOCKING: "`docker` is invoked without checking the existence of the docker-compose.yml file... Required correction: Add a check to ensure the docker-compose.yml file exists before invoking the docker command." | **A different finding from the first pass**, not a restatement, and not something the task asked for or a real gap (`docker compose config` already fails clearly, with a specific YAML error, if the file is missing or invalid - a separate existence check would be redundant). This retry's own output was then itself malformed (the loop rejected it: `Reviewer output must contain exactly one Validation gaps: section.`), so the loop errored out entirely with no record. |

### Why this is logged even without a finalised record

Every other entry in this file reviews a finalised record. This one exists because the *failure itself* is evidence: three of four total Release 1 loop attempts have now produced a reviewer finding that does not survive inspection against the actual code (only this attempt failed to even produce a usable record at all). Silently retrying until something parses, without logging the attempts that didn't, would understate how unreliable this reviewer model is on this prompt - the opposite of what the assignment's agentic-loop evidence requirement is asking for.

### What was done instead

Implemented by hand: added the same `Push-Location .../try { Invoke-Checked ... } finally { Pop-Location }` shape already used by the pytest block one line above, so the new step matches the file's own established pattern rather than introducing a new one.

**Verified twice, live, not just re-read:**
1. Ran the full script (`powershell -File scripts/test/student-3.ps1`) against the real, valid `docker-compose.yml` — 64/64 pytest pass, then the new compose-validation step passes silently (exit code 0), confirming it doesn't break the existing happy path.
2. Deliberately corrupted `docker-compose.yml`'s YAML (`sed` inserted an unindented line under `services:`), reran the script, and confirmed it now fails fast with `Docker Compose config is invalid.` plus the real underlying `yaml: line 3: mapping values are not allowed in this context` error - proving the check actually catches a broken config, not just a no-op that always "passes." Restored the original file immediately after and confirmed via `git diff` that only the intended two-line `docker-compose.yml` change (the unrelated `MCP_ENABLED`/`RAG_ENABLED` addition from earlier in this stage) remained.

### Findings

| Severity | Finding | Status |
|---|---|---|
| No action needed | Both reviewer findings across this attempt's two passes were either factually wrong or an out-of-scope invention; neither survived inspection. | Not acted on; the hand-written fix does not include a file-existence pre-check, since `docker compose config` already reports that case clearly. |
| Open | This is the fourth Release 1 agentic-loop task and the second (after the `RagResponseError` attempt 1) to fail outright rather than produce a usable, if wrong, record - both failures were format/parsing breakdowns under the loop's single-retry format-correction rule, not implementer defects. | Release 1 action: `prompt-engineering.md` should track failure rate (record-produced vs. not), not just finding-accuracy-when-a-record-exists, since a task that never produces a record is a total loss of the evidence the assignment wants. |
| Open | The implementer's own code (missing `try/finally`) had a real, if minor, defect neither reviewer pass identified - both were focused on the wrong things entirely. | Consistent with the pattern logged in the 2026-09-28 `confidenceBadgeClass` entry: reviewer accuracy, not just reviewer output format, remains the open problem for a v2 prompt. |

**Verdict (as of 2026-09-28):** No record to finalise, and none was fabricated. The task was completed by hand, verified live under both a passing and a deliberately failing condition, and this failed attempt is logged with the same rigour as a finalised one, because it is equally informative about the reviewer prompt's current limits.

## 2026-09-30 — Agentic Loop Attempt Review (Stage 5 `IsValidStudent3Mcp`, four failed attempts, no record; plus shared `ServiceValidation.cs` extension)

**Scope:** Two things this entry covers together, because the second explains why the first was needed. (1) Extending the shared `ai-services/agentic-loop/ServiceValidation.cs`, which already implemented `validate-mcp`/`validate-rag` for `student-1`/`student-2` (built by other students in earlier chunks) but explicitly rejected any other `--feature`, to also support `student-3`. (2) Four agentic-loop attempts to implement one function of that extension (`IsValidStudent3Mcp`), none of which produced a usable record.

### The shared-code extension

Ownership was confirmed with the group lead before touching this file (Stage 5 is explicitly flagged as shared in the handoff). Added: `DefaultBackendUrl("student-3")` → `http://127.0.0.1:5203`; `DefaultQuestion` for student-3's rag mode; request construction for student-3's actual routes (`POST /api/mcp/invoke {tool, arguments}` and `POST /api/rag/ask {question}` — different from student-1's single assistant endpoint and student-2's trip-scoped routes); and two new validators. `IsValidStudent3Rag` could not reuse the existing shared rag block, because that block explicitly rejects `"insufficient"` as a confidence level (a correct rule for student-1/2, where an unanswerable question is out of scope for this release), while student-3's own contract treats `"insufficient"` as a valid, correct outcome for a genuinely unanswerable question. An existing test, `ValidationModes_RejectUnsupportedFeatureFixtures`, explicitly asserted that `student-3` was rejected; it was repointed at `student-4`/`student-5` (which remain genuinely unsupported) rather than deleted, and new tests were added for both new validators plus the request-construction behaviour, following the same pattern as the existing `student-1` tests (`RecordingHandler`, exact-body assertions). `dotnet test` — 47/47 passing, including the repointed test and all new ones.

### The four loop attempts

| Attempt | What happened |
|---|---|
| 1 (longer task text) | Implementer degenerated into repeating `if (attractions.ValueKind != JsonValueKind.Array) return false;` hundreds of times — the identical failure class already logged for the Stage 2 `RagResponseError` attempt 1 and the Stage 4 compose-validation attempt. No usable proposal. |
| 2 (shortened task text, matching the fix that worked for Stage 2) | Implementer completed normally. At the ACT→OBSERVE transition, `ollama ps` showed **both** `qwen2.5:3b` and `llama3.2:3b` loaded simultaneously (~6.8GB) despite `OLLAMA_MAX_LOADED_MODELS=1` being set. The harness's own background low-memory monitor killed the run before it could be checked further. |
| 3 (same shortened task, retried after unloading both models) | Same double-load at the same transition point, observed live via `ollama ps` and killed manually per the "never both loaded" rule, before the harness needed to intervene. |
| 4 (same task, retried again) | Identical double-load at the identical transition point. Killed manually again. |

None of the four produced a JSON record (`WriteRecordAsync` never runs for a killed process). This is different from the Stage 2/4 failures, which were reviewer-output or implementer-repetition problems the loop's own logic could in principle recover from with a better prompt. This is an **environment** problem: the same double-load recurred at the identical structural point (reviewer model loading before the implementer model unloads) on three consecutive attempts, regardless of task content, which is a stronger signal than task-level flakiness. `OLLAMA_MAX_LOADED_MODELS=1` is confirmed still set in the user environment; the most likely explanation is that Ollama's running server process was never actually restarted after the setting was applied, since that variable is read at server startup, not per-request.

### What was done instead

Implemented `IsValidStudent3Mcp` by hand — the same function written earlier the same day, reverted to a stub for the loop attempts, restored unchanged once the loop attempts were abandoned. Verified with `dotnet test`: 47/47 passing.

For the live evidence the stage actually needs (student-3's cases exercised against the real backend), called `ServiceValidation.CaptureAsync` directly — the exact function `validate-mcp`/`validate-rag` use internally to build their pre-test evidence — rather than through the CLI commands that kept crashing. This function only makes an HTTP call to the student-3 backend; it has no dependency on the implementer/reviewer loop or on Ollama's model-loading behaviour at all, so none of the OOM risk applied. Three cases captured:

1. **`attractions.search {category: "restaurant"}`** — `contractPassed: true`. Real response: 4 restaurants (Chat Thai Sydney CBD, Mr. Wong, Chin Chin Melbourne, Queen Victoria Market), all genuinely category `"restaurant"`, `total_matches` matching the array length.
2. **Unanswerable question** ("What is the capital of France?") — `contractPassed: true`. Real response: the fixed insufficient-context sentence, `confidence: "insufficient"`, no citations. This path never calls Ollama (retrieval finds nothing relevant and short-circuits), so it succeeded on the first attempt.
3. **Answerable question** ("Is Chin Chin busy? Do I need to book?") — failed 4/4 times with `"The local model timed out."`, even after explicitly pre-warming `llama3.2:3b` with a direct Ollama call before each retry. This is the shared RAG server's own fixed 25-second generation deadline (`ai-services/rag-server/server.py`), not code this stage touches. It is a real, reproducible host-latency limit under current load, not a correctness defect: the identical question succeeded with a full grounded answer and citations in Stage 3's live browser test (`student-3/docs/evidence/release-1/stage3-frontend-panels/02-rag-answer-success-with-citations.png`), proving the contract itself works when the host has more headroom.

### Findings

| Severity | Finding | Status |
|---|---|---|
| Open | Ollama's running server process does not appear to honour `OLLAMA_MAX_LOADED_MODELS=1` set in the user environment, causing both loop models to load simultaneously and risking OOM on this 8GB host. Confirmed reproducible across three consecutive attempts at the identical transition point. | Not fixed here (requires restarting the Ollama service, which is outside this session's control). Flagged to the user directly, twice, during this stage. Release 1 action: note in `knownissues.md` as a known local-execution limit of the shared loop on this hardware. |
| No action needed | The shared RAG server's 25s generation deadline is too tight for a full grounded answer under current host load, even with a warm model. | Shared code, not owned by this stage; the contract's correctness is independently proven by Stage 3's earlier successful capture of the same question. Worth raising with whoever owns `ai-services/rag-server/server.py` if this recurs during the group demo. |
| No action needed | Four loop attempts produced zero usable records, extending the pattern from Stages 2 and 4 (implementer repetition, reviewer malformation) with a third failure mode (host environment/memory). | Documented with the same rigour as a finalised record, per the standing instruction not to hide failed attempts. The required live evidence was still obtained, independently of the loop's implementer/reviewer machinery. |

**Verdict (as of 2026-09-30):** No loop record to finalise. The shared-code extension is complete, tested, and used correctly (its own `CaptureAsync` function is what produced the live evidence this stage needed). Four attempts to also exercise the implementer/reviewer loop on this code failed for a genuine, reproducible environment reason unrelated to the reviewer prompt's own accuracy (the subject of every prior entry in this file) — this is the first Release 1 loop failure attributable to host memory/configuration rather than model output quality, and is recorded as such rather than folded into the existing reviewer-accuracy pattern.