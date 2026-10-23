# Budget & Expense Tracker Feature Plan

## Current Release 2 Delivery - 2026-10-23

Implemented in the uncommitted workspace: deterministic What-If preview,
preview/start/poll/decision APIs, static frontend, protected workflow binding and
integration with the existing native shared Planner/Worker/Reviewer service.
All four explicit human decision paths are implemented; no decision writes
financial data. No schema change or new runtime dependency was added.

This supersedes the calculator-only status and deferred endpoints/UI/CI/cloud
items in the earlier **Release 2 Spec** checkpoint below, not its calculation
contract or historical 74-test result. Current acceptance IDs are
[R2-01 through R2-12](requirements.md#release-2-acceptance).

Recorded validation: 322 backend tests (including the 74 calculator tests),
79 frontend tests/build, 35 Student 4 cloud tests and 210 related cloud-suite
tests; Compose config, four images and the four-container subset passed.
The real gateway/native workflow reached `awaiting_human_review` with concerns,
`degraded=false`, and no human decision. Preview captures at 1280/768/320px have
no horizontal page overflow.

Next evidence gates: genuine human decision/history and confirmed awaiting-human
browser capture; fresh full-group/R1 replay; post-push CI; live integrated cloud;
three report-review mode runs and human finalisation; group report/video/Q&A.
No release grade, final approval, commit or push is claimed. Use the
[runbook](release-2-runbook.md) and
[evidence record](evidence/release-2/validation-2026-10-23.md); earlier delivery
stages and release checkpoints below are retained as history.

## High-Level Design

Implement three independently containerised Student 4 services behind the
existing shared frontend. The static frontend presents complete budget and
expense CRUD. The backend owns public validation, deterministic conversion and
aggregation, and optional AI advice. The database API owns EF Core, SQLite,
migrations, constraints, and idempotent sample data.

## Delivery Stages

### Stage 0: Plan

- Validate scope against the Release 0 brief and current repository.
- Define testable functional, non-functional, and evidence requirements.
- Define service/data/Compose/DevOps architecture and risk controls.

Exit: no unresolved architecture blocker; documents reflect approved scope.

### Stage 1: Database API

- Create ASP.NET Core 8 database service, entities, EF configurations, initial
  migration, repositories, validation, stable errors, filters, and health.
- Add 12 budgets and 24 expenses through idempotent initialization.
- Add temporary-SQLite integration tests for migrations, CRUD, filtering,
  conflicts, foreign keys, cascade delete, exact integer storage, and seeds.

Exit: database tests pass and both tables contain at least ten rows.

### Stage 2: Backend API

- Add typed database client and stable dependency-error mapping.
- Add public budget/expense CRUD, journey list, currencies, conversion preview,
  and deterministic dashboard endpoints.
- Add fixed-rate provider configuration and unit/integration tests.

Exit: backend CRUD, conversion, aggregation, status, validation, and dependency
tests pass without EF Core or SQLite references.

### Stage 3: Application AI

- Add versioned prompt and typed Ollama client.
- Send an allow-listed dashboard summary as untrusted data.
- Require complete strict JSON, reject unknown fields/categories, retry once,
  and return deterministic fallback advice for every model failure.

Exit: valid, retry, malformed, partial, wrapped, unknown, extra-field, timeout,
connection, HTTP, and no-data tests pass without a live LLM.

### Stage 4: Frontend

- Build the working dashboard as the first screen using semantic HTML,
  feature CSS, vanilla JavaScript, and locally bundled HTMX.
- Implement budget/expense CRUD, conversion preview, notices, insights,
  accessible dialogs, status/error/empty/loading states, and safe rendering.
- Add separate Release 1 MCP budget-check and grounded-guidance controls, gated
  by `/api/capabilities`, with exact safe-integer money display and stale-request
  protection.
- Add Vitest/jsdom coverage and a deterministic packaging validation.

Exit: frontend tests and packaging pass; browser checklist is prepared.

### Stage 5: Integration and CI

- Add production Dockerfiles, nginx proxying, root Compose services, persistent
  storage, health/dependency ordering, shared route/card, and model setting.
- Replace Student 4 CI with frontend/.NET tests plus direct shared-Compose
  validation, image builds, model-independent health/API smoke tests, count
  assertions, and unconditional teardown. Do not add a Student 4-only Compose or
  container lifecycle path.

Exit: local config, builds, health, seeded API, and supported route checks pass,
or any environmental blocker is recorded precisely.

### Stage 6: Evidence Reconciliation

- Reconcile README, checklists, contribution log, known issues, prompt log, and
  review record with observed results only.
- When configured models are available, use the shared two-model loop for one
  bounded genuine change and leave final Adapt to Liam.

Exit: ACT report distinguishes produced evidence from human-only pending work.

## Development Method

Each substantive edit is followed by the narrowest relevant check. A failed
check is repaired in the same slice and rerun before implementation expands.
AI may commit and push feature branches when authorised by Liam. Liam retains
PR merge, human approvals, attendance, acceptance and showcase publication.

## Release 1 Delivery

Retain the current static HTML/JavaScript/HTMX frontend and deterministic budget
backend. Add a read-only `budget.get_summary` MCP tool whose fixed callback reads
the existing dashboard endpoint, and separate grounded budgeting guidance using
shared native RAG with `feature: student-4`, validated citations, and explicit
insufficient-context abstention. Keep Ollama advice distinct, preserve database
ownership, and make no schema changes or cross-student calls.

Status checked 2026-10-02: final feature revision `c282a73` includes the
cancellation-focus fix and its successful browser replay. The current
`BCP/R1_Budget_RAG` merge preserves newer shared-service changes from main and
requires fresh combined validation. Detailed historical live results and
limitations are in the [Release 1 runbook](release-1-runbook.md) and
[live-validation record](evidence/release-1/live-validation-2026-10-02.md).

1. **Modes/capabilities - implemented and tested:** strict flags and
  `GET /api/capabilities`; disabled advice preserves fallback behavior.
2. **MCP budget check - integrated and verified:** the UI-to-backend-to-native
  MCP callback returned HTTP 200 and matched every dashboard field/category.
  Before/after dashboard, budgets and expenses were byte-identical (12/26).
3. **Student 4 RAG - integrated and verified:** five answerable live gateway
  questions returned exact cited source paragraphs; the unsupported Mars query
  abstained in the UI. Earlier freeform failures remain preserved as history.
4. **Static UI - integrated and verified:** real budget/expense create, read,
  update and confirmed delete flows were exercised and cleaned up; canceling
  delete dialogs preserved records and focus. Screenshots at 320/768/1280px
  showed no horizontal overflow. After guidance cancellation, the final browser
  replay confirmed the visible cancelled status, request abort (`net::ERR_ABORTED`),
  and focus restoration to `guidance-question`. The frontend image was rebuilt
  and its container reported healthy.
5. **CI - passed:** Linux Actions run [36947214508](https://github.com/LucLeMoenic/Advanced-Software-Development-Project/actions/runs/36947214508)
  passed at the implementation commit with 439 tests; 19 live RAG tests were
  skipped and all six AI/MCP/RAG flags were false. Windows local `All` remains
  subject to its symlink privilege limitation.
6. **Shared validation loop - records produced, not finalised:** fresh MCP/RAG
  records both passed their runtime contracts and post-loop backend/frontend
  suites passed 136/136 and 19/19. Both records have null human decisions and
  post-tests; Liam's decisions and finalisation remain pending.
7. **Release evidence - partial:** Student 4 implementation criteria 2-7 have
  substantial implementation/runtime/CI evidence. All-five-feature integration,
  final group PDF/video links, attendance, Q&A and release sign-off are not
  established. PRs #104-#108 were merged, but #105-#108 targeted feature branches;
  the complete feature still requires the final integration PR into main.

Two independent functional/rubric reviews found no current Student 4 functional
blocker. No grade, group-wide completion, PR approval, or human loop decision is implied.

## Release 2 Spec: Preview-Only What-If Budget Planner

**Task:** Student 4 Release 2, first grounded calculator slice only.
**Date:** 2026-10-23.
**Status:** READY. Calculator slice implemented and focused tests passed;
endpoints, frontend and multi-agent integration are not implemented by this slice.

### Executive Summary

Preview a complete replacement set of category limits against an existing
dashboard, preserving actual spending and returning fresh dashboard/category
records. Money and classifications remain deterministic and reuse the existing
percentage/status helpers. No AI call, persistence, database schema change,
autonomous write or new dependency is introduced.

### Context & Assumptions

- This bounded R2 authorisation extends the historical R0/R1-only scope. The
  [Release 2 brief](../../docs/Project_Specifications/Release_2_brief.md) governs
  R2; existing [requirements](requirements.md) and [risks](risk-plan.md) still
  govern money precision, database ownership and model isolation.
- Input is the complete existing category set once each, not a partial patch.
  Trim and invariant lowercase establish identity; only the six existing
  supported categories are allowed, with 1-6 source/proposal entries.
- Every proposed limit is an integer minor-unit amount in
  `1..9_007_199_254_740_991`; the proposed total has the same upper bound.
- Source planned amounts must be positive, actuals nonnegative, all monetary
  magnitudes JavaScript-safe, remaining equal planned minus actual, and category
  planned/actual sums equal dashboard totals. Negative remaining is valid.
- Preserve journey, currency, category labels/order, dashboard actual and every
  category actual. Do not modify the source, its category collection or proposals.
- Next backend slice will supply preview/start/poll/decision endpoints using the
  existing shared Multi-Agent Server and built-in protected handle. That work,
  human workflow decisions, UI, CI/cloud and full R2 acceptance remain deferred.
  Complete-set input is chosen to avoid ambiguous merge/default semantics.
- No delegation, branches, commits or pushes. Documentation/evidence for this
  four-file task is consolidated here; other feature logs remain untouched.

### File-by-File Changes

**Contract group:** [Contracts.cs](../backend/Api/Contracts.cs), modified.
Add `public sealed record WhatIfLimit(string? Category, long LimitAmountMinor)`.
Reuse `DashboardResponse`; no endpoint binding or response wrapper yet.

**Calculation group:** [DashboardCalculator.cs](../backend/Services/DashboardCalculator.cs),
modified. Add `public static DashboardResponse CalculateWhatIf(DashboardResponse original, IReadOnlyList<WhatIfLimit> proposed)`.
Use `ArgumentException` with `ParamName = "proposed"` and a clear message for
invalid proposals; use existing `DashboardDataException` for invalid source data.
Reuse `Validation.Categories`, `Percentage` and `Status` without changing `Calculate`.

    if source/null categories/count/money/category identity is invalid:
        throw DashboardDataException
    if source category sums do not match source totals:
        throw DashboardDataException
    if proposal is null, empty, over six or not the source category count:
        throw ArgumentException
    for each proposal:
        normalize category; reject null entry/name, unknown/missing identity,
            duplicate identity and nonpositive/unsafe amount
        if amount exceeds safe maximum minus accumulated proposed total:
            throw ArgumentException before addition
    build fresh category records in source order with new planned/remaining,
        existing actual and reused Percentage/Status results
    return fresh dashboard with proposed total and unchanged actual

Source amounts/count are bounded before sums (at most six safe integers, below
`long.MaxValue`); subtraction uses bounded nonnegative operands. Existing helpers
use decimal percentage arithmetic, with status based on the unrounded ratio.

**Test group:** [CalculationTests.cs](../backend/tests/CalculationTests.cs), modified.
Preserve all three baseline tests; add focused xUnit facts/theories using existing
fixtures and naming. **Spec/evidence group:** this existing feature plan, appended
only. No other files are in scope.

### Edge Cases

| Scenario | Expected Behaviour |
|---|---|
| Shuffled, padded/mixed-case complete proposal | Match by normalized identity; preserve source labels/order and actuals. |
| Null list/entry/name, empty/whitespace, missing, duplicate, unknown or absent supported category, over six | `ArgumentException`; no partial result or mutation. |
| Zero, negative, above-safe or `long` extreme limit; safe individual limits with unsafe total | `ArgumentException` before unsafe arithmetic. |
| Null/empty/duplicate/unsupported source categories; unsafe/inconsistent source money or totals | `DashboardDataException`, not overflow or null-reference exceptions. |
| Zero spend; maximum-safe proposed total/actual; negative remaining | Exact minor units and fresh result; never change source actuals. |
| 79.99%, 80%, 100%, above 100%; below-80 ratio rounding to 80% | Within, warning, warning, overspent; last case stays within. |

### Test Plan & Observed Evidence

All cases are in `CalculationTests` in the linked test file above:
- `WhatIfChangesExactLimitsWithoutMutatingSourceOrProposal`: food/transport limits
  6000/12000, unchanged actuals 8000/3000, total 18000/11000/7000 and 61.11%;
  fresh dashboard, collection and category records; source/proposal snapshots equal.
- `WhatIfSupportsAllSixExistingCategoriesWithDifferentLimits`: reversed normalized
  input, distinct limits 1-6, zero spending, exact total 21 and within-budget statuses.
- `WhatIfUsesExactThresholdsBeforePercentageRounding`: 0, 79.99, 80, 100, 100.01%
  plus 79.9999% displayed as 80%; exact remaining, percentages and classifications.
- `WhatIfRejectsInvalidOrIncompleteCategorySets` and
  `WhatIfRejectsNonpositiveOrUnsafeLimits`: invalid input rows above; correct
  exception type, parameter name and meaningful messages.
- `WhatIfRejectsProposedTotalAboveSafeIntegerLimit`,
  `WhatIfAcceptsProposedTotalAtSafeIntegerLimit` and
  `WhatIfKeepsMaximumSafeActualAndNegativeRemainingExact`: safe boundary and
  boundary-plus-one totals; maximum actual preserved under limits 1 and maximum.
- `WhatIfRejectsUnsafeOrInconsistentSourceData`: invalid category structures,
  all three monetary fields at dashboard/category level including `long` extremes,
  invalid signs/remaining, mismatched totals and unsafe aggregate sums.

Immediate post-implementation command:
`dotnet test student-4/backend/tests/Backend.Tests.csproj --filter FullyQualifiedName~CalculationTests`.
Observed: **74 total, 74 passed, 0 failed, 0 skipped**; test duration 2.2s,
build succeeded in 7.7s. This is scoped local calculator evidence, not endpoint,
full-suite, live AI, UI, CI/cloud or release sign-off evidence. Pipeline research
delegation was skipped because scope was supplied; specification, implementation
and bounded review are local. Unavailable `cw-testing`/`test-affected` skills are
replaced by existing xUnit conventions and the exact scoped gate above.

### Blockers

| # | Question | Why It Blocks | Owner |
|---|---|---|---|
