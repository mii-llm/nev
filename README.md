# Nev — bilingual decision models

Use Nev to turn English or Italian requests into categorical, boolean, and ordinal decisions over options you supply. Install and try either released variant with the commands below, then compare their evaluation results—including the harder policy-following examples—to judge where each model is useful and where it fails.

**Weights:** [giux78/nev on Hugging Face](https://huggingface.co/giux78/nev), with separate `v2/` and `v3/` folders. Both the model repository and this GitHub repository are currently private.

## 1. Install and use Nev

Use **Python 3.12** and install a PyTorch build appropriate for your hardware first. The original verified environment was LUMI ROCm with PyTorch 2.10.0, Transformers 5.17.0, PEFT 0.21.0, Safetensors 0.8.0, Accelerate 1.13.0 and Hugging Face Hub 1.27.0. A fresh Python 3.12 environment on an NVIDIA A100 has also passed the limited inference checks and timing measurements below, using PyTorch 2.10.0+cu126. Apple M3 Pro CPU inference with F16 and Q8 GGUFs has now been tested (see below). Mobile deployment remains unvalidated.

From a checkout of this repository:

```bash
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime
hf auth login
```

Use an HF account that has access to the private model repository. The requirements record tested primary versions, not a complete transitive or hardware lockfile.

The simplest CLI downloads the pinned artifact and runs the native runtime:

```bash
python examples/hf_decide.py --variant v3 --language both
```

That built-in message is a loading smoke check. For a more demanding four-question Italian request, inspect and edit `examples/request-complex-it.json`, then run:

```bash
python examples/hf_decide.py --variant v3 \
  --request examples/request-complex-it.json
```

The JSON has two top-level fields, `state` and `questions`. It can include multiple `choice`, `noul`, and `score` questions with their own instructions and options. The response contains an `answers` object keyed by the question IDs, together with token usage and execution information.

Equivalent Python loading is:

```python
import json
from pathlib import Path
from huggingface_hub import snapshot_download
from decision_model import DecisionModel

revision = "c5c84121263b423f8846811a24790ab96e66cee3"
variant = "v3"  # or "v2"
folder = Path(snapshot_download(
    "giux78/nev",
    revision=revision,
    allow_patterns=[f"{variant}/**"],
)) / variant

model = DecisionModel.from_pretrained(folder, device="cuda")
request = json.loads(Path("examples/request-complex-it.json").read_text())
result = model.evaluate(**request)
print(json.dumps(result["answers"], ensure_ascii=False, indent=2))
```

PyTorch uses the `cuda` device name for the supported ROCm GPU path too. The native loader reads the artifact's `config.json`, `backbone/`, `tokenizer/`, decision head and calibration. It does not need to fetch the original parent after the standalone artifact has been downloaded.

The runtime enforces artifact-specific admission limits and rejects oversized inputs instead of silently truncating them. A selected option is always a model decision over the options supplied by the application; a high assigned probability is not permission to act without whatever checks the application needs.

### Can Transformers load Nev directly?

Transformers already loads the decoder inside the runtime. The whole released decision model is currently a custom `nn.Module` with `model_type=decision_model` and no `auto_map`. Therefore plain `transformers.AutoModel.from_pretrained("giux78/nev")` is not a supported loading command.

A custom `PreTrainedConfig` / `PreTrainedModel` wrapper and Hub registration could provide that interface without retraining. It would need to preserve the renderer, head, tokenizer, calibration, and equivalent outputs. That wrapper is not implemented in this release. For now, use the HF download plus native loader shown above.

### Run Nesso3 + Nev on a Mac CPU (GGUF)

The private [CPU GGUF release](https://huggingface.co/giux78/nev-nesso-cpu-gguf)
contains both models in **F16 and Q8_0**, plus Nev's original FP32 decision head,
tokenizers and configuration. Use Python 3.12–3.13 and a C/C++ compiler (Xcode
command-line tools on Mac). From this repository checkout:

```bash
cd experiments/cpu_gguf
./setup.sh --precision q8       # builds CPU bridge, logs into HF if needed, downloads + checks hashes
./run.sh --precision q8 --language both
.venv/bin/python decide.py --precision q8
.venv/bin/python test_smoke.py --precision q8 --output results/my-smoke.json

# Download F16 for closer agreement with the FP32 reference:
./setup.sh --precision f16
./run.sh --language both

# English request with a dependency between two calls:
./run.sh --precision q8 --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'

# Rerun the 12-request diagnostic, including known failures:
.venv/bin/python benchmark.py --precision q8 --output results/my-cpu-eval.json
```

Inference runs offline, on four CPU threads, with no Metal or CUDA offload.
Downloads are pinned and SHA-256 checked. Q8 uses about **902 MiB** for the two
GGUFs; F16 uses about **1685 MiB**. These are file sizes, not memory requirements.
The Python environment includes PyTorch for optional reference/conversion tests;
the GGUF inference path uses llama.cpp and NumPy.

**Nev needs its custom adapter and decision head.** It is not a chat GGUF that
can be dropped into a generic chat app. Nesso3 generates calls and answers;
Nev scores the supplied options from backbone hidden states. Each question runs
in an isolated causal row with the original renderer and calibration.

The passing bilingual smoke test produces this sequence (recorded F16 outputs):

| Language | Request | Nev choice | Nesso3 function call | Tool result | Answer |
| --- | --- | --- | --- | --- | --- |
| EN | Read temperature sensor S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `18.2 C` | The temperature is 18.2°C. |
| IT | Leggi la temperatura del sensore S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `18.2 C` | La temperatura è 18.2°C. |

These are selected passing examples with deterministic read-only mock tools.
The English dependent example finds `S-4J9`, then reads it and answers **21.5°C**.
The corresponding Italian dependent request still fails.

**CPU evaluation:** Apple M3 Pro, 18 GiB RAM, four threads, 14 October 2026.
Twelve fixed requests, six English/six Italian, with warmed resident models;
loading excluded. Shared desktop activity can affect these small-sample timings.

| Backend | EN median request | IT median request | Overall median |
| --- | ---: | ---: | ---: |
| Original FP32 PyTorch CPU | 3.02 s | 3.58 s | 3.39 s |
| F16 GGUF + FP32 head | 3.73 s | 4.61 s | 4.24 s |
| Q8_0 GGUF + FP32 head | 1.84 s | 2.26 s | 1.89 s |

F16 preserved **24/24 Nev decisions** on 20 verification requests (maximum
probability difference 0.00541); Q8 preserved **23/24** (maximum difference
0.06086). Nesso's eight first-generation sequences matched the FP32 reference
8/8 with F16 and 7/8 with Q8. F16 is the default for fidelity; quantized
probabilities have not been recalibrated.

All three backends executed the expected plan on **9/10 supported requests**,
but inspection found **7/10 fully grounded final answers**. Italian failures
included a wrong temperature unit and confusing artist with title. Correct
unsupported-action refusals were **0/2** for every backend. GGUF makes the
prototype runnable locally; it does not resolve those model weaknesses.
Sampled summed RSS was about 2.9 GiB for GGUF, but this can double-count shared
or mapped pages and is not physical footprint. Phones and other platforms have
not been validated.

The [complete CPU guide and source](experiments/cpu_gguf/README.md) include the
pinned build/conversion recipe, original raw traces, readable failures, numerical
checks and smoke tests. A clean bridge build and inference checks were rerun for
publication using the existing Python environment; a clean OS installation was
not tested. The original experimental provenance is preserved separately from
the hashes of the publication files.

### Run in the prepared A100 environment

A separate environment is installed at `~/nev-a100/.venv`, with source in
`~/nev-a100/source` and both HF variants cached locally. After SSH into the A100:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source

# Four decisions over a custom Italian request; edit the JSON to try your own.
python examples/hf_decide.py --offline --variant v3 \
  --request examples/request-complex-it.json

# Compare both models on all authored bilingual scenarios.
python examples/run_scenarios.py --variants v2 v3 \
  --output "../results/scenarios-$(date +%Y%m%d-%H%M%S).json"

# Time v3 with synchronized FP32 and BF16-autocast inference.
python examples/benchmark_latency.py --variants v3 --repeats 3 \
  --output "../results/speed-$(date +%Y%m%d-%H%M%S).json"
```

The scenario and timing commands preserve existing files, so use a fresh output
filename each time. `--variants v2 v3` times both variants; `--repeats 1` makes a
brief check. The speed script requires at least 6 GiB free GPU memory and caps
its PyTorch allocator at that amount. It leaves other GPU processes running.
The ordinary request helper uses FP32; the timing script explicitly compares
FP32 with BF16 autocast while retaining FP32 model weights.

The completed check is in `~/nev-a100/results/speed-shared.json`, with readable
progress in `speed-shared.log`. Model downloads and Python imports are excluded
from the latency measurements. Source the activation script in each new shell.

### Example gallery: English and Italian

Read these as **input → decision** examples. Each English/Italian pair below
passed on both released variants on the A100; the displayed outputs are from
**v3, native FP32 inference**. These four pairs were selected from the recorded
candidate run for documentation. They illustrate successful behavior, not
representative accuracy; the evaluation below retains all candidates and failures.

#### Support routing

Available choices: `shipping`, `billing`, `account`, `returns`, `technical`.

| Language | Input | Expected | Actual v3 output |
|---|---|---|---|
| English | My monthly subscription was charged twice on the same day. I can see both completed payments on my statement and need this checked. | `billing` | ✓ `billing` |
| Italian | Il mio abbonamento mensile è stato addebitato due volte nello stesso giorno. Vedo entrambi i pagamenti completati sull’estratto conto e vorrei una verifica. | `billing` | ✓ `billing` |

#### Function selection

Available choices: `get_order_status`, `get_invoice`, `search_help_center`, `list_transactions`, `no_tool`.

| Language | Input | Expected | Actual v3 output |
|---|---|---|---|
| English | I need a copy of the invoice for order ORD-2048 to attach to my expense report. Please retrieve the document. | `get_invoice` | ✓ `get_invoice` |
| Italian | Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota spese. Recuperate il documento, per favore. | `get_invoice` | ✓ `get_invoice` |

For both languages, the application can assemble the following proposed call:

```json
{"name": "get_invoice", "arguments": {"order_id": "ORD-2048"}, "executed": false}
```

**Nev selected `get_invoice`; the application supplied `order_id`.** This demo
neither generates arguments nor executes a tool.

#### News-topic classification

Available choices: `world`, `sports`, `business`, `science_technology`.

| Language | Input | Expected | Actual v3 output |
|---|---|---|---|
| English | Researchers demonstrated a new optical chip that processes signals using light. The laboratory prototype could reduce the energy required by future computers. | `science_technology` | ✓ `science_technology` |
| Italian | I ricercatori hanno presentato un nuovo chip ottico che elabora segnali usando la luce. Il prototipo di laboratorio potrebbe ridurre l’energia necessaria ai computer del futuro. | `science_technology` | ✓ `science_technology` |

#### Banking intents

Available choices: `cash_withdrawal`, `card_payment`, `bank_transfer`, `card_delivery`, `card_pin`, `exchange_rate`.

| Language | Input | Expected | Actual v3 output |
|---|---|---|---|
| English | The ATM debited my account, but the machine did not dispense any cash. How do I report the failed withdrawal? | `cash_withdrawal` | ✓ `cash_withdrawal` |
| Italian | Il bancomat ha addebitato il mio conto, ma non ha erogato contanti. Come posso segnalare il prelievo non riuscito? | `cash_withdrawal` | ✓ `cash_withdrawal` |

The complete editable inputs are in `examples/reference_examples.json`.
Use the commands immediately below to run them on the prepared A100. The full
32-candidate record, including unsuccessful cases, is retained in
`docs/nesso2/evidence/a100-reference-candidates.json` in the GitHub repository.

### Bilingual reference examples: routing, function selection and classification

The A100 examples below demonstrate decisions that succeeded in both English
and Italian. They use the exact released v2/v3 weights and native FP32 cached
inference. The complete candidate results, including failures, appear in the
evaluation section; the successful gallery is a **curated demonstration**, not
an accuracy benchmark. No model was retrained for these examples.

In the prepared A100 environment:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source

# See the English and Italian requests, selected function, probabilities,
# and the proposed call with application-supplied arguments.
python examples/function_calling_demo.py --variant v3 --language both

# Other read-only function selections: order, guide, payments.
python examples/function_calling_demo.py --variant v3 --example guide

# Run all 16 curated requests (8 parallel bilingual pairs).
python examples/run_reference_examples.py --variants v2 v3 \
  --cases examples/reference_examples.json \
  --output "../results/reference-$(date +%Y%m%d-%H%M%S).json"

# Run every candidate, including the unsuccessful account-recovery example.
python examples/run_reference_examples.py --variants v2 v3 \
  --output "../results/candidates-$(date +%Y%m%d-%H%M%S).json"
```

From a different machine, first install `runtime/`, authenticate for the private
HF repository and cache the pinned weights using
`python examples/hf_decide.py --variant v3 --download-only` (repeat for v2).
Create an output directory and adjust the output path. These runners require a
CUDA-compatible GPU and at least 4 GiB free memory, cap their PyTorch allocator
at 4 GiB, and load only locally cached weights. The normal request helper also
accepts `examples/request-function-en.json` or
`examples/request-function-it.json` with `--request`.

The function demo runs the invoice-retrieval example in the gallery by default.
The application then constructs a dry-run call with argument provenance:

```json
{
  "name": "get_invoice",
  "arguments": {"order_id": "ORD-2048"},
  "executed": false,
  "argument_source": "synthetic application context; not model output"
}
```

Nev predicts the **function name**. `proposed_call()` in
`examples/run_reference_examples.py` maps that name to an allowed argument
schema and uses synthetic application context. It does not extract arguments
from the user's text, generate arbitrary JSON or execute a function. Selecting
`no_tool` is supported by the example but was not evaluated in this candidate
set. Multi-step tool use and out-of-scope detection are not established here.

### Try Nev with generative Nesso3 as one agent

The A100 prototype now uses **`giux78/nesso3-0.4B-agentic`** for generated calls
and answers, with **Nev v3** ranking all four available tools. Python validates
arguments and runs **local simulated read-only tools**. Nesso3 is pinned to
`56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`; Nev's weights are unchanged.
The previous Nesso2 generator remains selectable with `--generator nesso2`.

On the prepared A100, these commands print human-readable steps:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source

python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked --format text --language it \
  --message "Qual è lo stato della spedizione e il riferimento di tracciamento dell’ordine ORD-6101?"

python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked --format text --language en \
  --message "What is the shipment status and tracking reference for order ORD-6101?"
```

`nesso3` is the default generator. Omit `--format text` for full JSON traces.
Use `--arm nesso_only` for the baseline. All tools remain available in
`nev_ranked`; hard top-two filtering is not recommended from the earlier pilot.
Both pinned models must be cached; the allocator is capped at 8 GiB and checks
for that much free GPU memory. Loading is outside the recorded inference timing.

**Successful Nesso3 + Nev examples, selected after inspecting all eight candidates:**

| Language / task | Exact request | Generated call | Actual final response |
|---|---|---|---|
| EN / shipment | What is the shipment status and tracking reference for order ORD-6101? | `get_order_status(order_id="ORD-6101")` | The shipment status is "in transit", and the tracking reference is TRK-ORD-6101. |
| IT / shipment | Qual è lo stato della spedizione e il riferimento di tracciamento dell’ordine ORD-6101? | `get_order_status(order_id="ORD-6101")` | Lo stato della spedizione è "in_transit" e il riferimento di tracciamento è "TRK-ORD-6101". |
| EN / invoice | Get the invoice for order ORD-6101 and tell me the filename. | `get_invoice(order_id="ORD-6101")` | The invoice for order ORD-6101 is in "invoice_ORD-6101.pdf". |
| IT / guide | Trova il riferimento della guida del prodotto PX-7. | `search_help_center(product="PX-7")` | Il riferimento della guida del prodotto PX-7 è GUIDE-PX-7. |

For either shipment example the sequence is: Nev puts shipment lookup first →
Nesso3 generates the call → the mock tool returns `in_transit` and
`TRK-ORD-6101` → Nesso3 answers from that observation. These four runs passed
without extra calls and took 1.12–1.41 seconds after warmup, including Nev, on
a shared A100. Separate fresh-process shipment demos took 1.79 s EN / 2.05 s IT
(excluding model loading, including first-inference warmup).

All candidates, including failures, appear in the
[readable step-by-step traces](docs/nesso3/SIMPLE_TRACES.md). This is a curated
demonstration, not a general accuracy claim. The comparison is reported below.
The adapter follows the compact tool contract in the
[Nesso3 model card](https://huggingface.co/giux78/nesso3-0.4B-agentic) and
[training report](https://github.com/mii-llm/zagreus-nesso-slm/tree/main/nesso3).



### One read operation: a tested controller for Nesso3's weak completion stage

On 24 simple requests (12 EN / 12 IT), Nev ranked the correct tool first and
Nesso3's first generated call had the correct function and arguments every time.
Failures came from extra calls, loops after a successful result, incorrect
copying of filenames, incomplete lists and refusals despite available data.
This is evidence for these four tools, not universal routing accuracy.

For an application that already restricts the request to **one supported read**,
use `--policy single_read`. It validates and deduplicates Nesso3's generated
calls, requires one valid call agreeing with Nev and one explicit reference,
executes once, and formats the returned facts in code. It records every rejected
extra call. It does not ask Nesso3 for a second answer.

```bash
python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy single_read --format text --language it \
  --message "Elenca i miei pagamenti di 2026-06 e dimmi il totale in EUR."
```

Actual application-formatted answer:

> Pagamenti di 2026-06: 24,50 EUR, 39,25 EUR. Totale: 63,75 EUR.

This endpoint does **not** detect all unsupported intents or multi-step requests.
Its scope must be established by the application. Ambiguous/no valid calls,
multiple recognized references, or disagreement with Nev cause deferral; arbitrary
out-of-scope detection is unmeasured. Use a separate workflow for multi-step
plans, unsupported actions and unrestricted chat. The demo default remains
`baseline`; selecting this endpoint is explicit. No model weights changed.



### Unified single-read, multi-step and unsupported-request workflow

`--policy workflow` adds one entry point above the previous single-read
controller. It recognizes declared English/Italian request forms, builds an
ordered plan, checks every step with Nev and Nesso3 before any execution, and
then runs up to four reads sequentially. It uses the same validators and
bilingual result templates. Unsupported or unmatched clauses stop the entire
request. The earlier policies remain available and unchanged.

```bash
python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy workflow --format text --language it \
  --message "Prima controlla la spedizione ORD-4731, poi recupera la fattura dell’ordine ORD-4731."
```

The workflow validates both proposed calls, executes shipment lookup followed
by invoice lookup, and returns:

> 1. Ordine ORD-4731: in transito. Riferimento di tracciamento: TRK-ORD-4731.
> 2. La fattura dell’ordine ORD-4731 è invoice_ORD-4731.pdf.

English works through the same entry point:

```bash
python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy workflow --format text --language en \
  --message "First check shipment ORD-4731, then get the invoice for order ORD-4731."

python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy workflow --format text --language en \
  --message "Shipment ORD-4731; cancel order ORD-4731."
```

The second request returns “This action is not supported by the available tools.
No operation was executed.” It performs neither lookup nor cancellation.

**Scope:** the full request must match a finite bilingual grammar. Each step
needs its own explicit reference. Conditional plans, pronouns, output-dependent
arguments, unknown paraphrases and unsupported actions defer or refuse. The
unsupported-word check can also refuse benign negations or phrases such as
“send me the invoice”. The planner and final summaries are application code;
this does not demonstrate general autonomous planning or the added value of
models over a pure parser for these known forms. All tools remain simulations.
The [workflow report](docs/nesso3/WORKFLOW_REPORT.md) describes the grammar,
execution states, limits and evidence.

### Try the domain-independent controller

The separate `experiments/abstract_agent/` pilot removes the application grammar
and answer templates. It accepts tool schemas at runtime: Nesso3 chooses calls,
consumes observations and generates the final answer; Nev can rank tools or
experimentally gate execution. The same controller handles notes, sensors and
media fixtures, including lookup→read dependencies and opaque tool names.

In the prepared A100 environment:

```bash
python -m pip install -r experiments/abstract_agent/requirements.txt
python experiments/abstract_agent/demo.py --toolset sensors --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'
python experiments/abstract_agent/demo.py --toolset sensors --language it \
  --message 'Trova il sensore di temperatura in Studio, poi leggi la sua temperatura.'
```

Use `--arm nesso_only`, `shuffled`, `nev_ranked` (default), or `nev_gated` to
compare behavior. Supply `--toolsets /path/to/custom.json --toolset name` to
change tools without editing the engine. Tool descriptions and schemas still
define what functions mean; the controller itself has no domain-specific rules.
All tools are mocks. This experiment measures model behavior on the A100,
not phone/laptop performance. The [protocol and source guide](experiments/abstract_agent/README.md)
explain validation, reproducibility and deployment limits.


## 2. Run and evaluate on LUMI

A ready copy of the examples and frozen runtime is staged in the existing project installation. After connecting to LUMI:

```bash
cd /scratch/project_465002563/decision-models/kev-nesso2/releases/publication-nev/demo

# Download the pinned private variants into the scratch cache.
bash examples/lumi_nev.sh fetch v2
bash examples/lumi_nev.sh fetch v3

# Compare both models on all 20 harder bilingual requests.
sbatch examples/lumi_scenarios.sbatch
```

The fetch commands use the existing HF login. GPU inference then runs offline in the recorded container. The job loads each model once, warms it up, and prints every prediction, assigned probability, expected answer and success/failure. A full JSON report is saved alongside the log.

Replace `JOBID` with the number returned by `sbatch`:

```bash
squeue -j JOBID
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.log
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.json
```

The completed run reported above is **22720810**, so its results can be inspected immediately:

```bash
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-22720810.log
```

To run only v3, append `--variants v3` to the scenario submission. To edit your own four-question Italian case and inspect one model:

```bash
sbatch examples/lumi_nev.sbatch --variant v3 \
  --request examples/request-complex-it.json
```

That single-request job writes `logs/nev-demo-JOBID.log`. For a quick test of your own text against the simple example's three department options:

```bash
sbatch examples/lumi_nev.sbatch --variant v3 --language it \
  --state "Mi avete addebitato due volte la stessa fattura."
```

These wrappers use the existing LUMI project environment and request one GPU on `dev-g`. When using another checkout on LUMI, submit from its root so `SLURM_SUBMIT_DIR` locates `runtime/` and `examples/`. All download, cache, log and result paths remain under `/scratch/project_465002563/`.

First-call time includes initialization and warmup. The difference between a slow first example and a faster later example is not a controlled latency benchmark.

## 3. Evaluation of the released models

| Released variant | Selected checkpoint | Observed strengths | Observed tradeoffs |
|---|---|---|---|
| **V2 Practical** | Original decision checkpoint 74k +256 adaptation updates | Better refund accuracy and Italian urgency than v3 on the reused practical test | Weaker routing |
| **V3 Routing** | Selected v2 +512 focused adaptation updates | Better routing; substantial gains on a new synthetic 16-intent/routing test | Refund and Italian urgency regressions; weak large-option intent classification |

These are measured differences on the described test sets. Both variants remain research models. The harder examples later in this README show that neither reliably follows all supplied policies, even when it assigns a high probability to its answer.

The following tables evaluate **merged exported weights**, not inferred adapter performance. Both exports store FP32 parameters; these benchmark runs used BF16 autocast. The external subsets used rows/T=1 scoring, while practical evaluation used packed logits.

Every comparison in the first table uses identical examples across v2 and v3. Unsupported requests count as incorrect. N is the number of examples **per language**.

| Task | N/language | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|---:|
| ARC-Challenge | 200 | 31.00% | 29.00% | 30.50% | 31.00% |
| HellaSwag | 200 | 33.00% | 33.00% | 29.50% | 33.00% |
| MMLU | 228 | 31.58% | 32.46% | 32.02% | 32.46% |
| ANLI | 150 | 30.67% | 38.00% | 30.00% | 38.00% |
| CLINC150+OOS | 151 | 4.64% | 6.62% | 5.30% | 12.58% |
| When2Call MCQ | 150 | 48.00% | 40.67% | 46.00% | 38.67% |
| Practical escalation | 256 | 51.95% | 51.56% | 53.52% | 51.17% |
| Practical refund | 256 | 61.33% | 52.73% | 52.73% | 50.39% |
| Practical routing | 256 | 29.69% | 34.77% | 55.08% | 46.88% |
| Practical urgency | 256 | 33.59% | 42.97% | 33.59% | 37.89% |
| **Practical overall** | **1,024** | **44.14%** | **45.51%** | **48.73%** | **46.58%** |

V3 improves practical routing by **25.39 English / 12.11 Italian percentage points** over the v2 export. Refund accuracy falls by **8.59 / 2.34 points**, and Italian urgency falls by **5.08 points**. The higher practical average does not mean all decisions improved.

### Comparing with Laya fairly

The comparison model is `convaiinnovations/laya-multilingual`. Its context/option admission limits exclude some examples that Nev can accept. For the table below, an English/Italian pair is included only when both versions fit every model in the recorded comparison. This produces smaller denominators for the external panels.

| Panel on common bilingual support | N/language | V2 EN / IT | V3 EN / IT | Laya EN / IT |
|---|---:|---:|---:|---:|
| Okapi academic subset | 513 | 31.19% / 31.19% | 30.41% / 32.55% | 30.02% / 27.10% |
| Decision Index subset | 378 | 24.07% / 25.66% | 23.81% / 27.78% | 30.16% / 32.01% |
| Practical v2 | 1,024 | 44.14% / 45.51% | 48.73% / 46.58% | 43.65% / 39.06% |

These are separate panel averages, not one combined benchmark score. The full-panel task table and common-support table have different denominators and should not be compared as if they used identical samples. Laya remains substantially stronger on CLINC, despite Nev's gains on the new synthetic 16-intent task.

The academic tasks use the multilingual evaluation work associated with Okapi in lm-evaluation-harness. The Decision Index work adapts selected tasks; it does not reproduce an official full-suite composite score. Italian evaluation text is synthetic and partly reviewed, including corrections to 27 CLINC labels. CLINC itself was not a training source, although other intent tasks were. Pretraining contamination is unknown.

### New synthetic 16-intent and routing test

A new synthetic 16-intent/routing test contained 512 requests per language:

| Artifact on the new synthetic test | English | Italian |
|---|---:|---:|
| V2 adapter | 23.63% | 25.00% |
| V3 adapter | 54.88% | 62.89% |
| **V3 released export** | **54.69%** | **62.50%** |
| Laya | 26.17% | 28.71% |

The v2 export was not measured on this new panel; the v2 row above is explicitly its adapter. This controlled synthetic 16-intent task differs from 151-option CLINC and real customer traffic.

### Bilingual reference candidates on A100

The existing broader evidence supports v3's relative routing and small-option
intent gains: 55.08% EN / 46.88% IT on practical routing and 54.69% / 62.50% on
the new synthetic 16-intent panel. News-topic classification also has a training
precedent in AG News, and Banking77 supplied banking intents. Training exposure
is not evidence of generalization. Function-name selection is an application of
categorical inference; there was no prior dedicated function-calling benchmark.

To find useful documentation examples, we authored **32 requests in 16 parallel
English/Italian pairs**, four pairs per domain. Text, options, expected labels
and the bilingual selection rule were fixed before running either model. All
32 requests were evaluated once per variant on the shared A100 on 2026-10-12,
using the pinned FP32 exports and native cached inference. No prompt was revised
after seeing its prediction. Counts below include **every candidate**, before
selecting the successful gallery.

| Candidate domain | Options | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|---:|
| Support routing | 5 | 3/4 | 4/4 | 3/4 | 3/4 |
| Function-name selection | 5 | 4/4 | 4/4 | 4/4 | 4/4 |
| News-topic classification | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Banking intent classification | 6 | 4/4 | 4/4 | 4/4 | 4/4 |

These tiny, clear-intent examples do not establish 100% task accuracy. Four
banking intents were queried out of six offered choices; four functions were
queried out of five choices. The news cases are invented examples, one per
topic, rather than an AG News test. These counts are not comparable to the
harder policy examples, 16-intent panel or 151-option CLINC results.

The failed routing pair asks to recover account access after changing phones:
v3 selected `technical` instead of `account` in both languages (96.1% EN and
77.2% IT assigned probability). V2 also failed English but passed Italian.
The failure remains in `examples/reference_candidates.json` and the complete
record `docs/nesso2/evidence/a100-reference-candidates.json`. High assigned
probability still does not establish correctness.

After inspecting these outputs, we selected **eight pairs / 16 requests** that
both variants answered correctly in both languages, saved as
`examples/reference_examples.json`. The selected file states that it was
curated after evaluation. It includes two examples each of routing, function
selection, news topics and banking intents. All were rerun with the user-facing
command; this repeat checks reproducibility, not independent accuracy.

The successful examples appear in the **Example gallery: English and Italian**
near the installation instructions above.

These results support using the released models as examples of **clear-intent
classification over a small, described option set**. They do not reverse the
observed failures on numeric thresholds, boolean policies, interacting rules,
or unfamiliar large intent sets. The application should keep deterministic
business rules separate from model-selected intent.

### Nesso3 + Nev: simple example check

Eight requests (four EN/IT pairs) were fixed before Nesso3 inference: shipment,
invoice, product guide and payment total. Both modes used the same four compact
schemas, mock observations, validators, greedy decoding and 192-token budget.

| Mode | Strict checks EN /4 | Strict checks IT /4 | Median EN | Median IT |
|---|---:|---:|---:|---:|
| Nesso3 alone | 2 | 2 | 1.59 s | 1.39 s |
| Nev-ranked → Nesso3 | 2 | 2 | 1.61 s | 1.56 s |

The same four cases passed in both modes. This demonstrates working bilingual
examples, with **no observed ranking benefit on this small set**. The Italian
invoice answer had the correct filename but a duplicate call. English guide
lookup looped into invalid order calls; payment requests also attempted
unrelated calls with invented identifiers. All outputs are retained.

Sixteen runs took 25.5 seconds after warmup and allocated at most 2.50 GiB GPU
memory. Shared-GPU wall times include Nev routing in the ranked mode; they
exclude model loading and real API latency. No weights were changed. This
simpler set differs from the historical 80-request pilot: do not compare its
pass fraction with the Nesso2 table as a model improvement. Nesso2 was not rerun
on these eight prompts. See the runnable recipe in `experiments/hybrid_agent/`
and complete evidence in `docs/nesso3/`.

### Nesso3: prompt versus application controller

Three policies were compared on eight previously inspected requests and 16
fresh authored requests fixed before inference. All kept Nev enabled and the
same four mock tools. The short prompt said to use the necessary tool once and
answer from its result. It introduced regressions and is not recommended as a
general fix. The controller uses the original prompt and writes the final
answer from the observation in application code.

| Policy | Complete answers, fresh EN /8 | Fresh IT /8 | Total /16 | Median EN | Median IT |
|---|---:|---:|---:|---:|---:|
| Original loop | 6 | 5 | 11 | 1.85 s | 1.37 s |
| Short prompt | 6 | 4 | 10 | 1.26 s | 1.44 s |
| Single-read controller + templates | 8 | 8 | 16 | 0.73 s | 0.76 s |

Completion requires correct executed actions and all requested facts; the
assistant reviewed all 72 outputs against the requests and mock results (not
independent human grading). Three automatic anchor-check passes omitted payment
entries and were marked incomplete in this table. Rejected extra calls remain
visible: the stricter metric penalizing any generated extra call scored 9/16,
9/16 and 12/16 respectively. Thus **16/16 is an application completion result,
not perfect raw generation**. The controller also completed all eight development
examples; the original loop completed five and the prompt completed three.

The fresh set is small, uses similar mock response shapes, and is entirely in
scope for single-read handling. It does not establish automatic scope detection,
production reliability or an incremental gain from Nev. Nine boundary/scoring
unit tests passed locally and on the A100. Full commands, failure patterns,
limits and evidence are in the [controller report](docs/nesso3/CONTROLLER_REPORT.md),
with [all readable traces](docs/nesso3/CONTROL_TRACES.md).

### Merged workflow: regression and multi-step checks

The new `workflow` entry point was checked on 60 EN/IT requests, including all
24 earlier single-read cases. The original free loop also ran on the 36 new
requests, producing 96 saved records in total.

| Application-contract check | English | Italian |
|---|---:|---:|
| Earlier single-read outputs preserved | 12/12 | 12/12 |
| New single reads completed | 4/4 | 4/4 |
| New 2–4-step reads completed in order | 6/6 | 6/6 |
| Unsupported/mixed requests refused without execution | 4/4 | 4/4 |
| Missing/conditional/unknown/ambiguous requests deferred without execution | 4/4 | 4/4 |

All earlier first-generation calls, executed calls and final answers matched the
previous single-read run exactly. Warm median latency for new multi-step reads
was 1.84 s EN / 2.22 s IT on the shared A100. All 16 boundary/scoring unit tests
passed locally and remotely, including aborting preflight without partial
execution and stopping after tool failures.

These are results for a **declared grammar and mock tools**, not general model
accuracy. New examples test that grammar; the earlier examples informed its
design. The code constructs the plan and formats final facts. Unknown wording
can defer even where a generative answer would be useful. The baseline also
showed concrete unsupported-action errors, including claiming an email was sent
after only retrieving an invoice. Full comparison metrics and interpretation
limits are in the [workflow report](docs/nesso3/WORKFLOW_REPORT.md), with
[all 96 readable traces](docs/nesso3/WORKFLOW_TRACES.md).

### Domain-independent function calling: 216-trial pilot

The abstract controller received schemas at runtime for notes, sensors and media;
it used no application grammar, gold plan, or answer template. We froze 54 paired
requests (27 EN/27 IT) and ran four configurations. Cases included dependent
lookup→read operations, missing arguments, unavailable actions and renamed tools.
All tools were mocks and the models were unchanged.

| Configuration | Exact executed plans, EN + IT | Reviewed complete answers EN | Reviewed complete answers IT |
| --- | ---: | ---: | ---: |
| Nesso3, original order | 16/36 | 5/18 (27.8%) | 4/18 (22.2%) |
| Nesso3, shuffled order | 21/36 | 7/18 (38.9%) | 6/18 (33.3%) |
| Nev-ranked → Nesso3 | 22/36 | 7/18 (38.9%) | 6/18 (33.3%) |
| Nev ranking + execution gate | 22/36 | 7/18 (38.9%) | 6/18 (33.3%) |

These denominators cover supported requests; missing-value, unsupported-action
and no-tool cases are reported separately. Complete answers require correct
execution and grounded final facts. An assistant review corrected nine raw
keyword-score false positives: wrong temperature units and artist/ID values
presented as track titles. This is a small authored pilot, not broad accuracy.

Nev-ranked execution was correct on **12/12 original-name single-operation
requests**, but only 8/12 final answers were complete and grounded. It completed
2/6 original-name dependent requests and 1/6 parallel requests. One successful
Italian trace was `find_sensor(room="Studio")` → returned ID `S-4J9` →
`read_sensor(sensor_id="S-4J9")` → “La temperatura è 21.5°C.” Other traces confused
titles with IDs, repeated calls, omitted fields, or falsely claimed an unavailable
action had completed after schema validation rejected it.

**Interpretation:** ranking improved exact execution over the original order,
but complete answers tied shuffled order. The proposed gate blocked no calls and
did not improve capability refusals. This supports more work on schema-driven
function calling, not a claim of reliable general autonomous behavior.

All 216 trials took 321 seconds. Nev-ranked median latency was 1.28 s EN / 1.30 s
IT on the shared A100; peak PyTorch allocation was 2.53 GiB with Nesso BF16 and
Nev FP32. These are not on-device measurements. No mobile runtime or quantization
was tested. The [full abstract-agent report](docs/abstract-agent/REPORT.md)
includes all comparisons, successful and failed examples, raw results and
readable traces. Its next proposed experiment is a generic structured result and
execution-status stage to reduce factual errors without adding domain templates.

### Nesso2 + Nev: historical first agent comparison

A runnable prototype combines generative
`giux78/nesso2-0.4B-agentic-v2` with Nev v3. Nev ranks four available tools;
Nesso generates the function name and arguments, receives a simulated tool
result, and attempts a final response. Python enforces schema and argument
checks. All tools are local read-only simulations, with no real account actions.

The corrected compact-schema pilot used **80 authored requests, 40 EN / 40 IT**,
covering straightforward requests, distracting details, two-step workflows,
missing arguments, no-tool questions and unsupported actions. Each was run with
three modes on the shared A100. Both models remained resident; inference used
BF16 Nesso and native FP32 Nev. All model revisions, requests, labels and traces
are retained. No model weights were trained or changed.

| Mode | Strict checks EN /40 | Strict checks IT /40 | Total /80 | Median EN | Median IT |
|---|---:|---:|---:|---:|---:|
| Nesso alone | 9 | 14 | 23 | 1.97 s | 1.55 s |
| Nev-ranked → Nesso | 12 | 15 | 27 | 1.51 s | 1.59 s |
| Nev top-2 → Nesso | 6 | 11 | 17 | 1.52 s | 1.59 s |

“Strict checks” means exact emitted calls and arguments, no extra calls,
a final response containing required result anchors, sequential turns where
requested, and clarification/refusal heuristics. It is a **mechanical proxy**,
not human-verified task accuracy. Manual review found replies that passed the
checks but added unsupported or imprecise statements. This small, partly
templated pilot is not a representative benchmark. Timing includes the measured
Nev routing cost where used and local mock-tool overhead; real API latency is absent.

Ranking achieved six paired wins and two losses versus Nesso alone: **four net
additional passes (+5 percentage points)**. This is a small directional result,
not evidence of a reliable general improvement. Importantly, Nesso alone had
better **first-call exactness** on the 28 tool requests per language: 22/28 EN
and 26/28 IT, versus 20/28 and 24/28 with ranking. Ranking helped more runs finish
after the initial call; it did not improve first-call accuracy here.

Hard top-2 selection lost six passes overall and excluded a required tool on
all four Italian two-step requests. Every mode failed the strict two-step
checks in both languages. Common failures were repeating calls after a valid
observation, adding output fields to new arguments, and failing to finish with
a grounded answer. Keep all tools available in the current prototype and treat
Nev's ordering as experimental advice.

**A material integration finding:** the initial run exposed JSON Schema
`pattern` and `additionalProperties` fields to Nesso. It passed only 4/80 checks
alone, 4/80 with ranking and 14/80 with top-2. Removing those fields from the
model-visible schemas, following the model card's minimal format, produced the
table above. The same validation remained in Python. Thus the first apparent
shortlisting gain was not a sound recommendation. Both protocol runs are
retained. The compact follow-up reused the same cases after inspecting the first
run, so it is a development comparison; a fresh held-out evaluation is still needed.

The corrected 240-run comparison took **452 seconds**, with peak allocated GPU
memory **2,572 MiB (2.51 GiB)** for the resident models and inference. The first
protocol took 853 seconds. The next experiments should separate call generation
from answering after an observation, compare Nev ordering with randomized or
simple deterministic ordering, and evaluate on new bilingual requests before
claiming an agent-level gain.

Reproducible code and exact methodology are in `experiments/hybrid_agent/`;
complete corrected traces and analysis are in
`docs/nesso2/evidence/a100-hybrid-compact-pilot.json` and
`a100-hybrid-compact-analysis.json`. The original protocol and smoke records
remain alongside them. The source used for the first run is Git commit
`1cab00d`; the compact run used `9997ec5`. The prototype now defaults to compact
schemas; passing `--schema-style validated` reproduces the old schema display.

### A100 inference speed: brief shared-GPU measurement

On 2026-10-12, a fresh isolated Python 3.12.13 environment loaded both releases on an NVIDIA A100 80GB PCIe with driver 575.57.08 and PyTorch 2.10.0+cu126. Another compute process was active throughout the timing samples. These are **shared-GPU observations**, not idle-GPU throughput or a controlled v2-versus-v3 speed comparison.

Each row measures 20 sequential bilingual requests after warmup. The one-question workload asks only routing; the four-question workload asks all four decisions over the same states. Timings include validation, tokenization and synchronized GPU execution, with batch size 1 and cached inference. There is no HTTP overhead, model download or text generation.

| Variant | Arithmetic | Questions/request | Median | p95 | Requests/s |
|---|---|---:|---:|---:|---:|
| v2 | FP32 | 1 | 85.8 ms | 100.4 ms | 11.50 |
| v2 | FP32 | 4 | 154.8 ms | 188.0 ms | 6.47 |
| v2 | BF16 autocast | 1 | 63.8 ms | 65.0 ms | 15.87 |
| v2 | BF16 autocast | 4 | 60.5 ms | 91.0 ms | 14.87 |
| v3 | FP32 | 1 | 77.2 ms | 98.5 ms | 13.30 |
| v3 | FP32 | 4 | 144.1 ms | 185.9 ms | 6.76 |
| v3 | BF16 autocast | 1 | 79.8 ms | 82.6 ms | 12.84 |
| v3 | BF16 autocast | 4 | 99.1 ms | 103.6 ms | 10.20 |

Loading the local model took 2.70 seconds for v2 and 1.93 seconds for v3, excluding Python imports and download. The first FP32 request after each load took 382 ms and 124 ms respectively; these are separate from the warmed samples. Peak allocated PyTorch GPU memory was 1,895 MiB (about 1.85 GiB), with 1,982 MiB reserved. CUDA/driver allocations and the other workload are additional. TF32 was disabled and CPU threads were set to four.

All **160 FP32 decisions** in the two full four-question panels matched the earlier LUMI predictions. BF16 autocast changed **0/100 decisions per model** across the one- and four-question workloads in this small check. This does not establish precision equivalence on other examples or remove the previously observed policy-following errors.

BF16 was faster for the four-question requests in this run. Changing background load prevents treating the measured differences as a stable speedup, and 20 samples provide only a rough p95. `benchmark_latency.py` saves individual timings, input hash, GPU-load samples, memory measurements and changed decisions. It measures requests and decisions per second; tokens/second is not the output metric for this non-generative model.

## 4. Harder examples: what the easy demo concealed

A parcel message routed to “shipping” with a high probability establishes that loading and inference work. To examine more useful behavior, we added **20 authored requests**, ten in each language, each asking four decisions together. Five paired scenarios change exactly one verified fact while keeping the message and policy fixed.

| Scenario pair | Single changed fact | Decision that should change |
|---|---|---|
| Return window | Product delivered 29 vs 31 days ago | Approve vs reject reimbursement |
| Security override | Unauthorized activity unconfirmed vs confirmed | Account vs security routing; urgency and escalation |
| Duplicate payment | Not yet refunded vs already refunded | Approve vs reject reimbursement |
| Delivery deadline | 25 vs 23 hours remaining | Priority vs urgent |
| Repeated contact | Two vs three unsuccessful previous contacts | No escalation vs escalation |

Messages contain distracting secondary requests, resolved complaints, suspicion distinguished from confirmed findings, and angry wording that should not change the policy. Expected answers were fixed before inspecting either model. Only the request enters the model; the answer key and pair metadata do not.

Both models were tested in native cached FP32 inference on the released HF revision:

| Correct answers on this small diagnostic | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|
| Routing | 7/10 | 5/10 | 9/10 | 5/10 |
| Refund | 8/10 | 8/10 | 8/10 | 8/10 |
| Urgency | 4/10 | 6/10 | 6/10 | 5/10 |
| Escalation | 8/10 | 8/10 | 8/10 | 8/10 |
| All four decisions correct | 2/10 | 2/10 | 2/10 | 0/10 |
| Changed decision correct on both sides | 0/7 | 1/7 | 1/7 | 0/7 |

**Both models answered false for every refund and escalation question.** The 8/10 counts merely equal the always-no baseline and miss every positive case. Always choosing routine urgency would score 5/10, and always choosing shipping would score 4/10, on this particular fixture.

Concrete v3 failures make the limitation clearer:

- After three unsuccessful English support contacts, the supplied rule requires escalation. V3 declines with probability **0.9885**.
- For a confirmed duplicate English charge that has not been refunded, the policy requires reimbursement. V3 declines with probability **0.8869**.
- For an Italian unopened-product return at 29 days, v3 denies reimbursement and routes to shipping. Changing 29 to 31 days does not repair its interpretation.

These cases expose weaknesses in applying the supplied policies and separating relevant facts from distracting wording. They are small, correlated, authored diagnostics, conceptually related to practical training tasks—not representative accuracy estimates. They were not used to train these released models. If used in future training, they must not continue to be reported as fresh independent tests.

## 5. Calibration, export, and verification

Temperature fitting and confidence-policy selection used distinct splits. The stored temperatures are **0.7320428479728127 for v2** and **0.8122523963562355 for v3**. Neither variant qualified for the declared confidence policy, which targeted at most 10% error with at least 30 accepted examples per language. The runtime still returns a decision. Temperature scaling does not implement abstention or make the probability a correctness guarantee.

FP32 merging and isolated reload were checked independently:

| Check | V2 | V3 |
|---|---|---|
| Maximum merge probability difference | 3.40e-6 across 16 questions | 4.62e-6 across 40 questions |
| FP32 argmax changes in merge check | 0 | 0 |
| Isolated same-dtype reload | Exact | Exact |

Small FP32 merge differences do not imply identical BF16-autocast benchmark answers. V3's merged model changed 12 of 1,024 predictions on the new synthetic test relative to its adapter. The release tables therefore score the actual exports separately.

The packaged runtime preserves 17 frozen source files identified by SHA-256. An isolated installation passed offline inference for both languages and variants. Later, both variants were downloaded from the private HF repository and tested on LUMI again; all four original smoke-example answers and probabilities matched the local-export results exactly.

The immutable model revision is:

```text
giux78/nev@c5c84121263b423f8846811a24790ab96e66cee3
```

HF privacy, remote weight sizes, and LFS SHA-256 were verified after upload. The evaluated core model files were unchanged. Weights are stored on Hugging Face; this repository contains source, recipes, descriptions, result evidence, and provenance.

## 6. What a decision model does

An application supplies a state, one or more questions, instructions, and the allowed answers. Nev returns a typed decision and a probability distribution over those answers.

| Question type | Meaning | Output |
|---|---|---|
| `choice` | Choose among named runtime options | Selected option ID and its distribution |
| `noul` | Make a boolean decision | `decision`, `p_true`, and false/true probabilities |
| `score` | Choose an ordered level | Selected level, expected level, and level probabilities |

For example, one support request can ask four questions together: which department should handle it, whether the stated refund policy applies, how urgent it is, and whether it should be escalated. The application supplies the policy and option descriptions. The available categories are not restricted to a fixed classification vocabulary learned during training.

The decoder represents the state and question branches. A shared **256-dimensional pointer head** scores the supplied options using representations of the decision position and each option endpoint. A softmax produces the distribution. Decision training updates LoRA adapters and the head; release exports merge the adapters into the decoder.

The ordinary language-generation head is not part of this interface. Nev does not generate a textual explanation or perform a tool action. The application receives the decision and decides what to do with it.

The runtime supports three execution forms:

- **Packed:** state and question branches share a pass with a mask that separates the branches; used in training and practical evaluation.
- **Rows:** each question has a causal row containing its state and branch; used for the external subset evaluations.
- **Cached:** encode the state once and reuse its prefix cache for question branches; used by the native examples.

These paths are intended to compute the same decision function, but arithmetic and precision can change close answers. Benchmark scores below identify the evaluated artifact and execution conditions.

## 7. The complete lineage

Nev is the decision-model stage of the **mii-llm Zagreus → Nesso2** lineage: a small language-model foundation trained from scratch, developed into an Italian/English agentic model, and then adapted to make structured decisions over options supplied by an application.

The project follows the whole path from that foundation to two released decision variants. It preserves **50% English / 50% Italian record and loss weight in every decision-training update**, uses the roughly 0.4B-parameter Nesso2 backbone, and builds on Kev's decision-model implementation. The objective is to understand how much useful decision behavior this small bilingual model can learn, how specialization changes its abilities, and where it still fails.

```text
Zagreus-0.4B-ita — foundation pretrained from scratch
    │
    ├─ Knowledge continued pretraining
    ├─ Context extension to 32k tokens
    └─ Bilingual agentic supervised fine-tuning
          │
          ▼
Nesso2-0.4B-agentic — the pinned parent of Nev
          │
          ├─ Kev compatibility and decision-head integration
          ├─ Translation, teacher pilots and data review
          └─ Full balanced bilingual decision training: 178,300 updates
                │
                ├─ 142k: original development-selected control
                └─ 74k: starting point for practical adaptations
                      │
                      ├─ Practical v1: exploratory experiment
                      └─ Practical v2: selected at +256 → released v2
                            │
                            └─ Focused v3: selected at +512 → released v3
```

The [pinned Nesso2 model card](https://huggingface.co/mii-llm/nesso2-0.4B-agentic/blob/86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041/README.md) reports the earlier stages: Zagreus was pretrained from scratch on about one trillion tokens, approximately 400B English, 400B Italian and 200B code. Sources included FineWeb, Italian FineWeb-2, Italian FinePDFs and StarCoder Data. That work used Nanotron on 64 A100 GPUs at Seeweb. Knowledge continued pretraining used Italian/English Wikipedia and augmented question-answer data, followed by 32,768-token context adaptation and bilingual agentic SFT with TRL/FSDP.

The foundation uses a Llama-style architecture and Llama-3 tokenizer. **“From scratch” describes the foundation's learned weights.** Nev builds on those weights through Nesso2, with Kev supplying the decision-model framework. Earlier-stage details above come from the parent card; the experiment records in this repository document the subsequent decision-model work on LUMI.

The exact Nesso2 parent is:

```text
mii-llm/nesso2-0.4B-agentic
86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041
```

The distinction between stages matters. The foundation's English/Italian/code pretraining mixture is different from Nev's exact 50/50 English/Italian decision-training balance. Nesso2's advertised 32k context also does not override the smaller input limits enforced by the decision runtime.

## 8. Making Nesso2 work with Kev

The original feasibility work extended Kev's decoder support to the Llama-style Nesso2 backbone and checked its tokenizer and decision delimiters. It preserved the supported decoder and added bilingual data/training behavior.

Before the full run, checks covered rendering, branch isolation, packed/rows/cached consistency, finite nonzero adapter/head updates, export and reload. A small memorization experiment established that learning occurred. A resume experiment reproduced all **452 trainable tensors exactly**. These checks helped establish implementation correctness; the later held-out evaluations measured how far that learning generalized.

All decision-model training and evaluation described here ran on **LUMI AMD MI250X / ROCm**. The earlier foundation and Nesso2 stages used the separate infrastructure described by the parent card.

## 9. Building and reviewing the bilingual corpus

The full reviewed decision-training corpus contained **713,198 records: 356,599 English and 356,599 Italian**.

| Source family | Decision behavior represented |
|---|---|
| AG News and TREC | Topic and question classification |
| Banking77 | Banking intent classification |
| BoolQ | Boolean question answering |
| MNLI | Natural-language inference |
| SST-5 | Ordered sentiment decisions |
| Generated rules | Executable policy and compositional labels |
| Custom support tickets | Application-style decisions |

About **72% of the corpus was MNLI**. Exact language balance therefore did not imply balanced task exposure. This distinction became important when later practical tasks remained weak despite strong original-domain results.

English/Italian counterparts retained matching answer identities and supervision. Source grouping and split separation preceded translation. Reviews filtered conflicting duplicate labels, malformed translations, and schema/context failures, with paired exclusions so one language did not silently receive different examples.

Italian text was translated using the existing LUMI vLLM setup with **Qwen3.6-35B-A3B**, pinned to `995ad96eacd98c81ed38be0c5b274b04031597b0`, and translation prompt `vllm-quoted-fewshot-v3`. An earlier translation artifact was rejected and retained for diagnosis.

The translator supplied Italian wording. Gold decision labels remained the supervision for the full run. Translation quality was reviewed but is not equivalent to a fully native, independently authored Italian corpus.

### Why the full run used gold labels

A representative pilot used 1,684 bilingual training records and compared gold-only training with teacher distillation. Teacher selection considered Nesso and Qwen alternatives; the selected Nesso teacher supplied soft targets where its interface could admit the question. Banking77 remained gold-only because that interface could not handle all 77 options.

On the full pilot test, with 341 questions per language:

| Pilot student | English | Italian |
|---|---:|---:|
| Gold-only | 38.4% | 36.4% |
| Distilled | 37.0% | 34.6% |

The teacher was much stronger on common eligible questions, but the tested distillation recipe did not transfer that advantage to the student. Paired intervals for the difference included zero. The full decision run therefore used gold labels. This experiment does not settle whether a different teacher, objective, or data mixture would help.

## 10. Full decision training and the first evaluation gap

| Setting | Full-run configuration |
|---|---|
| Initialization | Pinned Nesso2-0.4B-agentic decoder |
| Trainable components | LoRA adapters and shared decision head |
| LoRA | Rank 16, alpha 32, dropout 0.05 |
| Target projections | q/k/v/o and gate/up/down |
| Decision-head dimension | 256 |
| Optimizer and schedule | AdamW, OneCycle |
| Learning rate / weight decay | 5e-5 / 0.01 |
| Microbatch / accumulation | 1 / 8 |
| Language sampling | Four English and four Italian records per full eight-record update |
| Precision | FP32 parameters, BF16 autocast |
| Seed / epochs | 0 / 2 |
| Completed updates | 178,300 |
| Original development selection | Checkpoint 142k |

The language constraint is on **records and loss weight**, not equal token counts. Italian and English versions can tokenize to different lengths.

The original 142k-selected export reached **88.29% English / 86.87% Italian** on its original training-domain test, and **59.30% / 60.70%** on a separate unseen-source panel. These are historical control results on those mixtures, not scores for either released variant.

External MMLU, HellaSwag, ARC, ANLI, CLINC and When2Call subsets showed a much larger gap. This motivated the practical adaptations. Original checkpoint **74k** became their starting point; the original development-selected **142k** was retained as a control. Repeated external inspection influenced the experiment direction, so those external panels are reused diagnostic evidence rather than fresh independent release-selection tests.

## 11. The adaptation experiments

### Practical v1: an improvement that exposed a confidence failure

Starting from 74k, 512 additional updates on 4,096 records improved the synthetic practical final test:

| Model on the v1 practical test | English | Italian |
|---|---:|---:|
| Original 74k | 33.01% | 31.64% |
| After 512 updates | 40.23% | 35.35% |

Development improved more than the final test. Training, development and calibration shared narrow instruction wording, while the final test changed it.

A threshold of 0.7 selected on familiar wording accepted 55.08% of English and 40.63% of Italian final cases, with error rates of **59.57% and 67.31%** among accepted decisions. The confidence policy failed. This led to separating instruction wording as well as fact configurations in the next experiment.

### Practical v2: separate wording, replay, and development selection

V2 restarted from **original 74k**, independently of v1. Its 8,192 training records comprised 4,096 new practical examples and 4,096 original-data replay records, with exact EN/IT balance.

Training, development, temperature fitting, confidence-policy selection, and final testing used disjoint instruction banks and fact configurations. Previous v1 configurations were excluded. The adaptation used a learning rate of 1e-5, accumulation 8, 32 warmup updates, and evaluation every 128 updates. Original-domain retention constraints limited NLL increase to 0.05 and accuracy loss to two percentage points.

Development selected **+256 updates**. The selected adapter scored **43.75% EN / 45.90% IT** on 2,048 final practical requests. Laya scored **43.65% / 39.06%** on those same requests; the English difference was only one correct answer. The actual v2 export was subsequently evaluated independently and scored **44.14% / 45.51%**.

No confidence threshold qualified under the declared policy. V2 is retained for its measured relative strengths, especially refund decisions and Italian urgency compared with v3.

### Focused v3: stronger routing with measurable forgetting

V3 initialized from the selected v2 checkpoint. Its 8,192-record mixture was:

| Component | Records |
|---|---:|
| New routing examples | 1,024 |
| New synthetic 16-intent examples | 1,024 |
| Banking77 replay | 3,072 |
| Other original-data replay | 3,072 |

Each update remained half English and half Italian. Selection applied separate original-domain and practical-v2 development retention checks. The fixed selection was **+512 updates**. Training stopped at +896; later +640, +768 and +896 checkpoints failed retention eligibility.

The selected v3 adapter and export were evaluated on a new synthetic 16-intent/routing test; their results are included in the evaluation section above.

A later regression audit showed that routing gains accompanied refund losses and lower Italian urgency accuracy. Aggregate retention checks had not protected every individual task. That is why both variants are retained. No confidence threshold qualified for v3 either.

## 12. Rebuilding the decision training

The practical synthetic generators run with the Python standard library:

```bash
python tools/generate_synthetic.py --variant v2 --out data-v2-synthetic
python tools/generate_synthetic.py --variant v3 --out data-v3-synthetic
```

Use new output directories. The generators reproduced all eight recorded held-out split hashes: development, temperature fitting, confidence-policy selection and test for each variant. Pair validation checks one English and one Italian record with matching supervision.

Generated training files contain the new synthetic data only. Reconstructing the actual 8,192-record adaptation mixtures also requires the recorded original-data replay; the commands above do not recreate or redistribute the third-party base corpus.

The complete decision-stage recipe is:

1. Prepare source datasets at their recorded revisions, deduplicate, and enforce grouped split separation before translating.
2. Create and review Italian counterparts with the pinned translation setup, preserve gold labels, and apply paired exclusions.
3. Train the reviewed 713,198-record corpus using the full-run settings above. Preserve intermediate checkpoints, especially 74k and the independently selected 142k control.
4. Build v2 with disjoint practical instruction/fact splits and replay. Initialize from 74k, apply its development retention checks, and retain the full candidate-selection history. The observed selection was +256.
5. Build v3's routing/16-intent mixture plus Banking77 and broad replay. Initialize from selected v2, apply both development checks, and preserve rejected checkpoints in the history. The observed selection was +512.
6. Fit temperature and confidence policy on distinct splits; record that no threshold qualified. Export merged FP32 weights, verify merge and isolated reload, and evaluate the actual export independently.

Training for exactly the selected number of updates without reproducing selection is not the same experiment. Source manifests, recipes, retained controls and rejected candidates are part of the record.

The operational recipe files are `recipes/base-recipe.json`, `recipes/nesso2-practical-v2.json` and `recipes/nesso2-focused-v3.json`. The data revisions and review exclusions are in `recipes/data-manifest.json`; split hashes are in `recipes/synthetic-split-hashes.json`. Frozen implementations live in `recipe-source/`, and historical LUMI launchers in `experiments/lumi/`.

**A portable end-to-end rebuild from an empty machine is still unfinished.** Operational training wrappers expect the existing LUMI base-run tree and metadata. The repository provides the recorded recipes, implementations and verified inference artifacts; it does not claim that the complete foundation pretraining or decision-training pipeline has been independently rebuilt elsewhere.

## 13. What this work establishes, and what comes next

The project demonstrates a complete path from a foundation pretrained from scratch through bilingual agentic post-training to a functioning typed decision model. Within the decision stage, it documents learning, specialization, forgetting, export behavior, and substantial remaining weaknesses in policy-sensitive decisions.

The strongest observed development was v3's routing and synthetic 16-intent improvement. The central limitation is that success on a familiar task mixture and high softmax confidence do not establish reliable decisions under changed wording or interacting policies. The later contrast examples make that limitation visible without hiding it behind a favorable aggregate score.

The next experiments should use broader instruction wording and task balance, explicit positive/negative contrast pairs, and **task-level** development retention checks. Any examples used to improve the model must be separated from new independent tests. A Transformers loading wrapper would improve usability, but would not by itself fix the observed decision errors. These are directions for future work, not completed improvements.

The scope remains a small bilingual research model. External subsets have been reused; Italian text is partly synthetic; pretraining exposure is unknown; no confidence threshold qualified; and neither real-traffic reliability nor CPU/mobile or quantized performance is established here. Cross-platform evidence is limited to the recorded LUMI checks and the small shared-A100 inference test above.

## 14. A few deeper records

The main reading path ends here. For auditing or rebuilding specific details:

- [Chronological experiment log](docs/nesso2/EXPERIMENT_LOG.md): launches, controls, failed attempts, checkpoint selection, release work and later diagnostics.
- [Machine-readable export comparison](export-comparison.json): exact task denominators, common-support comparisons and source provenance.
- [Evidence directory](docs/nesso2/evidence): detailed training, regression, export, publication and harder-scenario reports. Historical focused documents remain available as supporting records.

Kev attribution, Nesso2 provenance and upstream notices are retained in [NOTICE](NOTICE). Software and declared parent-model licensing are Apache-2.0; see [LICENSE](LICENSE). Source datasets retain their own terms. Original third-party training and benchmark texts and model weight binaries are not checked into this code repository.
