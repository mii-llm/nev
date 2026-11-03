#!/bin/sh
set -eu
cd "$(dirname "$0")"
precision=f16
from_source=false
model=both
python_bin=python3
gguf_only=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --precision) precision="${2:?Expected f16, q8, or both}"; shift 2 ;;
    --model) model="${2:?Expected nev, nesso3, or both}"; shift 2 ;;
    --from-source) from_source=true; shift ;;
    --python) python_bin="${2:?Expected a Python 3.12 or 3.13 executable}"; shift 2 ;;
    --gguf-only) gguf_only=true; shift ;;
    *) echo 'Usage: ./setup.sh [--precision f16|q8|both] [--model nev|nesso3|both] [--python python3.12] [--gguf-only | --from-source]' >&2; exit 2 ;;
  esac
done
case "$precision" in f16|q8|both) ;; *) echo 'Invalid precision' >&2; exit 2 ;; esac
case "$model" in nev|nesso3|both) ;; *) echo 'Invalid model' >&2; exit 2 ;; esac
if [ "$from_source" = true ] && [ "$model" != both ]; then
  echo '--from-source builds both models; omit --model for this recipe.' >&2; exit 2
fi
if [ "$from_source" = true ] && [ "$gguf_only" = true ]; then
  echo '--gguf-only cannot convert source weights; omit it with --from-source.' >&2; exit 2
fi
if [ ! -d .venv ]; then
  "$python_bin" -c 'import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else "Python 3.12 or 3.13 required; pass --python python3.12")'
  "$python_bin" -m venv .venv
fi
.venv/bin/python -c 'import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else "Existing .venv needs Python 3.12 or 3.13; use a fresh checkout")'
if [ "$gguf_only" = true ]; then
  .venv/bin/python -m pip install -r requirements-gguf.txt
  .venv/bin/python -m pip install --no-deps ./vendor/runtime
else
  .venv/bin/python -m pip install -r requirements-lock.txt
fi
# The API keeps using this checkout's controller, build and downloaded models.
# Standalone copies of the CPU experiment can still install without the API.
if [ -f ../../nevso/api.py ]; then
  .venv/bin/python -m pip install --no-deps -e ../..
fi
if [ ! -d llama.cpp/.git ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git llama.cpp
  git -C llama.cpp fetch --depth 1 origin 37d6d653e49aa73c947cc9631a5d499869a21cca
  git -C llama.cpp checkout --detach 37d6d653e49aa73c947cc9631a5d499869a21cca
fi
if [ "$(git -C llama.cpp rev-parse HEAD)" != 37d6d653e49aa73c947cc9631a5d499869a21cca ]; then
  echo 'Different llama.cpp revision; use a separate checkout or inspect it first.' >&2; exit 1
fi
mkdir -p results gguf
.venv/bin/cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="$PWD/.venv/bin/ninja"
.venv/bin/cmake --build build --target nev-cpu-worker llama-quantize -j 4
if [ "$from_source" = false ]; then
  HF_HUB_DISABLE_XET=1 .venv/bin/python download_gguf.py --precision "$precision" --model "$model"
else
  HF_HUB_DISABLE_XET=1 .venv/bin/python download_models.py
  .venv/bin/python prepare_gguf.py
  if [ "$precision" != f16 ]; then
    for name in nesso3 nev-v3; do
      if [ ! -f "gguf/$name-q8.gguf" ]; then
        build/bin/llama-quantize "gguf/$name-f16.gguf" "gguf/$name-q8.partial.gguf" Q8_0 4
        mv "gguf/$name-q8.partial.gguf" "gguf/$name-q8.gguf"
      fi
    done
  fi
fi
