# Student 2 Release 2 Plan

Follow the [Release 2 brief](../../docs/Project_Specifications/Release_2_brief.md)
and [project specifications](../../docs/Project_Specifications/Project_Specifications.md).
Retain Release 0/1 functionality. The integrated group app, not an isolated
Student 2 service, is assessed.

## Required work and ownership

| Requirement | Existing work to reuse | Student 2 / shared change |
| --- | --- | --- |
| Planner -> Worker -> Reviewer -> human decision through terminal and UI | PR #112's shared native Multi-Agent Server, CLI, store and audit | Connect Student 2 backend and UI; do not build another agent system. |
| Two backend endpoint tests in assigned CI | Existing pytest suites and Student 2 workflow | Explicit create-trip and update-trip HTTP tests with retained results. |
| Pre-commit scans | Existing Ruff, detect-secrets and pip-audit hooks | Run them; record scope, exceptions and real results. |
| Three development-loop report review modes | Existing two-model loop, bounded context and human finalisation | Add mode-specific criteria; use ordinary report/evidence context files. |
| Integrated cloud deployment after CI | Existing full-group Compose application | Shared deployment scripts/workflow; all four AI modes off, persistent databases and core CRUD working. |
| Report, reviews and showcase evidence | Existing feature docs and group report | Supply actual local/cloud/CI/workflow results, not inferred completion. |

## Minimal feature

Add **Plan review** alongside Edit and Advice. Send a saved itinerary to the
existing server, show all three agent outputs, and record approve, correct,
partial-acceptance or reject. This UI is an implementation choice, not prescribed
by the brief. Decisions accept recommendations; they never edit the trip.
Existing manual editing and signed MCP preview/confirmation remain unchanged.

The backend reads evidence through the database API, excludes traveller identity,
bounds the payload, checks the returned feature/trip/record, and rejects decisions
against changed snapshots. Reuse the shared workflow store; add no database table,
agent runtime, autonomous editing or external travel provider.

## Delivery sequence

1. Implement and test the Student 2 create/poll/decision integration and UI.
2. Add endpoint-test artifacts and run existing security hooks.
3. Add the three shared review modes using existing context and finalisation.
4. Prepare one integrated Linux VM deployment path usable on Azure or AWS.
   Platform, host, access and budget still require team approval; no resources
   are provisioned by these changes.
5. Demonstrate terminal and integrated UI workflows with genuine human decisions,
   pushed CI, cloud CRUD and finalised report reviews. Supply the group report
   and showcase contribution.

Students 1, 3 and 5 must implement and test their own AI-off guards. Their
application/test changes are excluded from this contribution at the user's
request. Setting cloud environment flags alone does not implement those guards;
group cloud acceptance depends on the owners delivering them.

## Acceptance, not assumptions

Source implementation and local tests do not certify release acceptance.
The [runbook](release-2-runbook.md) is the single source for commands, results and
remaining gates. Container-to-native networking, human review, remote CI and a
real Azure/AWS deployment must be demonstrated, not replaced by mocks.

The release-specific brief says **25 October 2026, 11:59 PM AEST**; the general
specification lists **18 October**. Confirm Canvas/tutor guidance.
