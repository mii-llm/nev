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

# Nesso2 Decision V3 Routing

Research release in the public repository `mii-llm/nev`, subdirectory `v3/`. Code and experiment documentation: https://github.com/mii-llm/nev.

A small typed decision model built with Kev. Input: state, instructions and explicit options. Output: categorical (`choice`), boolean (`noul`) or ordinal (`score`) decisions with probabilities. The model does not expose ordinary text generation.

## Candidate identity

Selected v2 +512 focused adaptation updates. Training stopped at +896; later +640/+768/+896 failed retention guards. +512 was fixed by development selection before the new final test.

Parent: `mii-llm/nesso2-0.4B-agentic@86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`. LoRA rank 16/alpha 32/dropout .05 and a 256-dimensional shared decision head. Exactly half of each training update is English, half Italian. Standalone exports contain merged FP32 backbone weights and a decision head.

## Why this variant

V3 is the routing-focused candidate. It improves routing across both practical panels and the new synthetic 16-intent task, while losing accuracy on refund rules and Italian urgency. It does not replace v2 across every task.

## Measured adapter results

These are the selected **adapter** scores, not scores attributed to a merged export. N is per language. External tasks are small reused diagnostic subsets; practical tasks are synthetic. Unsupported requests count as wrong.

| Task | N/language | English | Italian |
|---|---:|---:|---:|
| ARC-Challenge | 200 | 30.50% | 31.00% |
| HellaSwag | 200 | 29.50% | 32.50% |
| MMLU | 228 | 31.14% | 32.02% |
| ANLI | 150 | 30.67% | 37.33% |
| CLINC150+OOS | 151 | 4.64% | 11.92% |
| When2Call MCQ | 150 | 46.00% | 37.33% |
| practical_escalation | 256 | 51.17% | 51.56% |
| practical_refund | 256 | 51.95% | 50.78% |
| practical_routing | 256 | 54.30% | 47.66% |
| practical_urgency | 256 | 33.59% | 37.50% |

## Merged export results

The v3 export has verified FP32 merge and isolated offline reload. Its BF16-autocast benchmark results differ slightly from the adapter.

| Panel | English | Italian |
|---|---:|---:|
| okapi, full | 30.73% | 32.17% |
| decision_index, full | 27.05% | 29.71% |
| practical_v2, full | 48.73% | 46.58% |
| New synthetic 16-intent/routing test, 512/language | 54.69% | 62.50% |

## Training, evaluation and confidence

The original full run used 713,198 records and gold decision labels. Qwen3.6-35B-A3B translated Italian text; it was not the distillation teacher for this run. Later practical data uses executable labels and bilingual templates. Language balance is exact, but the base task mixture is dominated by MNLI. CLINC is not a training source.

V3 adaptation used 8,192 records: 1,024 new routing, 1,024 synthetic 16-intent, 3,072 Banking77 replay and 3,072 other original replay. Its fitted temperature is T=0.8122523963562355.

No confidence threshold qualified under the experiment policy. The inference API still returns decisions: abstention must be implemented by the application. A probability is not a correctness guarantee. The 16-intent synthetic task is different from 151-option CLINC. Laya remains much stronger on CLINC.

Italian evaluation text is synthetic and only partially reviewed; pretraining contamination is unknown. The reused external panels influenced later experiment choices and are not fresh independent release-selection tests. No official full-suite Decision Index score, CPU/mobile performance, quantization result or production suitability is claimed.

## Inference and provenance

Use the accompanying frozen `decision_model` runtime and the artifact-specific `config.json`, not a generic text-generation pipeline. See the shared `INFERENCE.md`, `BUILD.md` and `EXPERIMENTS.md`. The artifact manifest identifies the exact weights; the source manifest identifies the runtime. This variant directory contains the standalone evaluated weights, runtime and reproducibility documentation.

The parent revision declares Apache-2.0 in its model metadata; Kev code attribution and upstream notices are preserved in `NOTICE`. Dataset terms remain separate. See `parent-provenance.json`.


## Bilingual A100 reference examples

The tested example runner supports this variant. From the code checkout with
its runtime installed and the pinned model cached:

```bash
python examples/function_calling_demo.py --variant v3 --language both
python examples/run_reference_examples.py --variants v3 \
  --cases examples/reference_examples.json --output reference-v3.json
```

The gallery contains 16 requests selected after inspecting all 32 candidates;
it is a curated demonstration, not an unbiased accuracy estimate. Both languages
passed for each selected routing, function-selection, news-topic and banking
intent pair. Full candidate counts and the unsuccessful account-recovery case
are retained in the root model card and GitHub README. Function calling here
means selecting an allowed function name. Arguments are supplied by the
application and no function is executed. It does not establish argument
extraction, no-tool rejection, multi-step planning or reliable policy execution.
