#!/usr/bin/env bash
#SBATCH --job-name=kev-di-italian-prepare
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/di-italian-prepare-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
task_italian_dir="${1:?Pass the Italian evaluation directory}"
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$task_italian_dir/preparation-source/prepare_italian_selection.py" \
  --root "$TASK_ROOT" --source "$TASK_ROOT/runs/bilingual-all-v1/decision-index-bilingual-v1" --out "$task_italian_dir"
