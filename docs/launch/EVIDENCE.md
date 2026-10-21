# Launch copy: sources and editorial record

Prepared 21 October 2026. The two articles are drafts, not a record of publication:

- [Nev launch](nev.md): compact bilingual decisions, standalone CPU quick start.
- [Nevso preview launch](nevso.md): division of work, measured local workflow gains.

User direction: lead with compact size, edge/local inference, fast decisions and favorable measured examples. The drafts select positive application evidence without claiming general-agent superiority or changing the underlying reports. Numerical claims retain their workload and hardware context. All existing evaluations remain intact.

## Claims and evidence

| Claim | Source | Interpretation preserved in copy |
| --- | --- | --- |
| ~0.4B backbone; 50/50 EN/IT decision updates; lineage; license | [Main README](../../README.md), [research guide](../RESEARCH.md), [NOTICE](../../NOTICE) | “First” is scoped to mii-llm; foundation weights were pretrained from scratch, not all architecture/software. Nev descends from Nesso2; Nesso3 is its generative partner. |
| 451 MiB Nev Q8; 902 MiB pair | [CPU guide](../../experiments/cpu_gguf/README.md), [release pins](../../experiments/cpu_gguf/release.json) | Backbone file size, not full package size or RAM. Nev needs its original head and tokenizer. |
| 77.2 ms p50; 98.5 ms p95 | [Raw A100 latency report](../nesso2/evidence/a100-speed-shared.json), `models.v3.measurements.fp32.workloads.one_question.summary` | 20 sequential requests, batch one, FP32, shared GPU. Includes validation/tokenization/synchronization; excludes loading, HTTP and download. Not a CPU Q8 timing. Historical receipt predates organization migration. |
| Bilingual billing, invoice, ATM examples | [Reference cases](../../examples/reference_examples.json), [selected results](../nesso2/evidence/a100-reference-selected.json) | Selected successes; support/banking request excerpts are explicitly shortened. No predicted argument extraction is attributed to Nev. |
| V2→V3 routing accuracy | [Export comparison](../../EXPORT_COMPARISON.md) | Same 256 requests/language; merged exports, BF16 autocast. No across-task improvement claim. |
| V3 synthetic 54.69% / 62.50% | [Focused test](../nesso2/FOCUSED_V3_RESULTS.md) | 512 examples/language, routing plus 16-intent panel; merged-export scores, not adapter scores or general customer accuracy. |
| 18→22 correct calls; 14→20 tasks; 2.57→1.72 s; 1546→316 prompt tokens | [Mac routing comparison](../../experiments/cpu_gguf/ROUTING_COMPARISON.md) | 24 authored requests, Q8, four M3 Pro CPU threads; Nev selection; both models resident. Reduction = (2.57−1.72)/2.57 ≈ 33.1%. Task-success gain = (20−14)/24 = 25 percentage points. |
| Greenhouse 23/24 calls, 22/24 factual tasks | [Mac greenhouse comparison](../../experiments/cpu_gguf/GREENHOUSE_COMPARISON.md), [GPU guide](../nevso/GPU_GUIDE.md), [GPU raw report](../nevso/evidence/greenhouse-a100.json) | Nev ranking; 24 requests per arm, 12 per language. Exact calls 12/12 EN and 11/12 IT on both backends. Assistant factual review, not independent human audit; strict date format yields 19/24. |
| Greenhouse CPU 4.16 s, GPU 1.44 s ranked | Same greenhouse reports | Separate runs/configurations; no CPU/GPU speedup inference. Ranking is slower than standalone on CPU; do not attach the 1.72 s selected-tool latency to greenhouse ranking. |
| English 28.3→93.3%; Italian 38.3→71.7% | [Completed stress review](../../experiments/nevso_stress/REVIEW.md) | Authored confusable category only; correct executed calls, not final answers; 20 cases/language × three correlated order repeats. Not an official BFCL score. |
| About 2.9 GiB summed RSS | [CPU diagnostic](../../experiments/cpu_gguf/README.md), [summary](../../experiments/cpu_gguf/results/SUMMARY.json) | Separate 12-request Q8 diagnostic, 2985 MiB sampled summed RSS. Not physical footprint, a minimum RAM requirement, or the greenhouse run's measured memory. |
| Public offline-capable CPU downloads | [Public-download verification](../../experiments/cpu_gguf/results/public-download-validation.json), [setup](../../experiments/cpu_gguf/setup.sh) | Public access verified in saved release checks; offline inference after downloading/building dependencies. No new hardware measurements made for these posts. |

## Packaging and review

Nevso is presented as a developer preview in the existing Nev repository, not a newly uploaded combined checkpoint or merged weights. The source models remain separately downloadable.

The articles do not reproduce unrelated low-scoring tables. They also make no blanket superiority, reliable arbitrary workflow, calibrated confidence, universal latency, phone validation, or “under 1 GB RAM” claim. The broader evidence remains linked. The Qwen comparison is not used as a marketing comparison because the evidence does not support overall superiority.

Quick-start commands reuse existing CLI options and release artifacts. For this documentation task, validate command syntax and paths; no full inference rerun or new benchmark is implied. Publishing the posts to an external blog is a separate action.
