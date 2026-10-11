#!/usr/bin/env bash
#SBATCH --job-name=kev-reference-summary
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/kev-reference-summary-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/summarize_kev_reference.py" \
  --root "$TASK_ROOT/runs/bilingual-v2"
