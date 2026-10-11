#!/usr/bin/env bash
#SBATCH --job-name=kev-bilingual-summary
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/bilingual-summary-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/summarize_pilot.py" \
  --root "${1:-$TASK_ROOT/runs/bilingual-v2}"
