# Workspace Instructions

This repository uses the Release 0 brief, the ASD project specifications, and the feature docs in `student-1/docs/` as the source of truth for the AI Accommodation Recommender work.

## Read Before Working

- Read `student-1/docs/context.md` first.
- Read `student-1/docs/requirements.md` before implementing or changing behavior.
- Read `student-1/docs/feature-plan.md` before starting a new step.
- Read `student-1/docs/risk-plan.md` before any risky integration or external-service change.
- Read the current Release 0 brief and project specifications when the task touches marks, report evidence, integration, or shared app structure.

## Write When Needed

- Update `student-1/docs/prompt-log.md` whenever AI meaningfully writes or edits code or infrastructure.
- Update `student-1/docs/review-record.md` whenever AI reviews existing work.
- Keep shared runtime prompts only under `ai-services/agentic-loop/prompts/`; feature documentation must link to them instead of copying them.
- Add only feature-specific reusable prompts that are not runtime prompts to `student-1/docs/prompt-library/`.
- Keep any report-facing evidence notes aligned with the Release 0 marking criteria and integration requirements.

## Working Rules

- Keep changes small and focused on the current step.
- Prefer the feature docs over memory when deciding scope or sequence.
- Prefer the Release 0 brief and project specifications over feature-specific assumptions when they conflict.
- If the task involves implementation, check the relevant docs before editing files.
- If the task involves review, check the current code and log the review outcome.
- Do not add entries to the logs for purely conversational questions.
- Copilot must never create Git commits or push changes for this repository. The user alone performs `git commit` and `git push` manually.
