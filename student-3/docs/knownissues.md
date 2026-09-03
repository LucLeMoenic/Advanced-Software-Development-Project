# Local Experience & Attraction Recommender — Known Issues and Limitations

## Open Evidence Gaps

- PR #38 (frontend CRUD UI) is open, not yet merged to `main` as of this document (confirmed via `git merge-base --is-ancestor`, not assumed). Until it merges, the deployed/integrated app only has backend/database CRUD, not frontend CRUD.
- ~~No browser-based visual verification has been performed on PR #38's UI~~ **Resolved 2026-09-04.** Card layout, the edit-form inline swap, the review-toggle expand/collapse, empty-name/out-of-range-rating client-side validation, and responsive behaviour at 375px were all click-tested against the integrated app with Playwright and pass — see `review-record.md`'s 2026-09-04 entry and `docs/evidence/03-*.png` through `10-*.png`. Not covered by this pass: the "Ask the AI" recommendation flow (success/fallback screenshots).
- ~~`refreshAttractions()`'s attempt to preserve the active category filter... not yet confirmed either way~~ **Resolved 2026-09-04.** Confirmed broken in a real browser (filtering to "Restaurants" then deleting a card reset the list to "All"), fixed by capturing the category at each filter button's own `hx-on:click`, and re-verified. See `riskplan.md` R-06 and `review-record.md`.
- No successful `student-3.yml` GitHub Actions run URL/screenshot has been captured for the PR #38 branch specifically (earlier workflow runs on `main` have passed). Still open — not addressed by the 2026-09-04 verification pass, which ran `pytest` and the live containers locally, not GitHub Actions itself.
- No finalised agentic-loop development record (`docs/agentic-loop-records/<record>.json`) exists for student-3. Checked again on 2026-09-04 (`ls docs/agentic-loop-records/`) — still only `README.md`, no student-3 record. This is a gap shared by the whole team (no team member has one yet), but it blocks Release 0 marking criteria 4 and 5 for my submission specifically until it's produced.
- Integrated-app screenshots for CRUD and review submission now exist (`docs/evidence/`, 2026-09-04). Still pending: AI-recommendation screenshots (success + fallback), the attendance checkpoint, and my segment of the group showcase video.
- The project specification lists Release 0 as due 30 August 2026; the latest repository commit is still dated 3 September 2026 as of 2026-09-04. Not yet confirmed with the tutor whether an extension applies.

## Product/Scope Limitations (intentional, Release 0 scope)

- RAG-based grounding over a curated destination knowledge base is explicitly Release 1 scope for this feature (per the Group 45 registration form). Release 0 uses closed-context prompting only — the model is limited to attractions the database's own filtered query returned.
- Review CRUD is create/list only; there is no review update/delete. This is a deliberate scope decision — the feature's primary CRUD resource is the attraction, and full CRUD is implemented there.
- `POST /api/itinerary` ("Add to itinerary") is an intentional Release 0 stub that logs the request and returns `202`; real itinerary persistence is owned by Student 1's feature and is a later integration point, not a student-3 defect.
- `category` is a free-text column, not a database-level enum — the `sight`/`restaurant`/`activity` set is enforced only by the frontend, not by the schema. A malformed category submitted directly to the API (bypassing the UI) would be stored as-is. Considered low risk for Release 0 since the only write path in normal use is the frontend's `<select>`.
- Cascade-delete of a review when its parent attraction is deleted is enforced in application code (`student-3/database/app.py`), not by a SQLite foreign-key constraint — `schema.sql` does not declare `ON DELETE CASCADE`. Functionally equivalent for Release 0, but worth tightening at the schema level if there's time.
- No authentication — reviews and attraction edits are not attributed to a user. Acceptable for a Release 0 classroom demonstration; would need addressing before any real deployment.

## Rollover Checklist (close before submission)

- [ ] Merge PR #38 (browser pass below is done; this is the remaining blocker).
- [x] Filter to "Restaurants," delete an attraction, confirm the list stays filtered — done 2026-09-04, bug found and fixed (`riskplan.md` R-06).
- [x] Click through: create, edit, delete an attraction; submit a review — all against the integrated app — done 2026-09-04 (`review-record.md`).
- [ ] Capture a green `student-3.yml` Actions run for the merged branch.
- [ ] Produce and finalise a student-3 agentic-loop record.
- [x] Capture CRUD/review/validation/responsive screenshots — done 2026-09-04, see `docs/evidence/`.
- [ ] Capture AI-recommendation screenshots (success + fallback) — not covered by the 2026-09-04 pass.
- [ ] Record the Week 6 attendance checkpoint.
- [ ] Confirm the Release 0 due date/extension with the tutor.
