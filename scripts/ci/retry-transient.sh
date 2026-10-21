#!/usr/bin/env bash
# Run a command and retry it ONLY when it failed for a transient registry or network reason.
#
#   scripts/ci/retry-transient.sh <attempts> <base-delay-seconds> <command> [args...]
#
# Docker Hub and other registries occasionally answer a build with a 500 or drop the connection
# ("unexpected status ... 500 Internal Server Error", "failed to authorize ... EOF"). That is not
# a code problem and a re-run fixes it, so it is retried with a growing delay. Any other failure,
# for example a real Dockerfile or compile error, fails at once so it is never hidden by a retry.
set -uo pipefail

attempts="${1:?attempts}"
delay="${2:?base delay in seconds}"
shift 2
[[ $# -gt 0 ]] || { echo "retry-transient: no command given" >&2; exit 2; }
[[ "$attempts" =~ ^[1-9][0-9]*$ && "$delay" =~ ^[0-9]+$ ]] || { echo "retry-transient: attempts must be >= 1 and delay a number" >&2; exit 2; }

transient='registry-1\.docker\.io|failed to authorize|failed to fetch (an )?oauth token|TLS handshake timeout|i/o timeout|connection reset by peer|unexpected EOF|error reading from server: EOF|Service Unavailable|Bad Gateway|Gateway Time-?out|toomanyrequests|500 Internal Server Error|502 |503 |504 |no such host|temporary failure in name resolution|net/http: request canceled'

log="$(mktemp)"
trap 'rm -f "$log"' EXIT

attempt=1
while true; do
  "$@" 2>&1 | tee "$log"
  status="${PIPESTATUS[0]}"
  if [[ "$status" -eq 0 ]]; then
    exit 0
  fi
  if ! grep -Eqi "$transient" "$log"; then
    echo "retry-transient: attempt $attempt failed and the output does not look transient; not retrying." >&2
    exit "$status"
  fi
  if [[ "$attempt" -ge "$attempts" ]]; then
    echo "retry-transient: still failing after $attempts attempts with a transient-looking error." >&2
    exit "$status"
  fi
  wait_for=$((delay * attempt))
  echo "retry-transient: attempt $attempt of $attempts failed with a transient-looking error; retrying in ${wait_for}s." >&2
  sleep "$wait_for"
  attempt=$((attempt + 1))
done
