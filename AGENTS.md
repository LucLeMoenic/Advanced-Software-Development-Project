# Workspace Instructions

These instructions apply to all student features and shared services. Use the applicable release brief, the ASD project specifications, and the documentation for the feature being worked on as the source of truth.

## Read Before Working

- Identify the student feature or shared service in scope before making changes.
- Read its context, requirements, current feature/release plan, and relevant risk documentation where available. Student documentation lives under `student-<n>/docs/`; follow each feature's existing filenames.
- Read the applicable release brief and project specifications under `docs/Project_Specifications/` when the task touches marks, report evidence, integration, or shared app structure.
- For shared services, read their own documentation and the affected feature contracts.

## Write When Needed

- Record meaningful AI code/infrastructure work and validation in the owning feature's existing prompt log.
- Record code reviews in the owning feature's existing review record.
- For shared work, use the contributing feature's logs or an existing shared log; do not duplicate entries in unrelated student folders.
- Keep shared runtime prompts only under `ai-services/agentic-loop/prompts/`; feature documentation must link to them instead of copying them.
- Put feature-specific reusable, non-runtime prompts in that feature's existing prompt library.
- Keep report-facing evidence aligned with the applicable release's marking criteria and integration requirements.

## Working Rules

- Keep changes small and focused on the current step.
- Prefer the feature docs over memory when deciding scope or sequence.
- Prefer the applicable release brief and project specifications over feature-specific assumptions when they conflict; flag discrepancies between authoritative documents.
- Reuse existing shared functionality rather than rebuilding it for each student.
- Do not change another student's feature without explicit scope or approval. Document owner dependencies instead.
- If the task involves implementation, check the relevant docs before editing files.
- If the task involves review, check the current code and log the review outcome.
- Do not add entries to the logs for purely conversational questions.

## Git

- AI assistants may create commits and push feature branches for this repository.
- Commit on a feature branch, never directly on `main`. Follow the user's requested branch name or the contributing student's convention; no single prefix is required.
- Use meaningful Conventional Commit messages and split independent changes into focused commits when requested.
- Never push to `main`, force-push, rewrite pushed history, delete branches, or merge pull requests. The user reviews and merges manually.
- Run relevant tests before each code/infrastructure commit and record results in the owning feature's log. Documentation-only commits need no application tests unless documentation checks exist.
