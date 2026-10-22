#!/usr/bin/env bash
# Restore the SQLite databases from a backup made by backup-data.sh.
#
#   bash restore-data.sh /opt/asd/backups/<timestamp> --yes
#
# Restoring replaces live data, so --yes is required. Order of operations: verify the backup's checksums
# and integrity, snapshot the current data to $ASD_ROOT/backups/pre-restore-<timestamp>/, stop the services,
# copy the databases back (removing stale -wal/-shm files), then start the current release again.
# ASD_ROOT defaults to /opt/asd.
set -euo pipefail

umask 077  # the pre-restore snapshot holds a full copy of live data
root="${ASD_ROOT:-/opt/asd}"
fail() { echo "restore: $*" >&2; exit 1; }

backup_arg="${1:-}"
confirm="${2:-}"
[[ -n "$backup_arg" ]] || fail "usage: restore-data.sh <backup-directory> --yes"
[[ "$confirm" == "--yes" ]] || fail "restoring replaces live data; re-run with --yes to confirm"
[[ -d "$backup_arg" ]] || fail "backup directory not found: $backup_arg"
backup="$(cd "$backup_arg" && pwd)"
[[ "$backup" == "$root/backups/"* ]] || fail "the backup must be inside $root/backups"
[[ -f "$backup/SHA256SUMS" ]] || fail "$backup has no SHA256SUMS; it is not a complete backup"
[[ -f "$root/current/compose.json" ]] || fail "no current release at $root/current to restart"
python="$(command -v python3 || command -v python)" || fail "python3 is required"

( cd "$backup" && sha256sum --check --quiet SHA256SUMS ) || fail "checksum mismatch: the backup is damaged; nothing was changed"
while read -r _ file; do
  "$python" - "$backup/${file#./}" <<'PY' || fail "integrity check failed for ${file#./}; nothing was changed"
import sqlite3
import sys

connection = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
result = connection.execute("PRAGMA integrity_check").fetchone()[0]
connection.close()
sys.exit(0 if result == "ok" else 1)
PY
done < "$backup/SHA256SUMS"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
safety="$root/backups/pre-restore-$stamp"
mkdir -p "$safety"
cp -a "$root/data/." "$safety/"
# cp -a copies the source directory's own mode onto $safety, overriding the umask, so make the snapshot private explicitly.
chmod -R go-rwx "$safety"
echo "restore: current data saved to $safety"

compose=(docker compose --project-name asd-cloud --file "$root/current/compose.json")
"${compose[@]}" stop
while read -r _ file; do
  relative="${file#./}"
  target="$root/data/$relative"
  mkdir -p "$(dirname "$target")"
  cp -f "$backup/$relative" "$target"
  rm -f "$target-wal" "$target-shm"
done < "$backup/SHA256SUMS"
"${compose[@]}" up --detach --no-build --wait --wait-timeout 240
echo "restore: databases restored from $backup. Run the public HTTPS verification (smoke_cloud.py) before declaring success."
