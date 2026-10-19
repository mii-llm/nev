# Nevso preview: Nev + Nesso3 on GPU

**Nevso is the planned name for the Nev + Nesso3 agent.** This runnable preview
combines the existing public models; it is not a new trained checkpoint or a
merged model release. The example uses a greenhouse catalog with 12 read-only
mock tools and parallel English/Italian requests.

```text
User request → Nev ranks functions → Nesso3 proposes a call
             → controller validates → mock tool returns data → Nesso3 answers
```

The controller and domain definitions are the same ones used on Mac. The GPU
backend runs **Nesso3 BF16 + Nev v3 FP32**, using PyTorch/Transformers and CUDA.
It does not load GGUF files or require the llama.cpp CPU build. Changing precision
and kernels can change outputs; GPU results are recorded separately from Mac Q8.

## Install on an NVIDIA GPU machine

The recorded environment uses Python 3.12, PyTorch 2.10.0+cu126 and Transformers
5.17.0 on an A100. Install a CUDA-enabled PyTorch 2.10 build compatible with your
NVIDIA driver. The runner requires at least 4 GiB free GPU memory and caps its
PyTorch allocator at 4 GiB; that cap excludes non-PyTorch allocations.

```bash
git clone https://github.com/mii-llm/nev.git
cd nev
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'torch>=2.10,<2.11'
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime
python -m pip install -r experiments/abstract_agent/requirements.txt
python -c "import torch; assert torch.cuda.is_available(), 'Install a CUDA-enabled PyTorch build'"
```

GitHub hosts the code; Hugging Face hosts the public weights. Cache both pinned
models once, without a Hugging Face login:

```bash
python examples/hf_decide.py --variant v3 --download-only
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    'mii-llm/nesso3-0.4B-agentic',
    revision='56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8',
    allow_patterns=['*.json', '*.safetensors', '*.jinja', 'tokenizer.model'],
    token=False,
)
PY
```

## Run an example and read the trace

From the GitHub checkout, with the environment activated:

```bash
mkdir -p results
RUN="results/nevso-ph-it-$(date +%Y%m%d-%H%M%S)"
python -u examples/nevso_demo.py --case read_soil_ph-it --output "$RUN.json"
cat "$RUN.txt"
```

The request is **“Leggi il pH del terreno nell’aiuola B-73.”** The mock pH result
is **6.4**. The trace shows the selected tools, calls, validation, mock responses
and final answers for all three approaches:

- `nesso_only`: Nesso3 sees all 12 tools in a fixed seeded order.
- `nev_ranked`: Nev ranks all 12 tools once before Nesso3 starts.
- `nev_selected`: only Nev's top-ranked tool is exposed to Nesso3.

Use `--case read_soil_ph-en` for English. Run the complete bilingual comparison:

```bash
RUN="results/nevso-greenhouse-$(date +%Y%m%d-%H%M%S)"
python -u examples/nevso_demo.py --output "$RUN.json"
cat "$RUN.txt"
```

This runs 24 requests under all three approaches, retaining all 72 trials. Add
`--language en` or `--language it` to restrict the language. Supply
`--suite /absolute/path/custom-suite.json` to use a different tool catalog and
fixtures without changing the controller. Output paths must be new.

The wrapper uses the shared runner under `experiments/cpu_gguf/`; its `--engine
cuda` default selects the native GPU backend. Existing Mac installations can use
`--engine gguf --precision q8` with the same wrapper.

## A100 results — 19 October 2026

Same frozen 24-request greenhouse suite, 12 English + 12 Italian, under three
approaches: **72 trials**, with all results retained. Nesso3 BF16 and Nev FP32,
using the native CUDA backend on a shared A100 80 GB PCIe.

| Approach | Exact calls EN | Exact calls IT | Factual task success | Strict task success | Warm median request |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nesso3 alone | 7/12 | 6/12 | 12/24 | 11/24 | 1.38 s |
| **Nev ranks all tools + Nesso3** | **12/12** | **11/12** | **22/24** | **19/24** | **1.44 s** |
| Nev selects one tool + Nesso3 | 10/12 | 10/12 | 19/24 | 16/24 | 1.43 s |

