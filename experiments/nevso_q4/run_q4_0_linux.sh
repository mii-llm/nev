#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then echo 'Usage: run_q4_0_linux.sh PREPARED_NEV_REPO EXPERIMENT_DIR' >&2; exit 2; fi
repo_root=$(cd "$1" && pwd)
experiment=$(cd "$2" && pwd)
code=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
python_bin="$repo_root/experiments/cpu_gguf/.venv/bin/python"
artifacts="$experiment/artifacts"
# Do not compete for CPU with the original four-run pilot.
timeout 1800 sh -c 'until test -f "$1/status.txt"; do sleep 5; done' sh "$experiment"
"$python_bin" "$code/quantize_q4_0.py" --artifacts "$artifacts" \
  --quantizer "$repo_root/experiments/cpu_gguf/build/bin/llama-quantize"
sha256sum "$code/PROTOCOL_Q4_0.md" "$code/run_q4_0.py" "$code/quantize_q4_0.py" \
  "$artifacts"/gguf/*q4_0.gguf > "$experiment/FREEZE_Q4_0.sha256"
for suite in routing greenhouse; do
  "$python_bin" "$code/run_q4_0.py" --repo-root "$repo_root" --artifacts "$artifacts" \
    --suite "$suite" --precision q4_0 --output "$experiment/results/$suite-q4_0.json"
done
echo complete > "$experiment/status-q4_0.txt"
