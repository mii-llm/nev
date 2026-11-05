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


## 3 November Nevso portability revision

The Nevso launch now leads with one Linux/macOS CPU installation and test path,
with the existing Linux/NVIDIA CUDA guide as an alternative. The new
[quick start](../nevso/QUICKSTART.md) includes supported Python versions,
bilingual real-inference smoke checks, three-arm comparisons, readable traces
and custom JSON catalogs. `setup.sh --gguf-only` installs the published-GGUF
inference dependencies without the training/reference stack in a fresh venv;
`--python` chooses Python 3.12 or 3.13 explicitly. Model pins, controller logic,
prompts and evaluation cases are unchanged.

[Linux validation](../nevso/LINUX_VALIDATION.md) records fresh-host installation
and CPU results separately from the historical Mac and CUDA scores. This is
portability validation on authored development examples, not new independent
quality evidence. Platform-specific measurements remain labelled. No new model
training or general multi-step reliability claim is introduced.

## 3 November Python API

The [source-checkout API](../nevso/PYTHON_API.md) registers Python handlers with
JSON schemas and bilingual descriptions. It uses the same controller and
one-time per-request selection/ranking as the launch comparison. It preserves
validation, argument-grounding checks and turn/call limits. The wrapper's
`none` strategy skips ranking but retains both loaded models.

Nine scripted-backend tests passed locally and on Linux. The three-function
example returned correct Italian pH and English tank readings, and six actual
Linux Q8 trials matched the previous CLI calls, answers, statuses and errors.
The [validation record](../nevso/evidence/python-api-20261103/validation.json)
pins the new source and evidence. This adds an integration interface, not new
model weights, new benchmark accuracy or a validated general agent. No fresh
CUDA API inference was run for this change.

## 5 November Nevso launch wording

Retitled the article to announce Nevso as a decision-model + SLM agent for small
devices. The opening defines each model's role, emphasizes local bilingual
inference and the Python API, and distinguishes the intended device use from
the tested Linux/macOS CPU and Linux/NVIDIA configurations. Installation,
evaluation structure, numerical claims and deployment limitations are retained.
This is an editorial change; no new inference or device validation is implied.

The subsequent wording revision uses “Building Nevso” and opens directly with
the implemented approach and the scoped 24-request Mac result. It avoids
rhetorical questions and moves the release announcement to the closing
paragraph. Installation, results and design discussion retain their order.
This presents an engineering account without making claims about guaranteed
reach or distribution on social publishing platforms.


## 5 November broader Nevso evaluation in the article

Expanded the stress-test section from two selected routing percentages to the
completed 200-request/1,800-trial evaluation. Counts distinguish unique requests
from correlated tool-order repeats. The article now shows coverage, EN/IT
confusable-call and completion-proxy tables, external BFCL call results,
reviewed clarification and dependent-workflow/date-format limits. These remain
native A100 BF16/FP32 results, separate from CPU Q8 demonstrations.

Confusable and external counts were recomputed from
`experiments/nevso_stress/evidence/a100/rows.jsonl`; clarification uses
`clarification_review.json`, not the uncorrected lexical proxy. Dataset counts
were checked against `suite.json`. No new evaluation was run. The article does
not attribute 1,800 independent examples, general agent accuracy or an official
BFCL score to this evidence. The reported findings and all source results remain
unchanged.

## 5 November lineage and RAM guidance

The opening now identifies Zagreus (foundation pretrained from scratch) →
Nesso2 → Nev, with Nesso3 as the generative partner rather than Nev's training
parent. This follows `docs/RESEARCH.md` and preserves credit for the existing
architecture, tokenizer and Kev framework.

The RAM planning estimate is **8 GB total system memory** for the small,
sequential Q8 workflow. Its basis is the existing CPU diagnostic's
`backends.q8.peak_summed_rss_mib = 2985.3125` in
`experiments/cpu_gguf/results/SUMMARY.json`, approximately 2.9 GiB. Summed RSS
can double-count shared pages and is not a physical-footprint or hard-maximum
measurement. The article and quick start explicitly mark 8 GB as an estimate;
neither an 8 GB device nor a 4 GB minimum was validated. No new memory test was
run for this wording change. Backbone disk size remains separate from RAM.
