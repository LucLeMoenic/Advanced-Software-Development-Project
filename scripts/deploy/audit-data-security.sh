#!/usr/bin/env bash
# Read-only audit of how application data, secrets and credentials are protected on the VM
# (Release 2 cloud security bonus, B6).
#
#   bash audit-data-security.sh
#
# Checks (PASS or FAIL; the script exits 1 if any FAIL):
#   perms:data / perms:backups  nothing under $ASD_ROOT/data or $ASD_ROOT/backups is accessible to other users
#   env:secrets                 no running container has a secret-looking variable (KEY, TOKEN, SECRET, PASSWORD, ...)
#                               set to a non-empty value. Only variable NAMES are printed, never values.
#   compose:secrets             the current release's compose.json has an empty LITEAPI_KEY
#   files:credentials           no .env file, private key or credential file is left under $ASD_ROOT
# It also prints INFO for which *_ENABLED flags are on, and MANUAL for what a script cannot know: whether the platform
# encrypts the disk at rest (capture that evidence from the cloud provider; see docs/release-2/cloud-validation-runbook.md).
# It changes nothing. ASD_ROOT defaults to /opt/asd.
set -uo pipefail

root="${ASD_ROOT:-/opt/asd}"
failures=0
pass() { printf 'PASS    %-18s %s\n' "$1" "$2"; }
fail() { printf 'FAIL    %-18s %s\n' "$1" "$2"; failures=$((failures + 1)); }
info() { printf 'INFO    %-18s %s\n' "$1" "$2"; }
manual() { printf 'MANUAL  %-18s %s\n' "$1" "$2"; }

# 1. Stored data and backups must not be readable, writable or searchable by other users.
for area in data backups; do
  if [[ ! -d "$root/$area" ]]; then
    manual "perms:$area" "$root/$area does not exist yet"
    continue
  fi
  exposed="$(find "$root/$area" -perm /o+rwx 2>/dev/null | head -3 | tr '\n' ' ')"
  if [[ -z "$exposed" ]]; then
    pass "perms:$area" "nothing under $root/$area is accessible to other users"
  else
    fail "perms:$area" "accessible to other users, for example: $exposed (fix: chmod -R o-rwx $root/$area)"
  fi
done

# 2. No running container should carry a secret in its environment. Names only: never print a value.
secret_names='KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE'  # pragma: allowlist secret  (variable NAMES to look for, not a secret)
ids="$(docker ps -q 2>/dev/null || true)"
if [[ -z "$ids" ]]; then
  manual "env:secrets" "no running containers to inspect"
else
  # shellcheck disable=SC2086
  leaked="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $ids 2>/dev/null \
    | grep -Ei "^[A-Za-z0-9_]*(${secret_names})[A-Za-z0-9_]*=." | sed 's/=.*//' | sort -u | tr '\n' ' ')"
  if [[ -z "$leaked" ]]; then
    pass "env:secrets" "no container has a secret-looking variable with a value"
  else
    fail "env:secrets" "non-empty secret-looking variables in container environments: $leaked(values not shown)"
  fi
fi

# 3. The release bundle must not carry the sandbox API key, and report which AI flags are on.
compose="$root/current/compose.json"
if [[ ! -f "$compose" ]]; then
  fail "compose:secrets" "no current release at $compose to audit"
else
  python="$(command -v python3 || command -v python)" || { fail "compose:secrets" "python3 is required"; python=""; }  # pragma: allowlist secret  (an empty python path, not a secret)
  if [[ -n "$python" ]]; then
    report="$("$python" - "$compose" <<'PY'
import json
import sys

services = json.load(open(sys.argv[1], encoding="utf-8"))["services"]
keys, flags = [], set()
for name, service in services.items():
    environment = service.get("environment", {}) or {}
    if environment.get("LITEAPI_KEY"):
        keys.append(name)
    flags.update(f"{k}={v}" for k, v in environment.items() if k.endswith("_ENABLED") and str(v).lower() == "true")
print("KEYS " + ",".join(sorted(keys)))
print("FLAGS " + ",".join(sorted(flags)))
PY
)"
    keys="$(sed -n 's/^KEYS //p' <<< "$report")"
    flags="$(sed -n 's/^FLAGS //p' <<< "$report")"
    if [[ -z "$keys" ]]; then
      pass "compose:secrets" "LITEAPI_KEY is empty in every service of the current release"
    else
      fail "compose:secrets" "LITEAPI_KEY is set for: $keys"
    fi
    info "compose:flags" "${flags:-every *_ENABLED flag is false (cloud baseline)}"
  fi
fi

# 4. No credential material should be left lying under the application root.
found="$(find "$root" -type f \( -name '.env' -o -name '.env.*' -o -name 'id_rsa*' -o -name 'id_ed25519*' -o -name '*.pem' -o -name '*.key' -o -name 'credentials*' \) 2>/dev/null | head -5 | tr '\n' ' ')"
if [[ -z "$found" ]]; then
  pass "files:credentials" "no .env, private key or credential file under $root"
else
  fail "files:credentials" "credential-like files under $root: $found"
fi

manual "disk:encryption" "capture the provider's evidence that the VM's disk is encrypted at rest (runbook, section 4)"

if [[ "$failures" -gt 0 ]]; then
  echo "audit: $failures check(s) failed" >&2
  exit 1
fi
echo "audit: all automated checks passed"
