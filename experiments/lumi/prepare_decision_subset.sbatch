#!/usr/bin/env bash
#SBATCH --job-name=kev-di-prepare
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/di-prepare-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
task_subset_dir="${1:?Pass the new evaluation directory}"
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$task_subset_dir/preparation-source/prepare_decision_subset.py" \
  --root "$TASK_ROOT" --out "$task_subset_dir"
