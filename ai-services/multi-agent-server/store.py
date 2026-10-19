"""File-backed workflow history and a hash-chained audit log.

Each workflow is one JSON file; the audit log is append-only JSON Lines where
every entry carries the SHA-256 of the previous entry, so editing or removing
any past entry is detectable with verify().
"""

import hashlib
import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

WORKFLOW_ID = re.compile(r"^wf-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
GENESIS = "0" * 64
_locks = {}
_locks_guard = threading.Lock()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def data_dir():
    return Path(os.getenv("MULTI_AGENT_DATA_DIR", Path(__file__).resolve().parent / "data"))


def _lock_for(path):
    with _locks_guard:
        return _locks.setdefault(str(path), threading.Lock())


def _digest(entry):
    return hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root else data_dir()
        self.workflows = self.root / "workflows"
        self.audit_path = self.root / "audit.log.jsonl"
        self.workflows.mkdir(parents=True, exist_ok=True)
        self._lock = _lock_for(self.root)

    # -- workflows ---------------------------------------------------------
    def save(self, record):
        record["updated_at"] = now()
        target = self.workflows / f"{record['id']}.json"
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=self.workflows, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, indent=2)
            os.replace(tmp, target)

    def load(self, workflow_id):
        if not WORKFLOW_ID.match(workflow_id):
            return None
        path = self.workflows / f"{workflow_id}.json"
        with self._lock:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

    def list(self):
        with self._lock:
            records = [json.loads(p.read_text(encoding="utf-8")) for p in self.workflows.glob("wf-*.json")]
        records.sort(key=lambda r: r["created_at"], reverse=True)
        return [{k: r.get(k) for k in ("id", "feature", "task", "status", "created_at", "updated_at")}
                for r in records]

    # -- audit log ---------------------------------------------------------
    def _read_audit(self):
        if not self.audit_path.exists():
            return []
        return [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines() if line]

    def audit(self, workflow_id, actor, event, details=None):
        with self._lock:
            entries = self._read_audit()
            entry = {
                "seq": len(entries) + 1, "ts": now(), "workflow_id": workflow_id,
                "actor": actor, "event": event, "details": details or {},
                "prev_hash": entries[-1]["hash"] if entries else GENESIS,
            }
            entry["hash"] = _digest(entry)
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def audit_entries(self, workflow_id=None):
        with self._lock:
            entries = self._read_audit()
        return [e for e in entries if workflow_id is None or e["workflow_id"] == workflow_id]

    def verify(self):
        """Recompute the whole chain. Returns {"valid": bool, "entries": n, "broken_at": seq|None}."""
        with self._lock:
            entries = self._read_audit()
        previous = GENESIS
        for index, entry in enumerate(entries, start=1):
            body = {k: v for k, v in entry.items() if k != "hash"}
            if entry.get("seq") != index or entry.get("prev_hash") != previous or _digest(body) != entry.get("hash"):
                return {"valid": False, "entries": len(entries), "broken_at": index}
            previous = entry["hash"]
        return {"valid": True, "entries": len(entries), "broken_at": None}
