#!/usr/bin/env bash
#SBATCH --job-name=kev-di-subset
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=00:45:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/di-eval-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
task_subset_dir="${1:?Pass the prepared evaluation directory}"
task_model="${2:?Choose 74000, 142000, parent, or laya}"
task_panel="${3:-selection}"
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$task_subset_dir/preparation-source/eval_decision_subset.py" \
  --root "$TASK_ROOT" --out "$task_subset_dir" --model "$task_model" --panel "$task_panel"
