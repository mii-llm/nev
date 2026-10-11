#!/usr/bin/env bash
#SBATCH --job-name=kev-focused-v3
#SBATCH --account=project_465002563
#SBATCH --partition=dev-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/focused-v3-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
task_pilot_dir="${1:?Pass the isolated v3 directory}"
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$task_pilot_dir/source/run_focused_v3.py" --out "$task_pilot_dir"

srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$task_pilot_dir/source/finish_focused_v3.py" --out "$task_pilot_dir"
