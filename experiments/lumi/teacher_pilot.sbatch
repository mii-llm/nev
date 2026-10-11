#!/usr/bin/env bash
#SBATCH --job-name=kev-nesso2-teacher
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/teacher-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/teacher_pilot.py" \
  --teacher-config "$TASK_ROOT/configs/teacher-qwen3-4b.json" --out "$TASK_ROOT/runs/teacher-$SLURM_JOB_ID"
