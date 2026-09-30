# Local Experience & Attraction Recommender — Known Issues and Limitations

Rewritten for Release 1 on 2026-09-30. Release 0's own known-issues history
(PR #38 merge, the `currentCategory` bug, the first agentic-loop record) is
preserved in `reviewrecord.md` and `contributionlog.md`, not repeated here —
every item below that referenced them as "open" has been resolved and
removed rather than carried forward stale.

## Open Evidence Gaps (Release 1)

- No successful `student-3.yml` GitHub Actions run link/screenshot has been captured for a Release 1 branch or PR. Local validation (real `docker compose build`/`run`/`up`, real smoke curls including the new disabled-body assertions) is captured in `docs/evidence/release-1/stage4-compose-ci-terminal.txt`, but that is not the same evidence as a green Actions run.
- The answerable-RAG-question case in Stage 5's live evidence capture timed out 4/4 times against the shared RAG server's own 25-second generation deadline, even with the model pre-warmed (see the Release 1 Local-Execution Limits section below). The underlying contract is proven working by Stage 3's earlier successful browser capture of the identical question, but that capture is now the only evidence of the answerable-question path succeeding end-to-end; it should be re-attempted for the report/demo when the host has more headroom (fewer other processes running, or after an Ollama restart — see below).
- The group showcase video and my segment within it have not been recorded.
- The Week 9 showcase attendance checkpoint has not been recorded.

## Release 1 Local-Execution Limits

- **Ollama does not reliably honour `OLLAMA_MAX_LOADED_MODELS=1`** on this host. Confirmed 2026-09-30: three consecutive agentic-loop attempts (Stage 5, `IsValidStudent3Mcp`) showed both loop models (`qwen2.5:3b`, `llama3.2:3b`, ~6.8GB combined) loaded simultaneously via `ollama ps`, despite the variable being set in the user environment. Most likely cause: the setting is read at Ollama server startup, not per-request, and the running server was never actually restarted after it was set. Mitigation used: manually killing the loop process and stopping both models the moment double-loading is observed, rather than relying on the setting alone. This blocks running the shared agentic loop's `run`/`validate-mcp`/`validate-rag` commands reliably on this machine until Ollama is properly restarted. See `reviewrecord.md` 2026-09-30 for the full account.
- **The shared RAG server's fixed 25-second generation deadline** (`ai-services/rag-server/server.py`) can be too tight for a full grounded answer under host load, even with the model pre-warmed — observed 4/4 times on 2026-09-30 for a question that had succeeded (with a full answer and citations) in Stage 3's browser test under lighter load. Not a correctness defect in student-3's own code; flagged for whoever owns that shared file if it recurs during the group demo. Mitigation for the demo: pre-warm the model with a throwaway Ollama call and close other CPU-heavy applications immediately beforehand.
- **The shared agentic loop's reviewer model (`llama3.2:3b`, `student3-reviewer-llama32-v1`) has not yet correctly identified a real defect on its own initiative** across all three finalised Release 1 records (`total_matches`, `RagResponseError.code`, `confidenceBadgeClass`) plus the shared `IsValidStudent3Mcp` extension. It either hallucinates a finding against code that contradicts it, or reuses boilerplate text from an unrelated earlier task. The one real defect caught this release (`RagResponseError`'s backwards branch order and `TypeError`-on-error-path bug) was found by the human re-deriving the code's behaviour against the task's own worked examples, not by trusting the reviewer's stated finding. Every reviewer finding in Release 1 was independently verified against the actual code before being accepted or rejected — see `reviewrecord.md` for the full, dated account across all records. This is a documented limitation of the current reviewer prompt, not something papered over.
- **A local implementer model (`qwen2.5:3b`) can degenerate into runaway token repetition** on a real (not toy) task, most reliably avoided by keeping loop task descriptions short and example-light rather than long and multi-constraint. Observed on the `RagResponseError.code` task (Stage 2), the compose-validation task (Stage 4), and the `IsValidStudent3Mcp` task (Stage 5). When it happens, the run either errors outright (if the resulting reviewer output is also unparseable) or wastes a full model-load cycle for nothing; the fix each time was shortening the task text, not changing the code being asked for.
- **scikit-learn has no prebuilt wheel for this host's Python 3.14** and failed to build from source during Stage 1 development; the RAG server's retrieval module was deliberately written as hand-rolled TF-IDF using only the standard library to avoid depending on it (see `ai-services/rag-server/retrieval.py`'s own header comment). This also means retrieval quality is bounded by TF-IDF's lexical-overlap limitations (no semantic matching), not embedding-based similarity — acceptable for a knowledge base this small, but worth stating plainly rather than implying embedding-quality retrieval.

## Product/Scope Limitations (intentional)

- RAG's retrieval is TF-IDF/lexical, not embedding-based (see above) — a question that doesn't share vocabulary with the relevant knowledge doc may score as insufficient even if a human would consider it answerable. Confidence thresholds (`ai-services/rag-server/confidence.py`) were calibrated by another student's chunk against a small fixture set, not an independent held-out evaluation.
- MCP tools are read-only by design (`attractions.search`, `attractions.get_reviews`); there is no MCP tool for creating, updating, or deleting attractions or reviews — the existing CRUD API is the only write path.
- `attractions.search`'s `category` filter accepts exactly `sight`/`restaurant`/`activity` (the allow-listed set the tool itself enforces); an unrecognised category is rejected with a structured error rather than silently ignored.
- Review CRUD is create/list only; there is no review update/delete. This remains a deliberate scope decision carried over from Release 0 — the feature's primary CRUD resource is the attraction, and full CRUD is implemented there.
- `POST /api/itinerary` ("Add to itinerary") remains an intentional stub that logs the request and returns `202`; real itinerary persistence is owned by Student 2's feature.
- `category` is still a free-text column, not a database-level enum, enforced only by the frontend `<select>` and the MCP tool's own allow list — not by the schema.
- No authentication — reviews, attraction edits, and MCP/RAG queries are not attributed to a user. Acceptable for a classroom demonstration; would need addressing before any real deployment.
- Ownership of the shared MCP server (`ai-services/mcp-server/`), RAG server (`ai-services/rag-server/`), and the `validate-mcp`/`validate-rag` loop extension is informal — these were built collaboratively across students' "chunks" without a single named owner. Student 3's contributions to shared code (the `ServiceValidation.cs` student-3 extension, the extra-top-level-field fix to the MCP tool wrapper, the retrieval stopword fix) were each confirmed with the group lead before merging, per the project's own coordination rule, but the shared files themselves have no single point of contact if something regresses.

## Rollover Checklist (close before submission)

- [x] Release 1 Stage 1 — MCP tools + RAG knowledge base (PR #62).
- [x] Release 1 Stage 2 — backend MCP/RAG integration (PR #79).
- [x] Release 1 Stage 3 — frontend MCP/RAG panels, verified live in a browser (PR #80).
- [x] Release 1 Stage 4 — Compose/CI wiring, verified live against real containers (PR #86).
- [x] Release 1 Stage 5 — shared loop validation-mode extension for student-3 (PR #89).
- [ ] Release 1 Stage 6 — this evidence/report/cleanup pass (in progress).
- [ ] Capture a green `student-3.yml` Actions run link for a Release 1 PR.
- [ ] Re-capture the answerable-RAG-question live evidence once Ollama has more headroom (see Local-Execution Limits above).
- [ ] Restart Ollama's background service so `OLLAMA_MAX_LOADED_MODELS=1` actually takes effect, for any further loop runs.
- [ ] Record the Week 9 showcase attendance checkpoint.
- [ ] Record my segment of the group showcase video.
- [ ] Confirm the Release 1 due date (4 Oct 2026 vs. 27 Sept per `Project_Specifications.md`) with the tutor.
