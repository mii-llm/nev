# Nesso3 + Nev on CPU — installation, examples and test results

Both models now run locally on this **Apple M3 Pro, 18 GiB RAM**, using four CPU
threads. Metal and CUDA are disabled. No server or network connection is needed
after setup. This experiment publishes the CPU bridge and recorded test results. Model files
are in two public HF repositories: [Nev GGUF](https://huggingface.co/mii-llm/nev-gguf)
and [Nesso3-0.4B-agentic GGUF](https://huggingface.co/mii-llm/nesso3-0.4B-agentic-gguf).
Each model card describes independent use; this guide also shows the combined agent.

## Install and run

Requirements: Python **3.12 or 3.13**, Git, a C/C++ compiler (on Mac, Xcode
command-line tools), GitHub and Hugging Face network access, and several GiB of
free disk space. The tested host is Apple Silicon macOS; Linux/Windows/phones
have not been validated. Setup builds the pinned llama.cpp CPU bridge, downloads
the selected GGUF pair plus required head/tokenizers, and verifies their SHA-256
hashes. Downloads are public and do not prompt for an HF login.

```bash
git clone https://github.com/mii-llm/nev.git
cd nev/experiments/cpu_gguf
./setup.sh --model both --precision f16

# Alternatively, download the faster/smaller Q8 pair:
# ./setup.sh --precision q8
# Or download both pairs:
# ./setup.sh --precision both
```

Both model revisions are pinned separately in `release.json`; the downloader refuses to
replace an existing artifact with a different hash. No original safetensors
backbone is needed for GGUF inference. The exact lock includes PyTorch for the
optional reference/conversion path; GGUF inference itself uses C++ and NumPy.

### Run one model independently

```bash
# Nev only: downloads its backbone, head and tokenizer; no Nesso3 weights.
./setup.sh --model nev --precision f16
.venv/bin/python decide.py
.venv/bin/python decide.py --request /absolute/path/request.json
.venv/bin/python test_standalone.py --model nev --precision f16

# Nesso3 only: downloads its generative backbone and tokenizer; no Nev weights.
./setup.sh --model nesso3 --precision q8
.venv/bin/python generate.py --precision q8 --language both
.venv/bin/python generate.py --precision q8 --language it --message 'Scrivi un breve saluto.'
.venv/bin/python test_standalone.py --model nesso3 --precision q8
```

The default Nesso3 example prints the proposed `read_sensor(sensor_id="S-6K3")`
call in both languages. It does not execute any tool or invent a sensor reading.
`--messages path.json` accepts a native role/content message array for custom
schemas and tool results. Nev independently returns decisions over supplied
options, including the default Italian refund example. Both commands share the
CPU build and Python environment; neither loads the other model.

### Compare Nesso3 alone with Nev selecting a tool

The [routing comparison](ROUTING_COMPARISON.md) demonstrates a clearer division
of work: Nev selects one of 12 tools; Nesso3 fills its arguments and answers from
the result. On 24 authored bilingual requests, exact execution improved from
18/24 to 22/24, reviewed task success from 14/24 to 20/24, and warm median time
fell from 2.57 s to 1.72 s on this Mac. All failures and readable traces are included.

```bash
.venv/bin/python compare_routing.py --precision q8 \
  --output "results/routing-$(date +%Y%m%d-%H%M%S).json"
```

This is a single-tool development demonstration, not a general-agent benchmark.
Use the guide for the English/Italian walkthrough and individual-case commands.

### Combine the models on CPU

Run `./setup.sh --model both --precision q8` to fetch both pinned releases.
The combined flow is **request → Nev ranks tool options → Nesso3 proposes a call
→ controller validates and executes a mock tool → result returns to Nesso3**.
It repeats within the controller limits and ends with a generated answer. The
controller uses supplied schemas and fixtures; it does not merge model weights.
The known multi-step and unsupported-action weaknesses below still apply.

From this experiment folder:

```bash

# Default: F16 GGUF, simple sensor read in both English and Italian.
./run.sh --language both

# Faster: both backbones in Q8. Quantization can change decisions.
./run.sh --precision q8 --language both

# A genuine two-step request, with the second call using a returned ID.
./run.sh --precision q8 --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'

# Different tools, same generic controller.
./run.sh --precision q8 --toolset notes --language it \
  --message 'Leggi la nota N-8R6 e dimmi il codice di accesso.'

# Nev alone: its default example is an Italian refund-routing request.
.venv/bin/python decide.py

# Supply your own Nev request JSON (state + questions).
.venv/bin/python decide.py --request /absolute/path/request.json
```

The default bilingual example is a passing smoke test selected after the full
CPU comparison. It asks for sensor `S-6K3`, executes the simulated read, and
answers **18.2°C** in both languages. The English dependent example searches
`Studio`, receives opaque ID `S-4J9`, reads that ID on a later turn, and answers
**21.5°C**. All tools are deterministic read-only mocks; no real device settings,
notes, files, music, or accounts are accessed. Use actual returned traces to
assess behavior. The Italian dependent case still fails in this pilot.

`--output results/my-test.json` saves a new trace file. Existing output files
are never overwritten. `--arm nesso_only` omits Nev ranking; both models still
load in this prototype. `--engine torch` runs the original models in FP32 on CPU.
The latter needs separately downloaded original weights (`.venv/bin/python
download_models.py`) and uses more memory.

### What the passing example looks like

| Language | Input | Nev decision | Nesso3 call | Tool result | Final answer |
| --- | --- | --- | --- | --- | --- |
| EN | Read temperature sensor S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `18.2 C` | The temperature is 18.2°C. |
| IT | Leggi la temperatura del sensore S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `18.2 C` | La temperatura è 18.2°C. |

These are the recorded F16 outputs in `results/demo-default.json`. The second
model turn sees the tool result before producing its answer. This is a selected
passing example, not a description of all requests.

## Run the tests

```bash
# Actual inference, bilingual tool/argument/answer checks and a Nev routing check:
.venv/bin/python test_smoke.py --precision f16 --output results/my-smoke-f16.json
.venv/bin/python test_smoke.py --precision q8 --output results/my-smoke-q8.json

# Twelve-request diagnostic including known failures (fresh output filenames):
.venv/bin/python benchmark.py --precision q8 --output results/my-q8-run.json
.venv/bin/python benchmark.py --precision f16 --output results/my-f16-run.json
```

Download the requested precision first. `test_smoke.py` fails if Nev chooses the
wrong tool, the executed function/arguments differ, the agent fails to answer,
or the expected temperature/unit is missing. It also checks Italian refund
routing. It is deliberately a small installation check. Benchmark output uses
an answer-anchor proxy; inspect complete traces and apply the documented semantic
corrections before interpreting it as quality. See `results/SUMMARY.json`.

## Measured results

Measured on this Mac on 14 October 2026, with four threads and no GPU. Twelve
fixed requests (six EN/six IT) include ten supported operations and two unavailable
actions. Models were warmed before request timing; loading is excluded. The Mac
was not isolated from other desktop activity. These are small diagnostic tests,
not stable production latency guarantees or a broad accuracy benchmark.

| Backend | Median full request EN | IT | Combined | Peak sampled summed RSS |
| --- | ---: | ---: | ---: | ---: |
| PyTorch / Transformers FP32 CPU | 3.02 s | 3.58 s | 3.39 s | 3336 MiB |
| GGUF F16 + FP32 Nev head | 3.73 s | 4.61 s | 4.24 s | 2872 MiB |
| GGUF Q8_0 + FP32 Nev head | 1.84 s | 2.26 s | 1.89 s | 2985 MiB |

RSS is sampled every 50 ms across Python and its worker children; shared/mapped
pages can be counted twice and macOS can reclaim mapped pages. This is **not
physical footprint**, and the similar F16/Q8 RSS numbers do not imply identical
weight sizes. The two Q8 files total approximately **902 MiB**, compared with
1685 MiB for the two F16 files. KV buffers, compute buffers, tokenizer, head and
Python add memory. The prototype uses FP32 KV caches for numerical checks and a
4096-token context per worker. Memory/cache optimization was not attempted.

For Nesso's eight short first-generation probes, median decoding speed excluding
prompt processing was about 89 tokens/s F16 and 129 tokens/s Q8. These are short
runs; end-to-end request timings above are the more useful comparison.

All three backends execute the expected plan on **9/10 supported requests**.
Answer anchors alone misleadingly pass nine: an Italian conversion answers
`68°C` when the result is `68°F`, and an Italian media answer presents artist
`Elio` as the track title. Assistant inspection therefore gives **7/10 complete,
grounded supported answers** for each backend. Neither unsupported-action request
gets a clear correct capability refusal. These errors already occur in the CPU
reference and are not solved by changing storage/inference format.

### Conversion checks

- Nesso3: GGUF tokenization matched HF on all eight bilingual probes. F16 greedy
  generation matched all eight FP32 reference token sequences; Q8 matched seven.
  The differing Q8 case and its reference both propose an invalid extra call.
- Nev: 20 requests contain **24 questions**, including choice, boolean, ordinal
  scores, and multi-question branch isolation. F16 preserved all 24 decisions;
  maximum probability difference from FP32 was **0.00541**.
- Nev Q8 preserved **23/24 decisions**, with a maximum probability difference of
  **0.06086**. In `notes-dependent-it`, the choice changed from `read_note` (about
  0.540) to `find_note` (about 0.518). That prerequisite choice is useful for the
  task, but it is still a change from the reference, not numerical equivalence.
- Nev's reserved-token IDs and tokenization matched. Final-normalized hidden
  states were checked at every option/readout position on a three-question input.
  Each question runs as a fresh causal row, so branches cannot attend to one
  another. The original FP32 head, scaling and calibration temperature are used.
- F16 is the default because it matched these decision checks more closely. It
  is not bit-identical FP32 inference; longer generations can still diverge.
  Q8 probabilities have not been recalibrated after quantization.

## Files and implementation

- `run.sh`, `demo.py`: user-facing bilingual agent runner.
- `decide.py`: standalone Nev CLI; accepts the existing request JSON format.
- `generate.py`: standalone Nesso3 generation; no Nev loading or tool execution.
- `test_standalone.py`: bilingual integration checks for one model at a time.
- `model_cards/nev.md`, `model_cards/nesso3.md`: current independent HF model cards.
- `HF_MODEL_CARD.md`: historical combined-repository card, kept with the original release evidence.
- `cpu_backend.py`: model adapters and NumPy implementation of the released Nev
  pointer head, with the frozen request renderer.
- `worker.cpp`: persistent CPU-only llama.cpp workers for generation and selected
  token hidden-state extraction. JSON-lines over local stdin/stdout; no HTTP server.
- `abstract_agent/`: unchanged schema-driven controller and frozen mock fixtures
  copied from `mii-llm/nev`, commit `28fda72603c8c7fe6729f3db2f856f8991fba38f`.
- `vendor/runtime/`: frozen native Nev source and original license/notice.
- `gguf/nesso3-{f16,q8}.gguf`: generative model.
- `gguf/nev-v3-{f16,q8}.gguf`: decision **backbone only**. Nev also needs the
  tokenizer, configuration and `models/nev/v3/decision_head.safetensors`.
- `models/`: tokenizers, head and configurations; optional original weights for reference checks.
- `results/agent-{torch,f16,q8}.json` and `.txt`: all 36 full agent traces.
- `results/verify-{nesso,nev}.json`: numerical/tokenization comparison evidence.
- `results/demo-default.txt`: output of the exact default command.
- `PROVENANCE.json`: original measurement revisions, hashes and host/build facts.
  Its script hashes describe the local experiment before publication edits.
  The repository-level `PACKAGE_MANIFEST.json` hashes the published source.
- `release.json`, `download_gguf.py`: separately pinned public HF releases and model-specific verified downloads.
- `test_smoke.py`: executable bilingual CPU integration check.
- `results/publication-smoke-*.json`: checks rerun from the publication checkout.

**Nev is not a standard chat GGUF.** Loading only its GGUF in a generic chat
application will not reproduce its decisions. Our adapter reads final hidden
states at the exact option and decision token positions and applies the original
head on CPU. It does not generate category labels or replace the trained head.
Nesso3 and Nev use separate trained backbones, so their weights are not shared.
The GGUF path does not use PyTorch for inference; the Python reference does.

## Reproduce or rerun

The environment is isolated in `.venv`. Python 3.13.2 was used here; the original
runtime supports Python 3.12–3.13. The exact dependency lock is included. The
llama.cpp source is pinned to `37d6d653e49aa73c947cc9631a5d499869a21cca`, with no
source modifications. Our bridge is outside that checkout. It is built with
Metal, CUDA, BLAS and OpenMP disabled; CPU ARM/NEON kernels are enabled.

The default `./setup.sh --precision f16` downloads already converted artifacts.
For independent conversion, `./setup.sh --from-source --precision both` downloads
the original pinned HF models and creates missing F16/Q8 files. Conversion writes
to a temporary filename before publishing a completed GGUF. Existing final files
are preserved; use the release downloader to verify their hashes.

The pinned bridge was rebuilt in this publication checkout and the smoke tests
were rerun. The existing dependency environment was reused; a completely fresh
OS/environment installation has not been tested. The HF downloader was also exercised in a separate folder: all ten ancillary
files were downloaded and verified, the existing Q8 pair was checked against
the remote manifest, and the bilingual smoke test passed using those files.
The large GGUFs were not downloaded a second time. The receipt and trace are
in `results/huggingface-download-check.json` and
`results/publication-hf-smoke-q8.json`. The full original dependency
lock is included. HTTPS downloads are used because an initial Xet transfer
stalled during the original experiment.

The optional original FP32 CPU reference needs `download_models.py` first:

```bash
# Fresh filenames are required for benchmark outputs.
.venv/bin/python benchmark.py --precision q8 --output results/my-q8-run.json
.venv/bin/python benchmark.py --precision f16 --output results/my-f16-run.json
.venv/bin/python benchmark.py --engine torch --output results/my-reference.json
```

`verify.py nesso` and `verify.py nev` produce fixed diagnostic filenames and
refuse to replace the saved results. Run them in a fresh experiment copy if you
want an independent conversion validation. Keeping Q4 out of this first version
avoids another unmeasured accuracy tradeoff; no phone runtime is claimed.

## Separate model release checks

`results/split-huggingface-publication.json` records the original split publication and
verified artifact hashes. Both F16 and Q8 standalone checks passed in English and Italian, in separate
folders with only the selected model artifacts. The combined Q8 CPU smoke test
also passed. `results/split-validation.json` indexes these checks. Supporting
files were freshly downloaded; existing GGUFs were verified against remote
SHA-256 manifests and reused.
The old combined repository is retired. Current downloads use the two public
releases under `mii-llm`; historical receipts preserve the original publication identities.

## Public download verification — 2026-10-16

The current `mii-llm` releases were checked using an empty HF cache and no saved
login or token. Both GGUF manifests and all supporting files downloaded and
passed hash checks; the bilingual combined Q8 smoke test passed. Existing GGUF
files were verified against the remote hashes and reused. Native Nev v2/v3 and
Nesso3 configuration downloads and weight-file metadata access also passed
anonymously. See `results/public-download-validation.json`.
