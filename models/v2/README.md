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
---

# Nesso2 Decision V2 Practical

Research release in the public repository `mii-llm/nev`, subdirectory `v2/`. Code and experiment documentation: https://github.com/mii-llm/nev.

A small typed decision model built with Kev. Input: state, instructions and explicit options. Output: categorical (`choice`), boolean (`noul`) or ordinal (`score`) decisions with probabilities. The model does not expose ordinary text generation.

## Candidate identity

Original checkpoint 74k +256 practical adaptation updates. V2 restarted from original 74k, not from the v1 adaptation.

Parent: `mii-llm/nesso2-0.4B-agentic@86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`. LoRA rank 16/alpha 32/dropout .05 and a 256-dimensional shared decision head. Exactly half of each training update is English, half Italian. Standalone exports contain merged FP32 backbone weights and a decision head.

## Why this variant

Keep v2 when investigating retention of refund rules and Italian urgency: it scores higher than v3 on those reused practical tasks. This is a relative strength, not evidence that all operational decisions are solved.

## Measured adapter results

These are the selected **adapter** scores, not scores attributed to a merged export. N is per language. External tasks are small reused diagnostic subsets; practical tasks are synthetic. Unsupported requests count as wrong.

| Task | N/language | English | Italian |
|---|---:|---:|---:|
| ARC-Challenge | 200 | 30.50% | 29.00% |
| HellaSwag | 200 | 32.50% | 33.00% |
| MMLU | 228 | 32.02% | 33.33% |
| ANLI | 150 | 31.33% | 38.00% |
| CLINC150+OOS | 151 | 4.64% | 6.62% |
| When2Call MCQ | 150 | 48.00% | 40.67% |
| practical_escalation | 256 | 50.00% | 51.56% |
| practical_refund | 256 | 61.33% | 54.69% |
| practical_routing | 256 | 30.08% | 34.38% |
| practical_urgency | 256 | 33.59% | 42.97% |

## Merged export results

Verified in LUMI job 22717040 (3m04s). FP32 merge maximum probability difference 3.40e-6 on 16 questions, with no argmax changes; isolated same-dtype reload was exact. These actual export scores use BF16 autocast and differ slightly from the adapter.

| Panel | English | Italian |
|---|---:|---:|
| okapi, full | 31.85% | 31.53% |
| decision_index, full | 27.72% | 28.38% |
| practical_v2, full | 44.14% | 45.51% |


## Training, evaluation and confidence

The original full run used 713,198 records and gold decision labels. Qwen3.6-35B-A3B translated Italian text; it was not the distillation teacher for this run. Later practical data uses executable labels and bilingual templates. Language balance is exact, but the base task mixture is dominated by MNLI. CLINC is not a training source.

V2 adaptation used 8,192 records, half practical examples and half original training replay. Its temperature was fitted on its own separate calibration-fit split: T=0.7320428479728127.

No confidence threshold qualified under the experiment policy. The inference API still returns decisions: abstention must be implemented by the application. A probability is not a correctness guarantee. The 16-intent synthetic task is different from 151-option CLINC. Laya remains much stronger on CLINC.

Italian evaluation text is synthetic and only partially reviewed; pretraining contamination is unknown. The reused external panels influenced later experiment choices and are not fresh independent release-selection tests. No official full-suite Decision Index score, CPU/mobile performance, quantization result or production suitability is claimed.

## Inference and provenance

Use the accompanying frozen `decision_model` runtime and the artifact-specific `config.json`, not a generic text-generation pipeline. See the shared `INFERENCE.md`, `BUILD.md` and `EXPERIMENTS.md`. The artifact manifest identifies the exact weights; the source manifest identifies the runtime. This variant directory contains the standalone evaluated weights, runtime and reproducibility documentation.

The parent revision declares Apache-2.0 in its model metadata; Kev code attribution and upstream notices are preserved in `NOTICE`. Dataset terms remain separate. See `parent-provenance.json`.


## Bilingual A100 reference examples

The tested example runner supports this variant. From the code checkout with
its runtime installed and the pinned model cached:

```bash
python examples/function_calling_demo.py --variant v2 --language both
python examples/run_reference_examples.py --variants v2 \
  --cases examples/reference_examples.json --output reference-v2.json
```

The gallery contains 16 requests selected after inspecting all 32 candidates;
it is a curated demonstration, not an unbiased accuracy estimate. Both languages
passed for each selected routing, function-selection, news-topic and banking
intent pair. Full candidate counts and the unsuccessful account-recovery case
are retained in the root model card and GitHub README. Function calling here
means selecting an allowed function name. Arguments are supplied by the
application and no function is executed. It does not establish argument
extraction, no-tool rejection, multi-step planning or reliable policy execution.
