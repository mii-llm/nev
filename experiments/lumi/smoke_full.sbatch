#!/usr/bin/env bash
#SBATCH --job-name=kev-resume-proof
#SBATCH --account=project_465002563
#SBATCH --partition=small-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/smoke-full-%j.log
set -euo pipefail
source src/experiments/lumi/environment.sh
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_HF_DATASETS_OFFLINE=1
run_python() {
  srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
    "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" "$@"
}
ROOT="$TASK_ROOT/runs/bilingual-all-v1"
PROOF="$ROOT/resume-proof-$SLURM_JOB_ID"
run_python -u "$TASK_ROOT/src/experiments/lumi/train_full.py" --root "$ROOT" --out "$PROOF/split" --smoke --stop-at 16
run_python -u "$TASK_ROOT/src/experiments/lumi/train_full.py" --root "$ROOT" --out "$PROOF/split" --smoke --stop-at 32
run_python -u "$TASK_ROOT/src/experiments/lumi/train_full.py" --root "$ROOT" --out "$PROOF/continuous" --smoke --stop-at 32
run_python "$TASK_ROOT/src/experiments/lumi/check_full_resume.py" "$PROOF"
