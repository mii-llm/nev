#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then echo 'Usage: run_linux.sh PREPARED_NEV_REPO EXPERIMENT_DIR' >&2; exit 2; fi
repo_root=$(cd "$1" && pwd)
experiment=$(cd "$2" && pwd)
code=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
python_bin="$repo_root/experiments/cpu_gguf/.venv/bin/python"
artifacts="$experiment/artifacts"
test -f "$artifacts/models/nev/v3/decision_head.safetensors"
ln -s "$repo_root/experiments/cpu_gguf/build" "$artifacts/build"
for model in nev-v3 nesso3; do
  ln -s "$repo_root/experiments/cpu_gguf/gguf/$model-q8.gguf" "$artifacts/gguf/$model-q8.gguf"
done
"$python_bin" "$code/quantize.py" --artifacts "$artifacts" \
  --quantizer "$repo_root/experiments/cpu_gguf/build/bin/llama-quantize"
mkdir -p "$experiment/results"
"$python_bin" -m pip freeze > "$experiment/environment.txt"
uname -a > "$experiment/host.txt"
lscpu >> "$experiment/host.txt"
sha256sum "$code/PROTOCOL.md" "$code/run.py" "$code/quantize.py" "$code/run_linux.sh" \
  "$artifacts"/gguf/*.gguf "$artifacts/models/nev/v3/decision_head.safetensors" \
  > "$experiment/FREEZE.sha256"
for config in routing:q8 routing:q4_k_m greenhouse:q4_k_m greenhouse:q8; do
  suite=${config%:*}
  precision=${config#*:}
  "$python_bin" "$code/run.py" --repo-root "$repo_root" --artifacts "$artifacts" \
    --suite "$suite" --precision "$precision" \
    --output "$experiment/results/$suite-$precision.json"
done
echo complete > "$experiment/status.txt"
