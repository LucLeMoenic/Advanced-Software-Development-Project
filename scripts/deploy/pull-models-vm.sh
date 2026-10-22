#!/usr/bin/env bash
# Pull the Ollama model(s) into the cloud AI profile's ollama container (bonus B1, B3, B4).
#
#   bash pull-models-vm.sh [model ...]        # default: llama3.2:3b, the one model every consumer uses
#
# Ollama starts with no models, and a 3B model is about 2 GB, far longer than the deployment's 240 s start-up wait, so this runs
# as its own step after deploy-vm.sh. It checks the ollama service is running, pulls each model, then confirms the model is
# listed (a pull that exits 0 is not trusted on its own). ASD_ROOT defaults to /opt/asd.
set -euo pipefail

root="${ASD_ROOT:-/opt/asd}"
fail() { echo "pull-models: $*" >&2; exit 1; }

models=("$@")
[[ ${#models[@]} -gt 0 ]] || models=(llama3.2:3b)
for model in "${models[@]}"; do
  [[ "$model" =~ ^[a-z0-9][a-z0-9._-]*(:[A-Za-z0-9._-]+)?$ ]] || fail "invalid model name: $model"
done

[[ -f "$root/current/compose.json" ]] || fail "no current release at $root/current"
compose=(docker compose --project-name asd-cloud --file "$root/current/compose.json")
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
echo "pull-models: ${models[*]} ready in the ollama container"
