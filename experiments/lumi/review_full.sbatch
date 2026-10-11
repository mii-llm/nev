#!/usr/bin/env bash
#SBATCH --job-name=kev-review-full
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/review-full-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/review_full.py" \
  --root "$TASK_ROOT/runs/bilingual-all-v1"
