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

## Load a variant

Authenticate with an account that has access to this private repository. Install the accompanying frozen runtime and its dependencies as described in the [inference guide](https://github.com/mii-llm/nev/blob/main/INFERENCE.md).

```python
from pathlib import Path
from huggingface_hub import snapshot_download
from decision_model import DecisionModel

variant = "v3"  # or "v2"
folder = Path(snapshot_download("giux78/nev", allow_patterns=[f"{variant}/**"])) / variant
model = DecisionModel.from_pretrained(folder, device="cuda")
result = model.evaluate(
    state="Il pacco non è arrivato. Vorrei sapere dove si trova.",
    questions={"route": {"type": "choice",
        "instructions": "Scegli il reparto che deve gestire la richiesta.",
        "criteria": {"shipping": "Spedizioni e consegne",
                     "billing": "Pagamenti e fatture",
                     "account": "Accesso e profilo"}}})
print(result["answers"])
```

Pin `revision` to a commit for reproducible downloads. The example uses native cached FP32 serving; benchmark tables used documented rows/packed BF16-autocast paths. Close decisions can change with execution form and precision. Both packaged variants passed offline reload and English/Italian inference checks on LUMI ROCm. Other hardware and quantization are not validated here.

## Recipe, provenance and limits

[Code and build documentation: mii-llm/nev](https://github.com/mii-llm/nev). Recipes, data revisions, translation/review metadata, archived source snapshots, failed experiments and regression tables are retained. Portable synthetic generation reproduces all eight held-out split hashes; a fully portable end-to-end base-data/training launcher remains unfinished.

The parent revision is `86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`. Full training used 713,198 balanced EN/IT records with gold decision labels; Italian was translated using the pinned Qwen3.6-35B-A3B setup. Subsequent adaptations used executable synthetic labels and original-data replay.

No confidence threshold qualified for either candidate. The API still returns a decision; stored temperatures do not guarantee correctness or enforce abstention. External benchmarks are small reused diagnostic subsets, not official full-suite scores; Italian evaluation text is synthetic and partly reviewed. Pretraining contamination is unknown.

Kev and Nesso2 attribution are preserved in NOTICE. The parent revision declares Apache-2.0. Dataset terms remain separate; no original training or benchmark dataset files are included.
