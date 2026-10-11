#!/usr/bin/env bash
# Run on the LUMI login node: bash examples/lumi_nev.sh fetch v3
set -euo pipefail
nev_code_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
nev_action="${1:-help}"
if [[ "$nev_action" != fetch ]]; then
  echo 'Usage: bash examples/lumi_nev.sh fetch [v2|v3]'
  echo 'Then: sbatch examples/lumi_nev.sbatch --variant v3 --language both'
  exit 0
fi
# Downloads do not need GPU-binding modules (which may stall on a login node).
source <(sed '/^module /d' /scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh)
export SINGULARITYENV_HF_HUB_OFFLINE=0
singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$nev_code_dir/examples/hf_decide.py" \
  --variant "${2:-v3}" --download-only
