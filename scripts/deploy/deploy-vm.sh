#!/usr/bin/env bash
set -euo pipefail
sha="${1:?Provide the validated 40-character revision}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid revision" >&2; exit 1; }
upload="$HOME/asd-upload/$sha"
release="/opt/asd/releases/$sha"
cd "$upload"
sha256sum --check SHA256SUMS
[[ "$(cat revision.txt)" == "$sha" ]] || { echo "Revision mismatch" >&2; exit 1; }
test -d /opt/asd/releases && test -w /opt/asd/releases && test -w /opt/asd/data && test -w /opt/asd || {
  echo "The VM owner must provision /opt/asd/releases and /opt/asd/data for this deployment account." >&2; exit 1;
}
mkdir -p "$release"
for file in compose.json Caddyfile revision.txt smoke_cloud.py; do
  cp "$file" "$release/$file"
done
for student in 1 2 3 4 5; do mkdir -p "/opt/asd/data/student-$student"; done
if [[ ! -e /opt/asd/data/student-1/accommodation.db ]]; then
  cp accommodation.db /opt/asd/data/student-1/accommodation.db
fi
docker image load --input images.tar
docker compose --project-name asd-cloud --file "$release/compose.json" config --quiet
docker compose --project-name asd-cloud --file "$release/compose.json" up --detach --no-build --wait --wait-timeout 240
echo "Services started for $sha. Run public HTTPS verification before declaring release success."
if [[ -L /opt/asd/current ]]; then readlink /opt/asd/current > "$release/previous-release.txt"; fi
ln -sfn "$release" /opt/asd/current
