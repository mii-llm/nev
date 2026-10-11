#!/usr/bin/env bash
#SBATCH --job-name=kev-nesso2-probe
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/probe-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -m pytest -q "$TASK_ROOT/src/tests/test_bilingual_port.py" \
  --basetemp "$TASK_ROOT/tmp/pytest-$SLURM_JOB_ID" -o "cache_dir=$TASK_ROOT/cache/pytest"
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$TASK_ROOT/src/experiments/lumi/probe.py" \
  --out "$TASK_ROOT/runs/probe-$SLURM_JOB_ID" --steps 10 --integrated
