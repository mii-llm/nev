#!/usr/bin/env bash
#SBATCH --job-name=nev-demo
#SBATCH --account=project_465002563
#SBATCH --partition=dev-g
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=7
#SBATCH --mem=48G
#SBATCH --time=00:10:00
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/nev-demo-%j.log
set -euo pipefail
# Submit from the directory containing examples/ and runtime/.
nev_code_dir="${SLURM_SUBMIT_DIR:?Submit with sbatch from the Nev source directory}"
source /scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
export PYTHONPATH="$nev_code_dir/runtime:$TASK_ROOT/env/lib/python3.12/site-packages:/opt/venv/lib/python3.12/site-packages"
export SINGULARITYENV_PYTHONPATH="$PYTHONPATH"
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_TRANSFORMERS_OFFLINE=1
srun --cpu-bind=none singularity exec -B /scratch/project_465002563:/scratch/project_465002563 \
  "$TASK_IMAGE" "$TASK_ROOT/env/bin/python" -u "$nev_code_dir/examples/hf_decide.py" \
  --offline --device cuda "$@"
