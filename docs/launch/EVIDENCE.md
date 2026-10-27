# Launch copy: sources and editorial record

Prepared 21 October 2026; Nev article revised 26 October 2026 with the completed Kev comparison and a stronger application-led narrative. The two articles are drafts, not a record of publication:

- [Nev launch](nev.md): compact bilingual decisions, standalone CPU quick start.
- [Nevso preview launch](nevso.md): division of work, measured local workflow gains.

User direction: release the established Nev variants as they stand; lead with compact size, edge/local inference, fast decisions, routing gains and working bilingual applications. Credit Kev as both inspiration and the software foundation. Use the completed fresh comparison, with competitive results scoped to particular tasks. The drafts select positive application evidence without claiming general-agent superiority or changing the underlying reports. Numerical claims retain their workload and hardware context. All existing evaluations remain intact.

## Claims and evidence

| Claim | Source | Interpretation preserved in copy |
| --- | --- | --- |
| 438,252,992 Nev parameters; 752,917,824 Kev parameters; approximately 42% fewer | [Completed fresh comparison](../../experiments/kev_comparison/evidence/results/report.json), `models.{v2,v3,kev}.engine.parameters` | Reduction is 41.79%; loaded parameter counts, not a RAM, latency or quality equivalence claim. Kev includes its merged adapter; the experimental Nev adapter is excluded from release-size claims. |
| Kev/Nev benchmark table and original-schema API figures | [Completed comparison](../../experiments/kev_comparison/evidence/results/README.md), [full JSON](../../experiments/kev_comparison/evidence/results/report.json), [protocol](../../experiments/kev_comparison/PROTOCOL.md) | Fresh FP32 runs for all three released models; all support 3,921 requests. Blog table explicitly uses `native_common.field_accuracy`, including Banking77; macro-F1 remains in full report. Eight selected rows plus original-schema API context, not an overall ranking. Native runtimes use different supported Torch versions. |
| 2,641 benchmark requests plus 1,280 workflow decisions | Same completed comparison and freeze manifest | 15 English tasks ×100, API-Bank 508×2, Home Appliance 25, MASSIVE 50×2; workflow 640 per language. Previously inspected diagnostics, not a fresh holdout. No experimental checkpoint result attributed to a released variant. |
| MASSIVE: EN/IT 58%/42% v2, 50%/38% v3, 64%/62% Kev | Same completed comparison, MASSIVE task/language rows | 50 matched IDs per language; native utterances with shared English intent descriptions. Training balance does not establish performance parity. |
| Routing specialization: +25.4 points EN, +12.1 IT | [Export comparison](../../EXPORT_COMPARISON.md) | 55.08−29.69=25.39 points, 46.88−34.77=12.11 points; same 256 cases/language, BF16-autocast merged-export evaluation. Separate from the FP32 Kev benchmark. |
| Eight passing bilingual reference pairs, four task families | [Reference gallery](../../examples/reference_examples.json), [selected outputs](../nesso2/evidence/a100-reference-selected.json) | Selected after inspecting 32 candidates; 16 requests (8 pairs) pass both v2/v3. Explicitly curated, never presented as representative accuracy. News excerpt retains the business label. |
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

The revised Nev article includes both competitive scores and substantial gaps, including Italian MASSIVE, ARC-Easy and original-schema API-Bank. It makes no blanket superiority, reliable arbitrary workflow, calibrated confidence, universal latency, phone validation, or “under 1 GB RAM” claim. The broader evidence remains linked. The earlier Qwen3-0.6B generative-agent comparison is not used as a marketing comparison because the evidence does not support overall superiority.

Quick-start commands reuse existing CLI options and release artifacts. For this documentation task, validate command syntax and paths; no full inference rerun or new benchmark is implied. Publishing the posts to an external blog is a separate action.

## 26 October release decision and wording

The user chose to launch the existing v2/v3 models and requested stronger claims
about routing and other demonstrated uses. The revised Nev article leads with
reproducible routing gains, the selected-tool Nev–Nesso3 CPU comparison, and the
four bilingual reference-gallery tasks. The original Nevso article remains a
separate developer-preview launch; no new combined model or agent reliability
claim was added.

The supported positioning is “competitive on selected tasks with approximately
42% fewer parameters,” with an explicit Kev acknowledgement. It is not “matches
Kev overall,” “equally accurate in English and Italian,” “the first decision model
in the world,” or a claim that selecting a tool completes an arbitrary workflow.
The more specialized research candidates are excluded from the launch artifacts.

This documentation revision imports the completed 26 October evaluation; it does
not run new inference, alter model weights or publish the posts externally.
