# Student 5 - Pre-Commit Security Testing Report (Release 2)

Date: 22 October 2026 · Branch: `AC/student5-r2-precommit` · Plan: Chunk 4 in
[`release-2-plan.md`](../../release-2-plan.md)

## Tools and versions

| Tool | Version | How it runs |
|---|---|---|
| pre-commit | 4.7.0 | Git `pre-commit` hook, installed in the repo `.venv` |
| Ruff (`--select S`, flake8-bandit rules) | 0.17.1 | `ruff-check` hook, pre-commit-managed environment |
| detect-secrets | 1.5.0 | `detect-secrets` hook against `.secrets.baseline` |
| pip-audit | 2.10.1 | Local hook `scripts/security/pip_audit_all.py`, run by the `python` on `PATH` (see finding 4) |

The configuration is shared and unchanged by this chunk: `.pre-commit-config.yaml`,
`pyproject.toml` (Ruff rules and per-file ignores), `.secrets.baseline` and
`scripts/security/pip-audit-accepted.json`. Setup is in `scripts/security/README.md`.

## Scope

- **Ruff and detect-secrets:** every tracked Student 5 file, `git ls-files student-5`
  (111 files). Ruff checks the Python files among them. detect-secrets checks all of
  them, including the HTMX frontend, nginx config, Dockerfiles, docs and evidence.
- **pip-audit:** `student-5/backend/requirements.txt` and
  `student-5/database/requirements.txt`. The frontend is nginx with no Python
  dependencies.

## Results

| Scan | Raw result | Action | Hook result |
|---|---|---|---|
| Ruff `S` rules | 371 findings with the per-file ignores off: 369 `S101` (all in `tests/`), 2 `S104`. With inline `noqa` ignored (per-file ignores on), 5 `S608` in `database/app.py`. | No real finding. All are accepted with reasons below. Only change: reasons added to three bare `# noqa: S608` comments. | **Passed** |
| detect-secrets | 4 candidates without the baseline: 3 hex strings, 1 base64 string. | Each checked by hand; none is a secret. All four were already in the baseline as `is_secret: false`, so the baseline is unchanged. | **Passed** |
| pip-audit | Database (as on `main`, exception off): 2 entries for `PYSEC-2026-1845`, pytest 8.4.2, fix 9.0.3. Backend: clean, but its `pytest>=8.0` floor allowed the vulnerable 8.x. | Both pins now `pytest>=9.0.3,<10.0`. Student 5 exception removed from `pip-audit-accepted.json`. | **Passed**, 0 vulnerabilities and no exceptions applied |
| Blocked commit (negative test) | Throwaway file with AWS's documented example key ID and `subprocess.call(..., shell=True)` | Dry run first: `pre-commit run --files` on the untracked file failed Ruff (`S602`) and detect-secrets (AWS Access Key), exit 1. Then staged and a real `git commit` attempted; file unstaged and deleted afterwards. | Dry run: **Failed** as intended. Real commit: see `04` |

Regression after the pin bumps: under pytest 9.1.1, the Student 5 database tests
(26) and backend tests (199) pass. The combined install
`-r student-5/database/requirements.txt -r ai-services/mcp-server/requirements.txt -r ai-services/rag-server/requirements.txt`
used to fail with `ResolutionImpossible` (`pytest<9.0` against `pytest==9.0.3`). It
now resolves to pytest 9.0.3 and Flask 3.1.3.

## Findings and how each was resolved

1. **`PYSEC-2026-1845` in pytest (database), resolved.** The database pin capped
   pytest below 9, which is below the fixed version and clashes with the shared
   MCP/RAG `pytest==9.0.3`. CI never failed, because `scripts/test/student-5.ps1`
   installs each requirements file separately and pip just upgraded pytest.
   The new range `>=9.0.3,<10.0` is used for both the database and the backend.
   The backend's old `>=8.0` floor was clean only because the audit resolves the
   newest 9.x. pytest is a test
   dependency only, but it is installed in the database image by `RUN pip install -r
   requirements.txt`, so the fix also reaches the container. `pip_audit_all.py` now
   enforces the database file with no exception.