Exact tool execution improves from **13/24 to 23/24** with ranking. Factual
success reflects assistant review of all requests, executed calls and final
answers. Strict success also requires the explicitly requested date format.
This is not independent human evaluation; the full traces are available below.

Peak PyTorch-allocated GPU memory was **2,616 MiB (2.55 GiB)**; peak reserved
memory was **2,662 MiB (2.60 GiB)**. These are measurements for this process,
including both loaded models, not total device use or host RAM. CUDA driver and
other non-PyTorch allocations are excluded. The GPU served another workload,
so the small timing differences between arms should not be treated as stable
speed rankings. No RAM optimization was applied.

### Italian example: retrieve soil pH

Request: **“Leggi il pH del terreno nell’aiuola B-73.”**

| Step | Nesso3 alone | Nev-ranked + Nesso3 |
| --- | --- | --- |
| Tool choice | `read_soil_moisture` | Nev places `read_soil_ph` first |
| Nesso3 call | `read_soil_moisture(bed_id="B-73")` | `read_soil_ph(bed_id="B-73")` |
| Mock observation | Soil moisture: 38% | Soil pH: 6.4 |
| Final answer | Reports **38% moisture**, answering the wrong question | “Il pH del terreno nell’aiuola B-73 è **6.4**.” |

The controller validates the generated arguments and executes the mock. It does
not supply the tool choice or generate the final prose. The isolated case and
the public `examples/nevso_demo.py` command reproduced this comparison.

### English example: retrieve the water-tank level

Request: **“What percentage of water remains in tank W-26?”**

Nesso3 alone says the tank's water level was not found after choosing the wrong
tool. Nev-ranked Nesso3 calls `read_water_tank_level(tank_id="W-26")`, receives
`water_remaining_percent: 81`, and answers **81%**. The Italian counterpart also
improves. These highlighted examples were selected from the retained full set.

### Failures remain visible

The ranking arm fails the Italian irrigation workflow by making additional
unrelated calls and never completing its answer. Its Italian fertilizer answer
uses the correct time but calls the operation irrigation. Three otherwise
correct date answers fail the requested `YYYY-MM-DD` format. Single-tool
selection additionally propagates wrong Nev choices; it is not the most
accurate strategy in this domain.

On GPU, Nesso3 alone already answers the English soil-pH example correctly.
Do not reuse the CPU-only claim that it fails that English case. The Italian
soil-pH and bilingual tank-level examples demonstrate measured GPU improvements.

## Evidence and regression checks

- [Full GPU JSON](evidence/greenhouse-a100.json), including model revisions,
  frozen suite, source hashes, individual reviews, timing and memory.
- [All 72 readable GPU traces](evidence/greenhouse-a100.txt).
- [Standalone Italian pH rerun](evidence/greenhouse-ph-it-a100.json).
- [Public CLI rerun](evidence/nevso-cli-ph-it-a100.json) and its
  [readable output](evidence/nevso-cli-ph-it-a100.txt).
- [Validation record](evidence/validation.json): seven controller tests, GPU
  subset/CLI reproduction, and unchanged Mac Q8 example outputs.
- [Nevso release working record](RELEASE_PLAN.md): what to preserve for release.

## Evaluation scope

These are frozen authored development examples, not an independent benchmark.
All results, including wrong calls and incorrect final answers, are retained.
Only supported, single-operation requests with explicit argument values are
covered. The controller validates schemas and argument provenance; it does not
verify every assertion in the generated answer. All tools are local mocks.

Exact-call accuracy and answer-fragment matches are computed automatically.
Answer-fragment matches are only a proxy: correct dates in the wrong requested
format and incorrect labels or units require trace review. Shared-GPU timings
include Nev, generation and validation, excluding loading and warmup. They do
not establish a controlled CPU-versus-GPU speedup.
