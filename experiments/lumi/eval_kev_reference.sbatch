#!/usr/bin/env bash
#SBATCH --job-name=kev-reference-eval
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/kev-reference-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/eval_kev_reference.py" \
  --name "${1:?kev08b or kev4b}" --root "$TASK_ROOT/runs/bilingual-v2" \
  --references "$TASK_ROOT/references/jaredpalmer-kev"
