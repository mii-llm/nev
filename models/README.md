---
language:
- en
- it
license: apache-2.0
base_model: mii-llm/nesso2-0.4B-agentic
tags:
- decision-model
- bilingual
- research
inference: false
---

# Nev — bilingual Nesso2 decision models

Two English/Italian research variants built using Kev on the ~0.4B Nesso2 backbone. Both support categorical (`choice`), boolean (`noul`) and ordinal (`score`) decisions over supplied criteria. Every training update is half English and half Italian. They are structured decision models, not ordinary text-generation checkpoints.

| Variant | Folder/card | Observed relative strengths | Limitations |
|---|---|---|---|
| V2 Practical | [v2](v2/README.md) | Refund rules and Italian urgency | Weaker routing than v3 |
| V3 Routing | [v3](v3/README.md) | Routing, plus gains on the new synthetic 16-intent task | Refund and Italian urgency regressions; weak 151-option CLINC intent classification |

The exact identities are original 74k +256 updates (v2) and selected v2 +512 (v3). These were fixed before the final evaluations. Both folders contain standalone FP32 merged weights, the tokenizer, decision head, exact runtime, artifact checksums and model-specific conversion/evaluation metadata.

## Install and run Nev

**Two repositories, two purposes:**

- **Hugging Face — [mii-llm/nev](https://huggingface.co/mii-llm/nev/tree/main):** this page hosts the model weights, tokenizer and decision head in the `v2/` and `v3/` folders. Downloads are public; no Hugging Face account or login is needed.
- **GitHub — [mii-llm/nev](https://github.com/mii-llm/nev):** clone this repository to get the Python runtime (`runtime/`) and runnable examples (`examples/`). The commands below install that runtime and download the Hugging Face weights automatically.

### 1. Install the Python runtime

Use **Python 3.12**. This quick start targets a Linux machine with an NVIDIA GPU. The function-selection and reference-example runners need at least **4 GiB of free GPU memory**. For a Mac CPU, use the separate [Nev GGUF instructions](https://huggingface.co/mii-llm/nev-gguf).

```bash
# Clone the CODE repository from GitHub, not the model repository from HF.
git clone https://github.com/mii-llm/nev.git
cd nev

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "torch>=2.10,<2.11"
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime

# Confirm that PyTorch can see your GPU.
python -c "import torch; print('GPU available:', torch.cuda.is_available())"
```

If this prints `False`, install the [PyTorch build for your hardware](https://pytorch.org/get-started/locally/) before continuing with the GPU examples. The `decision_model` Python module comes from the `./runtime` installation above.

### 2. Run your first English and Italian decisions

Run these commands from the **GitHub checkout directory `nev/`**, with `.venv` activated:

```bash
# Downloads v3 from Hugging Face on the first run, then evaluates both languages.
python examples/hf_decide.py --variant v3 --language both --device cuda

# A function-selection example using your own request file.
python examples/hf_decide.py --variant v3 --device cuda \
  --request examples/request-function-it.json

# Show invoice-function selection in both languages and an application-built call.
python examples/function_calling_demo.py --variant v3 --language both
```

The first command caches the pinned v3 files from `mii-llm/nev` on Hugging Face. The third command reuses that cache. There is no need to download weights manually or clone the Hugging Face repository. To try v2, replace `--variant v3` with `--variant v2`; run the first command for v2 before its function demo.

The output is JSON: `answers` contains each selected label and its option probabilities. In the function demo, `model_selected_function` is Nev's prediction; `application_built_call` contains arguments supplied by the application. **Nev selects an option; it does not generate arguments or execute a tool.** The bilingual examples and their recorded outputs appear below.

To define a different task, copy a request file and edit its `state`, question `instructions`, and `criteria` (the allowed labels and their descriptions), then pass its path with `--request`. After the initial download, add `--offline` to `hf_decide.py` to reuse cached weights without contacting Hugging Face.

### 3. Use Nev in your Python application

After the same installation, download a variant and load it with the `decision_model` runtime:

```python
from pathlib import Path
from huggingface_hub import snapshot_download
from decision_model import DecisionModel

variant = "v3"  # or "v2"
folder = Path(snapshot_download(
    repo_id="mii-llm/nev",                 # Hugging Face model repository
    revision="c5c84121263b423f8846811a24790ab96e66cee3",
    allow_patterns=[f"{variant}/**"],
    token=False,
)) / variant
model = DecisionModel.from_pretrained(folder, device="cuda")

result = model.evaluate(
    state="Mi serve la fattura dell'ordine ORD-2048.",
    questions={"action": {
        "type": "choice",
        "instructions": "Scegli la funzione adatta alla richiesta.",
        "criteria": {
            "get_invoice": "Recupera la fattura di un ordine.",
            "get_order_status": "Controlla lo stato della spedizione.",
            "no_tool": "Nessuna funzione disponibile è adatta.",
        },
    }},
)
print(result["answers"]["action"])
```

This illustrates the API; it is not an additional benchmark result. You can supply English text and descriptions in the same structure. The runtime supports `choice` (categorical), `noul` (boolean) and `score` (ordered levels).

**Use `DecisionModel.from_pretrained`, not Transformers' `AutoModelForCausalLM`.** Nev needs its trained decision head and input renderer as well as its backbone. The runtime uses Transformers internally. See the [inference guide](https://github.com/mii-llm/nev/blob/main/INFERENCE.md) for artifact layout and execution details.

These examples use native cached FP32 inference; benchmark tables use the documented rows/packed BF16-autocast paths. Close decisions can change with precision. CPU F16/Q8 checks and installation are documented in the separate [Nev GGUF release](https://huggingface.co/mii-llm/nev-gguf).

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
Use the commands immediately below to run them on your GPU. The full
32-candidate record, including unsuccessful cases, is retained in
`docs/nesso2/evidence/a100-reference-candidates.json` in the GitHub repository.

### Bilingual reference examples: routing, function selection and classification

The A100 examples below demonstrate decisions that succeeded in both English
and Italian. They use the exact released v2/v3 weights and native FP32 cached
inference. The complete candidate results, including failures, appear in the
evaluation section; the successful gallery is a **curated demonstration**, not
an accuracy benchmark. No model was retrained for these examples.

After completing the installation above, run from the **GitHub `nev/` checkout**:

```bash
# Cache both variants for the reference runner, which loads offline.
python examples/hf_decide.py --variant v2 --download-only
python examples/hf_decide.py --variant v3 --download-only
mkdir -p results

# Show requests, selected functions, probabilities and application-supplied arguments.
python examples/function_calling_demo.py --variant v3 --language both

# Another function-selection example: searching a help guide.
python examples/function_calling_demo.py --variant v3 --example guide

# Run all 16 curated requests (8 parallel bilingual pairs).
python examples/run_reference_examples.py --variants v2 v3 \
  --cases examples/reference_examples.json \
  --output "results/reference-$(date +%Y%m%d-%H%M%S).json"

# Run all 32 candidates, including unsuccessful examples.
python examples/run_reference_examples.py --variants v2 v3 \
  --output "results/candidates-$(date +%Y%m%d-%H%M%S).json"
```

These reference runners require a CUDA-compatible GPU with at least 4 GiB free memory and load the weights cached by the first two commands. Reports are saved in the `results/` directory you just created. The normal request helper also accepts `examples/request-function-en.json` or `examples/request-function-it.json` with `--request`.

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

## Results on the actual exported weights

Accuracy on the reused practical test, 256 cases per task/language, FP32 parameters with BF16 autocast. These are synthetic tasks, not real customer traffic.

| Task | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|
| Routing | 29.69% | 34.77% | 55.08% | 46.88% |
| Refund decisions | 61.33% | 52.73% | 52.73% | 50.39% |
| Urgency | 33.59% | 42.97% | 33.59% | 37.89% |
| Escalation | 51.95% | 51.56% | 53.52% | 51.17% |
| Overall, 1,024 cases/language | 44.14% | 45.51% | 48.73% | 46.58% |

See the code repository for [all exported-model results and Laya comparisons](https://github.com/mii-llm/nev/blob/main/EXPORT_COMPARISON.md), [adapter results](https://github.com/mii-llm/nev/blob/main/COMPARISON.md), and the [complete experiment narrative](https://github.com/mii-llm/nev/blob/main/EXPERIMENTS.md). The new v3 synthetic 16-intent/routing export scored 54.69% EN / 62.50% IT; that panel is distinct from CLINC and the older practical test. V2 export was not evaluated on that fresh panel.

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

## Recipe, provenance and limits

[Code and build documentation: mii-llm/nev](https://github.com/mii-llm/nev). Recipes, data revisions, translation/review metadata, archived source snapshots, failed experiments and regression tables are retained. Portable synthetic generation reproduces all eight held-out split hashes; a fully portable end-to-end base-data/training launcher remains unfinished.

The parent revision is `86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`. Full training used 713,198 balanced EN/IT records with gold decision labels; Italian was translated using the pinned Qwen3.6-35B-A3B setup. Subsequent adaptations used executable synthetic labels and original-data replay.

No confidence threshold qualified for either candidate. The API still returns a decision; stored temperatures do not guarantee correctness or enforce abstention. External benchmarks are small reused diagnostic subsets, not official full-suite scores; Italian evaluation text is synthetic and partly reviewed. Pretraining contamination is unknown.

Kev and Nesso2 attribution are preserved in NOTICE. The parent revision declares Apache-2.0. Dataset terms remain separate; no original training or benchmark dataset files are included.
