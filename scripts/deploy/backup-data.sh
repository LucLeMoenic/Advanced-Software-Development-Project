#!/usr/bin/env bash
# Consistent online backup of every SQLite database under $ASD_ROOT/data/student-N/.
#
#   bash backup-data.sh
#
# Uses SQLite's backup API, so it is safe while the services are running (a plain file copy of a live
# database can be torn). Each copy is integrity-checked, then listed in SHA256SUMS. Backups go to
# $ASD_ROOT/backups/<UTC timestamp>/ and only the newest ASD_BACKUP_KEEP (default 7) timestamped
# backups are kept. ASD_ROOT defaults to /opt/asd.
set -euo pipefail

root="${ASD_ROOT:-/opt/asd}"
keep="${ASD_BACKUP_KEEP:-7}"
fail() { echo "backup: $*" >&2; exit 1; }

[[ "$keep" =~ ^[1-9][0-9]*$ ]] || fail "ASD_BACKUP_KEEP must be a positive integer"
python="$(command -v python3 || command -v python)" || fail "python3 is required"
[[ -d "$root/data" ]] || fail "$root/data does not exist"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dest="$root/backups/$stamp"
mkdir -p "$dest"
count=0
for db in "$root"/data/student-*/*.db; do
  [[ -e "$db" ]] || continue
  student="$(basename "$(dirname "$db")")"
  mkdir -p "$dest/$student"
  "$python" - "$db" "$dest/$student/$(basename "$db")" <<'PY' || { rm -rf "$dest"; fail "backing up $db failed; the partial backup was removed"; }
import sqlite3
import sys

source = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
target = sqlite3.connect(sys.argv[2])
with target:
    source.backup(target)
result = target.execute("PRAGMA integrity_check").fetchone()[0]
target.close()
source.close()
if result != "ok":
    sys.exit(f"integrity check failed: {result}")
PY
  count=$((count + 1))
done
if [[ "$count" -eq 0 ]]; then
  rm -rf "$dest"
  fail "no databases found under $root/data/student-*/"
fi

( cd "$dest" && find . -type f -name '*.db' | sort | xargs sha256sum > SHA256SUMS )

# Keep only the newest $keep timestamped backups. Other directories (for example pre-restore-*) are left alone.
ls -1 "$root/backups" | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort | head -n -"$keep" | while read -r old; do
  rm -rf "${root:?}/backups/$old"
done
echo "backup: $count database(s) saved to $dest"
