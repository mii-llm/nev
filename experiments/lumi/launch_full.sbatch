#!/usr/bin/env bash
#SBATCH --job-name=kev-launch-full
#SBATCH --account=project_465002563
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/launch-full-%j.log
set -euo pipefail
python3 src/experiments/lumi/launch_full.py \
  --root /scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1 \
  --proof-job "${1:?completed GPU proof job}" --segments 8
