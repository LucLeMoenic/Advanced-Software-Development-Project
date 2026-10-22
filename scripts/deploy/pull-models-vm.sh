#!/usr/bin/env bash
# Pull the Ollama model(s) into the cloud AI profile's ollama container (bonus B1, B3, B4).
#
#   bash pull-models-vm.sh [model ...]        # default: llama3.2:3b, the one model every consumer uses
#
# Ollama starts with no models, and a 3B model is about 2 GB, far longer than the deployment's 240 s start-up wait, so this runs
# after Compose starts inside deploy-vm.sh. It verifies each model is listed and returns a nonempty warm-up response.
# ASD_ROOT defaults to /opt/asd.
# deploy-vm.sh supplies ASD_COMPOSE_FILE to provision the new release before changing current.
set -euo pipefail

root="${ASD_ROOT:-/opt/asd}"
fail() { echo "pull-models: $*" >&2; exit 1; }

models=("$@")
[[ ${#models[@]} -gt 0 ]] || models=(llama3.2:3b)
for model in "${models[@]}"; do
  [[ "$model" =~ ^[a-z0-9][a-z0-9._-]*(:[A-Za-z0-9._-]+)?$ ]] || fail "invalid model name: $model"
done

compose_file="${ASD_COMPOSE_FILE:-$root/current/compose.json}"
[[ -f "$compose_file" ]] || fail "no current release or prepared Compose file at $compose_file"
compose=(docker compose --project-name asd-cloud --file "$compose_file")
"${compose[@]}" ps --services --status running | grep -qx ollama \
  || fail "the ollama service is not running; was the release prepared with the ai, rag or multi-agent component?"

for model in "${models[@]}"; do
  echo "pull-models: pulling $model (a 3B model is about 2 GB; this can take several minutes)"
  "${compose[@]}" exec -T ollama ollama pull "$model" || fail "pulling $model failed"
done

listing="$("${compose[@]}" exec -T ollama ollama list)"
for model in "${models[@]}"; do
  awk -v wanted="$model" '$1 == wanted { found = 1 } END { exit !found }' <<< "$listing" \
    || fail "$model is not listed by ollama after the pull"
done
for model in "${models[@]}"; do
  answer="$("${compose[@]}" exec -T ollama ollama run "$model" "Reply only with OK.")" \
    || fail "warming $model failed"
  [[ -n "${answer//[[:space:]]/}" ]] || fail "$model returned no response during warm-up"
done
echo "pull-models: ${models[*]} ready in the ollama container"
