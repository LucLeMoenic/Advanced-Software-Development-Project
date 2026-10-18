# Local Pre-Commit Security Scans (Release 2)

Three scans run on every `git commit` via `.pre-commit-config.yaml`:

| Scan | Hook | Config |
|---|---|---|
| Ruff security rules (flake8-bandit `S`) | `ruff-check --select S` | `pyproject.toml` (documented per-file ignores) |
| detect-secrets | `detect-secrets --baseline .secrets.baseline` | `.secrets.baseline` (every entry audited, `is_secret: false`) |
| pip-audit (requirements files in the commit; all files with `--all-files`) | `scripts/security/pip_audit_all.py` | `pip-audit-accepted.json` (documented, owner-tagged exceptions) |

## Setup (once per clone)

```bash
pip install pre-commit ruff detect-secrets pip-audit
pre-commit install
pre-commit run --all-files   # optional full run
```

If a command is not on PATH on Windows, use `python -m pre_commit ...`.

## Notes

- Python only. The Student 1 and Student 4 backends are .NET, where Ruff and
  pip-audit do not apply. Their equivalent is `dotnet list <project> package --vulnerable
  --include-transitive` (pip-audit's counterpart) and the .NET security analyzers.
- A detect-secrets finding must be fixed or audited into the baseline, never bypassed
  with `--no-verify`.
- An entry in `pip-audit-accepted.json` is a visible exception, not a fix. Remove it when
  the pin is bumped.
