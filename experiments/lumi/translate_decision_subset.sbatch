#!/usr/bin/env bash
# Adapted from the user's training/sbatch-vllm-qwen36.sh; native vLLM, TP=8.
#SBATCH --job-name=kev-di-translate
#SBATCH --account=project_465002563
#SBATCH --partition=standard-g
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=56
#SBATCH --mem=480G
#SBATCH --time=01:00:00
#SBATCH --exclusive
#SBATCH --chdir=/scratch/project_465002563/decision-models/kev-nesso2
#SBATCH --output=/scratch/project_465002563/decision-models/kev-nesso2/logs/di-translate-%j.log
set -euo pipefail
source runs/bilingual-all-v1/training-source/experiments/lumi/environment.sh
task_subset_dir="${1:?Pass the prepared evaluation directory}"
MODEL_PATH=/scratch/project_465002563/training/hf_cache/hub/models--Qwen--Qwen3.6-35B-A3B/snapshots/995ad96eacd98c81ed38be0c5b274b04031597b0
export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_TRANSFORMERS_OFFLINE=1
export SINGULARITYENV_NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3
export SINGULARITYENV_NCCL_NET_GDR_LEVEL=PHB
export SINGULARITYENV_OMP_NUM_THREADS=7
export SINGULARITYENV_VLLM_WORKER_MULTIPROC_METHOD=spawn
export SINGULARITYENV_VLLM_USE_TRITON_FLASH_ATTN=1
export SINGULARITYENV_MIOPEN_FIND_MODE=FAST
export SINGULARITYENV_VLLM_CACHE_ROOT=/scratch/project_465002563/training/vllm_cache
export SINGULARITYENV_TRITON_CACHE_DIR=/scratch/project_465002563/training/triton_cache
export SINGULARITYENV_TORCHINDUCTOR_CACHE_DIR="$TASK_ROOT/cache/vllm-inductor"
mkdir -p "$SINGULARITYENV_TORCHINDUCTOR_CACHE_DIR"

# Use native container packages for the server; Kev's Transformers overrides are
# used only by the separate translation client and data finalizer.
SINGULARITYENV_PYTHONPATH=/opt/venv/lib/python3.12/site-packages \
singularity exec -B /scratch/project_465002563:/scratch/project_465002563 "$TASK_IMAGE" bash -c '
  export HIP_VISIBLE_DEVICES="${ROCR_VISIBLE_DEVICES:-${HIP_VISIBLE_DEVICES:-}}"
  exec /opt/venv/bin/python -m vllm.entrypoints.openai.api_server \
    --model "$1" --tensor-parallel-size 8 --dtype bfloat16 \
    --gpu-memory-utilization 0.90 --max-model-len 8192 --max-num-seqs 64 \
    --max-num-batched-tokens 8192 --enable-chunked-prefill --reasoning-parser qwen3 \
    --served-model-name Qwen3.6-35B-A3B --no-enable-log-requests --host 127.0.0.1 --port 8017
' bash "$MODEL_PATH" > "$TASK_ROOT/logs/vllm-server-$SLURM_JOB_ID.log" 2>&1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT
for ((attempt=0; attempt<180; attempt++)); do
  if curl --silent --fail http://127.0.0.1:8017/health > /dev/null; then break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    tail -n 50 "$TASK_ROOT/logs/vllm-server-$SLURM_JOB_ID.log"
    exit 1
  fi
  if (( attempt % 6 == 0 )); then echo "Waiting for native vLLM: $((attempt * 10)) seconds"; fi
  sleep 10
done
curl --silent --fail http://127.0.0.1:8017/health > /dev/null
singularity exec -B /scratch/project_465002563:/scratch/project_465002563 "$TASK_IMAGE" \
  "$TASK_ROOT/env/bin/python" -u "$task_subset_dir/preparation-source/translate_decision_subset.py" \
  --out "$task_subset_dir"
singularity exec -B /scratch/project_465002563:/scratch/project_465002563 "$TASK_IMAGE" \
  "$TASK_ROOT/env/bin/python" -u "$task_subset_dir/preparation-source/prepare_decision_subset.py" \
  --root "$TASK_ROOT" --out "$task_subset_dir" --finalize
