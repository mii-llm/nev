# Nevso: install, compare and inspect

Nevso combines **Nev v3 for tool selection** with **Nesso3 for call generation
and answers**. A shared controller validates calls and runs the supplied tools.
The preview uses local read-only mocks, with English and Italian examples.
There is no separate Nevso checkpoint: download the two public models once,
then run inference offline.

Choose **CPU GGUF on Linux or macOS** below, or the
[Linux/NVIDIA GPU guide](GPU_GUIDE.md). Both use `examples/nevso_demo.py` and the
same JSON tool catalog. Windows and phone deployment are not validated.

## 1. Prepare the host

You need Python **3.12 or 3.13**, Git, a C/C++ compiler, network access during
setup and several GiB of free disk space. The Q8 backbones total about 902 MiB;
that is not the total download, installation size or RAM requirement. Allow
room for the environment, build and two resident models. The historical Mac
diagnostic sampled about 2.9 GiB summed process RSS, not a minimum requirement.

**Ubuntu 24.04 CPU:**

```bash
sudo apt-get update
sudo apt-get install -y git build-essential python3.12 python3.12-venv
```

On another Linux distribution, install equivalent compiler, Python and venv
packages. A machine whose default `python3` is 3.10 needs a separate supported
Python; the installer accepts `--python /path/to/python3.12`.

**macOS CPU:** install Python 3.12 or 3.13 and the Xcode command-line tools:

```bash
xcode-select --install  # Only if the command-line tools are not installed.
python3.12 --version
```

## 2. Install the two CPU models

Run these commands on either Linux or macOS:

```bash
git clone https://github.com/mii-llm/nev.git
cd nev
./experiments/cpu_gguf/setup.sh \
  --python python3.12 --gguf-only --model both --precision q8
```

Use `--python python3.13` if that is your installed version. Setup creates
`experiments/cpu_gguf/.venv`, builds a pinned llama.cpp worker with CUDA and
Metal disabled, and verifies downloaded model hashes. No HF login is required.
CMake and Ninja are installed in the environment. The executable is built for
this host; rebuild it on a different CPU rather than copying the binary.

`--gguf-only` skips PyTorch and training/conversion packages in a fresh
environment. It supports published GGUF inference, not `--engine torch`, CUDA
or weight conversion. Omit that flag for the historical full dependency recipe;
do not combine it with `--from-source`. Existing environments are preserved.
Transformers may print “PyTorch was not found”; this is expected in this mode:
it supplies tokenization, while the C++ worker runs the models.

## 3. Check the installation

From the repository root:

```bash
RUN="results/nevso-$(date +%Y%m%d-%H%M%S)"
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/test_smoke.py \
  --precision q8 --output "$RUN-smoke.json"
```

This performs real CPU inference. It checks an English and Italian sensor call,
the returned **18.2°C**, and a standalone Nev routing decision. It exits with an
error if these checks fail. This is an installation check, not an accuracy
benchmark. Keep the output and report any failure; hardware kernels may change
generation.

## 4. Compare the models on the same request

```bash
# Italian: soil pH; the mock measurement is 6.4.
experiments/cpu_gguf/.venv/bin/python examples/nevso_demo.py \
  --engine gguf --precision q8 --threads 4 \
  --case read_soil_ph-it --output "$RUN-it.json"
cat "$RUN-it.txt"

# English: water remaining; the mock measurement is 81%.
experiments/cpu_gguf/.venv/bin/python examples/nevso_demo.py \
  --engine gguf --precision q8 --threads 4 \
  --case read_water_tank_level-en --output "$RUN-en.json"
cat "$RUN-en.txt"
```

Each case runs three approaches: Nesso3 sees all tools (`nesso_only`), Nev
orders all tools (`nev_ranked`), or Nev exposes one tool (`nev_selected`). The
trace shows the request, tool calls, validation, observations and final answer.
The expected measurement above is the fixture, not a guarantee that every arm
answers correctly. The purpose is to see the difference yourself.

All 24 greenhouse requests, including failures, can be run with:

```bash
experiments/cpu_gguf/.venv/bin/python examples/nevso_demo.py \
  --engine gguf --precision q8 --threads 4 --output "$RUN-full.json"
cat "$RUN-full.txt"
```

This retains 72 trials, three approaches per request. Use `--language en` or
`--language it` to select a language. Output paths must be new. JSON reports
separate exact executed calls from an answer-fragment proxy; the latter does
not establish factual correctness. Read the final answers too. Timings exclude
loading and warmup, and depend on the CPU and contention.

## 5. Bring a different catalog

Copy `experiments/cpu_gguf/greenhouse_suite.json` and adapt its tool descriptions,
JSON schemas, mock responses and test cases, preserving the structure. Run it
with `--suite /absolute/path/my-suite.json` using the same command and controller.
You do not need to retrain the models to try a new catalog.

Start with supported, single-operation requests whose required arguments are
present. Compare selection and ranking: a wrong top choice removes the correct
tool in selection mode, while ranking keeps alternatives but uses more tokens.
Real tools require your application's executor and permissions. The preview
does not provide a general guarantee for multi-step planning, unavailable
actions or factual final answers.

## Evidence

- [CPU Linux validation](LINUX_VALIDATION.md): fresh installation and actual tests.
- [Mac CPU comparison](../../experiments/cpu_gguf/GREENHOUSE_COMPARISON.md).
- [Linux/NVIDIA GPU comparison](GPU_GUIDE.md).
- [Notes, sensors and music comparison](../../experiments/cpu_gguf/ROUTING_COMPARISON.md).
- [Full stress-test results](../../experiments/nevso_stress/README.md).

The build follows llama.cpp's [CMake CPU build](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)
with the repository's pinned revision and explicit CPU-only settings.
