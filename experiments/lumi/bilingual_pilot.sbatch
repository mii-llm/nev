#!/usr/bin/env bash
#SBATCH --job-name=kev-bilingual-pilot
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/bilingual-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/run_bilingual_pilot.py" \
  "${1:?stage: compare, distilled, gold, or baselines}" \
  --root "${2:-$TASK_ROOT/runs/bilingual-v2}" --configs "$TASK_ROOT/configs"
