#!/usr/bin/env bash
# Roll the VM back to the release that deploy-vm.sh recorded as "previous".
#
#   bash rollback-vm.sh
#
# Layout written by deploy-vm.sh:
#   $ASD_ROOT/releases/<40-hex-sha>/   compose.json, revision.txt, previous-release.txt, ...
#   $ASD_ROOT/current                  symlink to the live release
#   $ASD_ROOT/data/student-N/          SQLite data, bind-mounted by the services (never touched here)
# ASD_ROOT defaults to /opt/asd. Rolling back code does not roll back data: if a release changed a
# database schema, restore a backup with restore-data.sh as well.
set -euo pipefail

root="${ASD_ROOT:-/opt/asd}"
fail() { echo "rollback: $*" >&2; exit 1; }
valid_release() { [[ "$1" == "$root/releases/"* && "${1##*/}" =~ ^[0-9a-f]{40}$ ]]; }

[[ -L "$root/current" ]] || fail "no current release is installed ($root/current is not a symlink)"
current="$(readlink "$root/current")"
valid_release "$current" || fail "unexpected current release path: $current"

previous_file="$current/previous-release.txt"
[[ -f "$previous_file" ]] || fail "release ${current##*/} has no recorded previous release; nothing to roll back to"
previous="$(tr -d '\r\n' < "$previous_file")"
valid_release "$previous" || fail "the recorded previous release is not under $root/releases: $previous"
[[ "$previous" != "$current" ]] || fail "the previous release is the current release (a redeploy of the same revision); nothing to roll back to"
[[ -f "$previous/compose.json" && -f "$previous/revision.txt" ]] || fail "previous release ${previous##*/} is missing its files"
[[ "$(tr -d '\r\n' < "$previous/revision.txt")" == "${previous##*/}" ]] || fail "previous release revision does not match its directory"

echo "rollback: ${current##*/} -> ${previous##*/}"
docker compose --project-name asd-cloud --file "$previous/compose.json" config --quiet
if ! docker compose --project-name asd-cloud --file "$previous/compose.json" up --detach --no-build --wait --wait-timeout 240; then
  fail "starting ${previous##*/} failed (its images may have been pruned); the current symlink was NOT changed, inspect the containers before retrying"
fi
printf '%s\n' "$current" > "$previous/rolled-back-from.txt"
ln -sfn "$previous" "$root/current"
echo "rollback: now serving ${previous##*/}. Run the public HTTPS verification (smoke_cloud.py) before declaring success."
