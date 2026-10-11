#!/usr/bin/env bash
# Source on LUMI. All writable project paths stay in the user's scratch allocation.
export TASK_ROOT=/scratch/project_465002563/decision-models/kev-nesso2
export TASK_IMAGE=/pfs/lustref1/appl/local/laifs/containers/lumi-multitorch-u24r70f21m50t210-20260807_115122/lumi-multitorch-full-u24r70f21m50t210-20260807_115122.sif
export HF_HOME="$TASK_ROOT/cache/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub" HF_DATASETS_CACHE="$HF_HOME/datasets"
export XDG_CACHE_HOME="$TASK_ROOT/cache/xdg" XDG_CONFIG_HOME="$TASK_ROOT/cache/config"
export PIP_CACHE_DIR="$TASK_ROOT/cache/pip" TMPDIR="$TASK_ROOT/tmp"
export APPTAINER_CACHEDIR="$TASK_ROOT/cache/apptainer" SINGULARITY_CACHEDIR="$TASK_ROOT/cache/apptainer"
export APPTAINER_TMPDIR="$TMPDIR" SINGULARITY_TMPDIR="$TMPDIR"
export TRITON_CACHE_DIR="$TASK_ROOT/cache/triton" MIOPEN_USER_DB_PATH="$TASK_ROOT/cache/miopen"
export MIOPEN_CUSTOM_CACHE_DIR="$TASK_ROOT/cache/miopen"
export TORCH_HOME="$TASK_ROOT/cache/torch" TORCH_EXTENSIONS_DIR="$TASK_ROOT/cache/torch-extensions"
export NUMBA_CACHE_DIR="$TASK_ROOT/cache/numba" MPLCONFIGDIR="$TASK_ROOT/cache/matplotlib"
export PYTHONUSERBASE="$TASK_ROOT/cache/python-user" PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$TASK_ROOT/env/lib/python3.12/site-packages:$TASK_ROOT/src:/opt/venv/lib/python3.12/site-packages"
export TOKENIZERS_PARALLELISM=false WANDB_MODE=disabled HF_HUB_DISABLE_TELEMETRY=1
export OMP_NUM_THREADS=4
# Container-defined environment variables otherwise take precedence over the host.
for task_env_name in HF_HOME HF_HUB_CACHE HF_DATASETS_CACHE XDG_CACHE_HOME XDG_CONFIG_HOME \
  PIP_CACHE_DIR TMPDIR TRITON_CACHE_DIR MIOPEN_USER_DB_PATH MIOPEN_CUSTOM_CACHE_DIR \
  TORCH_HOME TORCH_EXTENSIONS_DIR NUMBA_CACHE_DIR MPLCONFIGDIR PYTHONUSERBASE \
  PYTHONDONTWRITEBYTECODE PYTHONPATH TOKENIZERS_PARALLELISM WANDB_MODE HF_HUB_DISABLE_TELEMETRY OMP_NUM_THREADS; do
  export "SINGULARITYENV_${task_env_name}=${!task_env_name}"
done
mkdir -p "$HF_HUB_CACHE" "$HF_DATASETS_CACHE" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" \
  "$PIP_CACHE_DIR" "$TMPDIR" "$APPTAINER_CACHEDIR" "$TRITON_CACHE_DIR" "$MIOPEN_USER_DB_PATH" \
  "$TORCH_HOME" "$TORCH_EXTENSIONS_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR" "$PYTHONUSERBASE" \
  "$TASK_ROOT/logs" "$TASK_ROOT/runs"
module use /appl/local/laifs/modules
module load lumi-aif-singularity-bindings
