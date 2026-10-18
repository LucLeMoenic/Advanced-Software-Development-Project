"""Run pip-audit against requirements files, in parallel.

Used by the pre-commit ``pip-audit`` hook (which passes only the requirements
files in the commit) and runnable directly:

    python scripts/security/pip_audit_all.py                 # every requirements*.txt
    python scripts/security/pip_audit_all.py path/to/requirements.txt ...

pip-audit builds a virtualenv per file (about a minute each), so files are
audited concurrently. Exits non-zero if any file has a known-vulnerable
dependency or cannot be audited. Documented exceptions live in
``pip-audit-accepted.json``.
"""

import json
import subprocess  # noqa: S404 - fixed argv only, no shell
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "bin", "obj"}
MAX_WORKERS = 4
ACCEPTED = Path(__file__).with_name("pip-audit-accepted.json")


def accepted_ids(rel: str) -> list[str]:
    """Vulnerability IDs documented as accepted for this file (see the JSON)."""
    entry = json.loads(ACCEPTED.read_text(encoding="utf-8")).get(rel, {})
    return entry.get("ids", [])


def all_requirement_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("requirements*.txt") if not SKIP_DIRS & set(p.relative_to(ROOT).parts)
    )


def audit(path: Path) -> tuple[str, int, str]:
    rel = path.resolve().relative_to(ROOT).as_posix()
    command = [sys.executable, "-m", "pip_audit", "--requirement", str(path), "--progress-spinner", "off"]
    notes = ""
    for vuln_id in accepted_ids(rel):
        notes += f"   accepted exception (see pip-audit-accepted.json): {vuln_id}\n"
        command += ["--ignore-vuln", vuln_id]
    for attempt in (1, 2):
        result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 - argv list built from repo paths
        output = result.stdout + result.stderr
        # Retry once only for tool/infrastructure errors (e.g. the temporary venv
        # failing to upgrade pip), never for genuine vulnerability findings.
        if result.returncode != 0 and "known vulnerabilit" not in output and attempt == 1:
            continue
        break
    return rel, result.returncode, notes + output


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or all_requirement_files()
    if not paths:
        print("pip-audit: no requirements files to audit")
        return 0
    failed = []
    with ThreadPoolExecutor(max_workers=min(len(paths), MAX_WORKERS)) as pool:
        for rel, code, output in pool.map(audit, paths):
            print(f"== pip-audit {rel}\n{output.rstrip()}", flush=True)
            if code != 0:
                failed.append(rel)
    if failed:
        print("pip-audit FAILED for: " + ", ".join(failed))
        return 1
    print(f"pip-audit OK for {len(paths)} requirements file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
