#!/usr/bin/env bash
#SBATCH --job-name=kev-okapi-small
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/okapi-eval-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
task_eval_dir="$TASK_ROOT/runs/bilingual-all-v1/decision-index-okapi-v1"
for task_mode in smoke full; do
  task_args=()
  if [ "$task_mode" = smoke ]; then task_args+=(--smoke); fi
  srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
    "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/okapi_eval.py" \
    --root "$TASK_ROOT" --out "$task_eval_dir" "${task_args[@]}"
done
