#!/bin/sh
set -eu
cd "$(dirname "$0")"
precision=f16
from_source=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --precision) precision="${2:?Expected f16, q8, or both}"; shift 2 ;;
    --from-source) from_source=true; shift ;;
    *) echo 'Usage: ./setup.sh [--precision f16|q8|both] [--from-source]' >&2; exit 2 ;;
  esac
done
case "$precision" in f16|q8|both) ;; *) echo 'Invalid precision' >&2; exit 2 ;; esac
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-lock.txt
if ! .venv/bin/hf auth whoami >/dev/null 2>&1; then .venv/bin/hf auth login; fi
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
  HF_HUB_DISABLE_XET=1 .venv/bin/python download_gguf.py --precision "$precision"
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
