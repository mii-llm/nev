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

## Load a variant

Authenticate with an account that has access to this private repository. Install the accompanying frozen runtime and its dependencies as described in the [inference guide](https://github.com/mii-llm/nev/blob/main/INFERENCE.md).

```bash
# From the mii-llm/nev checkout, after installing the runtime and logging in:
python examples/hf_decide.py --variant v3 --download-only
python examples/function_calling_demo.py --variant v3 --language both
```

Pin `revision` to a commit for reproducible downloads. The example uses native cached FP32 serving; benchmark tables used documented rows/packed BF16-autocast paths. Close decisions can change with execution form and precision. Both packaged variants passed offline reload and English/Italian inference checks on LUMI ROCm. A fresh A100 CUDA environment also passed the recorded inference checks. Quantization is not validated here.

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

The function example selects among `get_order_status`, `get_invoice`,
`search_help_center`, `list_transactions` and `no_tool`. The default English
request is “I need a copy of the invoice for order ORD-2048 to attach to my
expense report. Please retrieve the document.” Its Italian counterpart is
“Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota
spese. Recuperate il documento, per favore.” Both selected `get_invoice`.

The application then constructs this dry-run call:

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

Four representative pairs from that curated file are shown below. Probabilities
are v3's actual assigned probabilities on the candidate run, rounded to one
decimal percent; they are not calibrated reliability estimates.

**Routing a duplicate-charge request**

- **EN:** “My monthly subscription was charged twice on the same day. I can see both completed payments on my statement and need this checked.” → `billing` (99.9%).
- **IT:** “Il mio abbonamento mensile è stato addebitato due volte nello stesso giorno. Vedo entrambi i pagamenti completati sull’estratto conto e vorrei una verifica.” → `billing` (100.0%).

**Selecting an invoice-retrieval function**

- **EN:** “I need a copy of the invoice for order ORD-2048 to attach to my expense report. Please retrieve the document.” → `get_invoice` (99.8%).
- **IT:** “Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota spese. Recuperate il documento, per favore.” → `get_invoice` (95.5%).

**Classifying a technology news brief**

- **EN:** “Researchers demonstrated a new optical chip that processes signals using light. The laboratory prototype could reduce the energy required by future computers.” → `science_technology` (99.7%).
- **IT:** “I ricercatori hanno presentato un nuovo chip ottico che elabora segnali usando la luce. Il prototipo di laboratorio potrebbe ridurre l’energia necessaria ai computer del futuro.” → `science_technology` (99.6%).

**Recognizing a failed cash withdrawal**

- **EN:** “The ATM debited my account, but the machine did not dispense any cash. How do I report the failed withdrawal?” → `cash_withdrawal` (100.0%).
- **IT:** “Il bancomat ha addebitato il mio conto, ma non ha erogato contanti. Come posso segnalare il prelievo non riuscito?” → `cash_withdrawal` (100.0%).

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
