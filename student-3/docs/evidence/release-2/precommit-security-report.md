# Student 3 — Pre-Commit Security Testing Report (Release 2)

Date: 2026-10-18 · Branch: `KSS/R2_Pre_Commit_Security` · Tools: ruff 0.17.1, detect-secrets 1.5.0, pip-audit 2.10.1, pre-commit 4.7.0

## What runs on commit

`.pre-commit-config.yaml` (repo root) runs three scans on every `git commit`: Ruff security rules (`--select S`), detect-secrets against `.secrets.baseline`, and pip-audit over the `requirements*.txt` files in the commit. pip-audit builds a virtualenv per file (about a minute), so it is scoped to changed requirements files on commit; `pre-commit run --all-files` audits all eight, four at a time (about 4–5 minutes). Setup is in `scripts/security/README.md`.

## Results

| Scan | Result on main (before) | Action | Result after |
|---|---|---|---|
| Ruff `S` rules | 896 raw findings: 888 `S101` test asserts, 2 `S105` test token fixtures, 6 `S104` container binds | Config in `pyproject.toml`: test asserts/fixtures ignored; `0.0.0.0` bind ignored for the five Flask `app.py` services because Docker/nginx must reach them and host exposure is set by Compose port mappings. No production code changed. | Pass |
| detect-secrets | 49 candidates in 15 files | Each inspected: SHA-256 hashes in loop records and evidence JSON, HTMX subresource-integrity hashes, and fake credential strings in `AgenticLoopTests.cs` that exist to test credential rejection. No real secret. All marked `is_secret: false` in the baseline. | Pass |
| pip-audit (Student 3) | 18 known vulnerabilities (backend 16 in flask, flask-cors, requests, pytest; database 2 in flask) | Bumped `flask 3.1.3`, `flask-cors 6.0.0`, `requests 2.33.0`, `pytest 9.0.3` in `student-3/*/requirements.txt`. Same bumps in `ai-services/mcp-server` and `rag-server` (both audited clean). | 0 vulnerabilities |
| pip-audit (other owners) | Student 2 backend/database and Student 5 database: flask, requests, pytest | Not my files. Recorded as owner-tagged exceptions in `scripts/security/pip-audit-accepted.json` with fix versions, so the group is not blocked. | Pass with 3 documented exceptions |

Regression after dependency bumps: `student-3` pytest 64/64, `ai-services/mcp-server` 166/166, `ai-services/rag-server` 123 passed, 28 skipped.

Note: `flask-cors` moved 4.0.1 → 6.0.0 (major); the existing CORS tests pass, but check browser behaviour in the Chunk 9 local regression.

## Negative test (the hooks really block)

A deliberately insecure file (`subprocess.call(shell=True)`, `eval`, hardcoded AWS key and password) failed Ruff (S105, S602, S307) and detect-secrets (AWS Access Key, Secret Keyword), exit code 1. File was deleted afterwards.

## Evidence files (`student-3/docs/evidence/release-2/precommit/`)

| File | Shows |
|---|---|
| `01-pip-audit-before-remediation.txt` | Student 3 pins as on `origin/main`, 18 findings |
| `02-pip-audit-after-remediation.txt` | Diff of pins, clean audit, pytest result |
| `03-precommit-all-files-pass.txt` | Full `pre-commit run --all-files`, all three hooks pass |
| `04-precommit-blocks-insecure-file.txt` | Hooks failing on the insecure file |
| `05-git-commit-hooks-fire.txt` | **TODO:** capture of the real `git commit` firing the hooks |

## Limits

Ruff and pip-audit cover Python only. Student 1 and 4 .NET code needs the equivalent noted in `scripts/security/README.md`. pip-audit needs network access to PyPI.
