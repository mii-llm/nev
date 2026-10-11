# Nesso2 bilingual decision model — release draft

Release preparation now targets **two variants**. The separate
[v2 Practical card](../../models/v2/README.md) and
[v3 Routing card](../../models/v3/README.md), plus the
[actual export comparison](../../EXPORT_COMPARISON.md),
supersede this single-candidate draft for publication planning.

**Draft, not a released model.** The latest experimental candidate is focused v3
(v2 + 512 updates), with completed [synthetic-test and export results](FOCUSED_V3_RESULTS.md).
The [broader regression audit](V3_REGRESSION.md) is complete: routing improves,
but refund decisions and Italian urgency regress relative to v2. V3 is not an
across-the-board replacement for v2.

## Model and intended use

A small structured-decision model built from `mii-llm/nesso2-0.4B-agentic`, parent
revision `86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`, using the Kev implementation.
The adapter trains attention/MLP LoRA projections plus a 256-dimensional decision
head. Inputs are a state, question instructions and explicit answer options.
Outputs are categorical, boolean or ordinal decisions and probabilities.
This conversion does not add general text generation or reduce the backbone size.

The intended research use is bilingual English/Italian routing, classification
and small operational decisions with supplied criteria. Abstention/human review
must be designed and validated for the actual application.

## Training recipe and provenance

The base run used 713,198 reviewed records (356,599 per language), gold labels,
LoRA rank 16 / alpha 32 / dropout .05, FP32 weights with BF16 autocast, on AMD
MI250X hardware. Every update is exactly half English and half Italian.
The full run ended at 178,300 updates; 142k was selected on original development
NLL. Later diagnostic results motivated practical adaptations from 74k.

Italian base text was translated using the pinned Qwen3.6-35B-A3B setup on LUMI.
The practical adaptations use repository-authored paired templates and executable
labels, without a separate distillation teacher. The full corpus is dominated by
MNLI; equal language weight does not imply equal task weight.

Practical v2 selected +256 updates before final test, using disjoint instruction
banks and fact configurations. Focused v3 starts from this v2 checkpoint, adding
new routing and synthetic 16-intent examples, rebalanced Banking77 replay and broad
original-data replay. Its frozen protocol is in `FOCUSED_V3.md` and the recipes are
`recipes/nesso2-practical-v2.json` and `recipes/nesso2-focused-v3.json`.

## Current measured results

All cells show **English / Italian** accuracy. V3 adapter and merged export are
measured separately using FP32 parameters with BF16 autocast.

| Panel | V2 | V3 adapter | V3 export | Laya |
|---|---:|---:|---:|---:|
| Practical v2, 1,024 synthetic cases/language | 43.75 / 45.90% | 47.75 / 46.88% | 48.73 / 46.58% | 43.65 / 39.06% |
| Common-supported Okapi subset, 513/language | 31.19 / 31.77% | 30.02 / 32.36% | 30.41 / 32.55% | 30.02 / 27.10% |
| CLINC diagnostic, 151/language | 4.64 / 6.62% | 4.64 / 11.92% | 5.30 / 12.58% | 26.49 / 27.81% |

The practical average hides task-specific regressions: v3 adapter refunds drop
9.38 points EN / 3.91 IT, and urgency drops 5.47 points IT. Routing improves
24.22 / 13.28 points. The export shows the same pattern. All practical task cells
contain 256 cases/language. Laya remains substantially stronger on CLINC.
See `V3_REGRESSION.md` for per-task results and paired correctness transitions.
Benchmarks are small reused
diagnostic subsets, not official full-suite leaderboard scores. Italian evaluation
text is synthetic and only partially reviewed. Pretraining contamination is unknown.
See `COMPARISON.md` for all controls, task breakdowns, unsupported examples and
historical results. Do not attach the original 142k full-test accuracy to v2/v3.

## Confidence and limitations

No threshold qualified under either the v2 or v3 predeclared confidence policy. Their accepted
coverage is zero; this is abstention, not error-free predictions. High-confidence
mistakes remain. The fitted temperature does not guarantee correctness on new
wording or traffic. The earlier v1 policy failed under wording changes.

Synthetic rule and utterance templates do not represent customer traffic. The new
v3 intent panel has 16 classes and cannot establish 151-option CLINC performance.
The model may fail on ambiguous inputs, unfamiliar instructions, long menus,
negation, numeric comparisons and rare intents. No safety-critical suitability,
general reasoning competence or production readiness has been established.

## Candidate export and inference

The v3 pipeline prepares a private FP32 merged candidate only after development
selection and final comparison. It records merge, isolated reload, and final-test
prediction differences versus the adapter. FP32 is chosen for this first export;
quantized deployment performance has not been measured.

```python
from decision_model import DecisionModel

model = DecisionModel.from_pretrained("path/to/verified-export", device="cuda")
result = model.evaluate(
    state="I want to change the delivery address for my order.",
    questions={"intent": {
        "type": "choice",
        "instructions": "Select the customer's request.",
        "criteria": {
            "address": "Change the delivery address",
            "tracking": "Locate the parcel in transit",
            "refund": "Request money back"
        }
    }}
)
print(result)
```

This snippet requires the accompanying frozen Kev/Nesso runtime. It is not a
claim that an ordinary causal-language-model loader can load the decision head.

## Before publication

Replace this draft's identity with the reviewed selected artifact and SHA-256
hashes. Include its actual export test results, complete build sources, environment,
all recipes and dataset/translation provenance, limitations and attribution.
Review redistribution terms for materials actually packaged; the model, code,
recipes and underlying source datasets are separate artifacts. Preserve Kev and
parent notices. Remove site-specific paths from public instructions while retaining
internal manifests. No public upload has occurred in this adaptation pipeline.
