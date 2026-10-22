#!/usr/bin/env bash
set -euo pipefail
sha="${1:?Provide the validated 40-character revision}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid revision" >&2; exit 1; }
root="${ASD_ROOT:-/opt/asd}"
upload="$HOME/asd-upload/$sha"
cd "$upload"
sha256sum --check SHA256SUMS
[[ "$(cat revision.txt)" == "$sha" ]] || { echo "Revision mismatch" >&2; exit 1; }
components="$(cat ai-services.txt)"
release="$root/releases/$sha"
if [[ -n "$components" ]]; then
  release="$release-ai"
  [[ -s gateway-auth.caddy ]] || { echo "AI deployment requires the private gateway authentication file." >&2; exit 1; }
fi
test -d "$root/releases" && test -w "$root/releases" && test -w "$root/data" && test -w "$root" || {
  echo "The VM owner must provision /opt/asd/releases and /opt/asd/data for this deployment account." >&2; exit 1;
}
mkdir -p "$release"
for file in compose.json Caddyfile revision.txt smoke_cloud.py smoke_cloud_ai.py cloud_auth.py pull-models-vm.sh ai-services.txt vm-pull-images.txt; do
  cp "$file" "$release/$file"
done
if [[ -n "$components" ]]; then
  install -m 600 gateway-auth.caddy "$release/gateway-auth.caddy"
  rm -f "$upload/gateway-auth.caddy"
fi
for student in 1 2 3 4 5; do mkdir -p "$root/data/student-$student"; done
if [[ ! -e "$root/data/student-1/accommodation.db" ]]; then
  cp accommodation.db "$root/data/student-1/accommodation.db"
fi
docker image load --input images.tar
docker compose --project-name asd-cloud --file "$release/compose.json" config --quiet
while IFS= read -r image; do
  if [[ -n "$image" ]]; then docker pull "$image"; fi
done < "$release/vm-pull-images.txt"
docker compose --project-name asd-cloud --file "$release/compose.json" up --detach --no-build --remove-orphans --wait --wait-timeout 240
case ",$components," in
  *,ai,*|*,rag,*|*,multi-agent,*)
    ASD_ROOT="$root" ASD_COMPOSE_FILE="$release/compose.json" bash "$release/pull-models-vm.sh"
    ;;
esac
docker compose --project-name asd-cloud --file "$release/compose.json" up --detach --no-deps --force-recreate tls-gateway
echo "Services started for $sha. Run public HTTPS verification before declaring release success."
if [[ -L "$root/current" && "$(readlink "$root/current")" != "$release" ]]; then
  readlink "$root/current" > "$release/previous-release.txt"
fi
ln -sfn "$release" "$root/current"