2. **Ruff `S101` (369, tests only), accepted.** pytest relies on bare `assert`.
   For Student 5 files, `pyproject.toml` ignores `S101` only under `**/tests/**`
   and in `conftest.py`. Those globs also ignore `S105`/`S106` (dummy test tokens),
   but the scan with ignores off found none in Student 5.
   With the ignores off, every one of the 369 is in `backend/tests/` or
   `database/tests/`, so no production `assert` is hidden.
3. **Ruff `S104` (2), accepted.** `backend/app.py` and `database/app.py` bind
   `0.0.0.0` inside their containers so nginx and the other containers can reach
   them. Host exposure is set by the `docker-compose.yml` port mappings (5205,
   5305). `pyproject.toml` scopes this ignore to `student-*/backend/app.py` and
   `student-*/database/app.py`.
4. **Ruff `S608` (5, inline `noqa`), accepted after checking the code.** The generic
   CRUD helpers in `database/app.py` build SQL with f-strings:
   - every `table` value is a string literal passed by a route handler
     (`"destinations"`, `"weather_notes"`, `"transit_options"`);
   - column names come from the constant `WRITABLE_FIELDS[table]`, never from
     payload keys;
   - every value, including `id`, is a bound `?` parameter.

   No request data reaches the SQL text. Three of the five `noqa` comments had no
   reason. All five now say why, with no change to the code.
5. **detect-secrets candidates (4), not secrets.**
   - `docs/evidence/agentic-loop-run-final-record.json` lines 22, 24 and 25 are
     SHA-256 hashes in the run record's `evidenceHashes` block. They identify the
     context file and prompts the agentic loop reviewed.
   - `frontend/index.html` line 44 is the `sha384-` subresource-integrity hash on
     the HTMX `<script>` tag. It is a public value the browser uses to check the
     CDN file.

   All four were already audited as `is_secret: false`, so the baseline is unchanged.
6. **The pip-audit hook depends on `PATH`, documented and flagged.** The hook is
   `language: system` with `entry: python ...`. The git hook starts pre-commit with
   the repo `.venv`, but this hook still uses whatever `python` is first on `PATH`.
   On this machine an unactivated Git Bash resolves the WindowsApps Python 3.13,
   which has no `pip_audit`. A commit that changes a requirements file would then
   fail. It would be blocked, not let through.
   - Student 5 workaround: install pip-audit in the repo `.venv` and commit with
     the venv activated (`source .venv/Scripts/activate`).
   - The shared hook is not changed here. This is noted for the owner of
     `.pre-commit-config.yaml` and `scripts/security/README.md`.

## Evidence files (`precommit/`)

| File | Shows |
|---|---|
| `01-ruff.txt` | Ruff hook over all 111 Student 5 files (Passed), plus the same Ruff with per-file ignores off (371) and with `noqa` ignored (5 `S608`) |
| `02-detect-secrets.txt` | detect-secrets hook (Passed), plus a scan without the baseline (4 candidates, values omitted) and their baseline status |
| `03-pip-audit.txt` | Database audit before the fix (`PYSEC-2026-1845`), the install conflict, the diff, the hook after the fix (both files clean), the conflict resolved, database tests 26 passed |
| `04-blocked-commit.txt` | A real `git commit` of a deliberately insecure file, rejected by the hooks (captured by hand, fake key redacted). The Chunk 4 commits themselves also run all three hooks, including pip-audit, because they change both requirements files. |

## How to reproduce

From the repo root in Git Bash, with the repo `.venv` activated:

```bash
source .venv/Scripts/activate
python -m pip install pip-audit==2.10.1          # once; into the repo .venv only
python -m pre_commit run ruff-check     --verbose --files $(git ls-files student-5)
python -m pre_commit run detect-secrets --verbose --files $(git ls-files student-5)
python -m pre_commit run pip-audit      --verbose --files $(git ls-files student-5)
python -m pip_audit --requirement student-5/database/requirements.txt --progress-spinner off
(cd student-5/database && python -m pytest -q)
```

## Limits

- pip-audit checks declared Python dependencies only. It does not cover the
  `python:3.11-slim` or nginx base images, and it needs network access to PyPI.
- pip-audit audits what each requirements range resolves to today, which is the
  newest allowed version. A range can pass while still allowing an older,
  vulnerable version, which is why both Student 5 floors were raised.
- Ruff `S` is static pattern matching. It does not replace the endpoint tests or a
  code review.
