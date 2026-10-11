# Nesso2 bilingual decision model: experiment record

Last updated: 11 October 2026. This is the durable project record for the planned
public model and build recipe. Preserve failures and superseded runs as well as
successful results. Publication is planned; no new model has been uploaded by
this work. Follow-up work should read this file and append outcomes with evidence.

## Objective and fixed constraints

- Convert `mii-llm/nesso2-0.4B-agentic` into a small EN/IT decision model using Kev.
- Parent revision: `86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`.
- Maintain exactly 50% English and 50% Italian training weight per update.
- Run on LUMI AMD GPUs only; preserve remote artifacts under project scratch.
- Prioritize useful decisions and honest confidence/abstention over broad LLM claims.
- Publish an auditable recipe, source revisions, evaluation definitions and limitations.
- Keep original dataset terms and Kev attribution; software licensing does not
  automatically grant permission to redistribute every source dataset.

## Evidence and reproducibility

`evidence/lumi-evidence-20261010.tar.gz` preserves 165 files: frozen training Python
source, base recipe, data manifest/review metadata, completed reports, and the v1
pilot source and metrics. It excludes model weights and original training JSONL.
Every member was checked against `evidence/archive-index.json` after download.

Archive SHA-256:
`d740cf309846e2ff0842ce8994cc6e5d00d240572ef57e8a5a75acc15e80722f`.

This is an internal evidence archive, not a ready-to-publish bundle. Raw reports
contain site-specific paths. Public summaries must retain checkpoint hashes and
results while replacing machine-specific paths with documented parameters.
Frozen remote artifacts remain the authoritative run record. Preserve a separate
archive rather than rewriting evidence when preparing the public package.

Readable extracted reports:

- [Full training report](evidence/full-training-report.json)
- [Decision Index selection reports](evidence/decision-index-selection-reports.json)
- [Practical v1 report](evidence/practical-v1-report.json)
- [Practical v1 training history](evidence/practical-v1-training.json)

## Milestones before the practical pilots

The early 1,684-record bilingual pilot was a compatibility experiment, not the
intended full-data model. Initial translation output was rejected, then repaired.
The gold-only pilot performed better than the tested distillation alternative.
These historical observations are recorded in `experiments/lumi/README.md`; do
not present them as controlled claims that every teacher would be worse.

Training audits found finite nonzero adapter/head updates and successful
memorization of a small clean sample. Packed/rows/cached execution agreed within
the recorded tolerances. A restart proof matched all 452 trainable tensors exactly
between resumed and uninterrupted runs. No training bug explaining the original
large baseline gap was established. Numerical/export differences were measured,
and parent pretraining contamination remains unknown.

The reviewed full corpus contains **713,198 training records**, 356,599 per
language, across AG News, TREC, Banking77, BoolQ, MNLI, SST-5, generated composition
and contrastive rules, and custom support tickets. The source mixture is about
72% MNLI; language balance does not imply task balance. Therefore intent
classification WAS trained (Banking77/support), but CLINC was not a training source.

The full-corpus Italian translator was **Qwen/Qwen3.6-35B-A3B**, revision
`995ad96eacd98c81ed38be0c5b274b04031597b0`, served using the existing LUMI vLLM
setup. The paired corpus records prompt version `vllm-quoted-fewshot-v3`, cache
and prompt hashes, exclusions and schema corrections. This translator did not
replace the gold decision labels or supply distillation targets to the full run.

Reviewed data manifest SHA-256:
`6410cdcf4157ec1e849dd62f7afec217a9fe7e27342d8509ecc749030464f6da`.

The two-epoch full run finished at **178,300 updates**. Development NLL selected
**142k**. The exported selected model reached **88.29% EN / 86.87% IT** on the
full training-domain test and **59.30% EN / 60.70% IT** on the separate unseen-source
panel. These panels have different task mixes and cannot be compared directly
with Okapi, Decision Index, or the practical pilots.

## External diagnostic evaluations

Okapi-derived MMLU, HellaSwag and ARC-Challenge use 628 matched requests per
language (1,256 total), not full benchmark suites. Repeated evaluation influenced
our later choice of starting checkpoint; these are now development evidence.

| Checkpoint | EN accuracy | IT accuracy | Combined |
|---|---:|---:|---:|
| Original parent | 24.2% | 24.2% | 24.2% |
| 74k | 31.1% | 31.5% | 31.3% |
| 142k | 29.9% | 28.8% | 29.4% |
| Final 178300 | 30.3% | 28.5% | 29.4% |

The Decision Index custom selection panel has 451 EN + 451 IT cases: ANLI 150,
CLINC150+OOS 151 and When2Call 150 per language. The official composite score is
not being reproduced. Upstream code was pinned to
`87d4650b42b377c0291a89c1f1a879f9b31082bf`.

| Model | EN task-macro accuracy | IT task-macro accuracy |
|---|---:|---:|
| Original parent | 10.66% | 10.67% |
| 74k | 28.66% | 27.99% |
| 142k | 26.22% | 26.66% |
| Laya | 26.39% | 26.83% |

Unsupported examples count as wrong in that table. Laya missed 55 EN / 69 IT
When2Call requests, compared with 1 EN / 6 IT for our checkpoints, so this is not
a fair common-support ranking. CLINC is intent-balanced. The pinned When2Call
source contains no gold direct-answer class. Italian is synthetic and only
partially reviewed: 27 shared CLINC intent labels were corrected. Two remaining
numeric-format flags affect unused confirmation cases, not selection cases.
The user accepted minor translation imperfections for this diagnostic and later
deprioritized When2Call. Confirmation was not used in the recorded selection run.

## Practical v1: completed 10 October

Preparation job **22672695** passed; GPU job **22672696** completed in **34m04s**.
The pilot initialized from 74k and ran 512 updates with 4,096 records: half new
synthetic cases, half original-data replay, exactly half each language. Four
families: routing, refunds, urgency and escalation. Each split had disjoint full
fact configurations, but training/dev/calibration shared one instruction template
per family; final test changed that wording. This limitation motivated v2.

| Model | Final-test EN (512 cases) | Final-test IT (512 cases) |
|---|---:|---:|
| 74k | 33.01% | 31.64% |
| 142k | 36.91% | 31.05% |
| 74k + 512 updates | 40.23% | 35.35% |

Uniform random choice averages approximately **35.42%** across these four tasks.
The absolute scores do not establish readiness. The adapted model's dev accuracy
rose from 57.03% at 128 updates to 78.13% at 512; NLL fell from .9034 to .4897.
The adaptation passed the original-task regression guard at all four checkpoints.
The final EN/IT average was only **37.79%** after the wording change, suggesting
template sensitivity rather than robust rule understanding.

Calibration accuracy was 81.15% on the familiar wording. The fitted temperature
was .8409 and threshold .7. On final test, that threshold accepted 55.08% of EN
cases with **59.57% error**, and 40.63% of IT cases with **67.31% error**. This is
a confidence failure, not a usable escalation policy. The 512-update checkpoint
remains experimental and must not be described as production-ready.

MI250X timing for the adapted checkpoint: median **78.35 ms**, p95 **81.73 ms**
per request; peak allocated GPU memory **2,035,248,640 bytes** (~1.90 GiB).
Batch size 1, FP32 weights with BF16 autocast, warmup, includes tokenization,
excludes loading/network. These measurements do not predict CPU/mobile latency.

## Practical v2: completed

The user authorized a wording-diverse round and asked to retain all important
steps/results for publication. V2 starts from original 74k, with 142k as a control.
It does not continue from v1's adapted weights. The generator excludes every v1
fact configuration and treats v1's examined test as diagnostic history only.

The recipe is [nesso2-practical-v2.json](../../recipes/nesso2-practical-v2.json).
There are nine bilingual instruction pairs per family: four for training, one
for development, one for temperature fitting, one for threshold selection, two
for final test. State presentation varies among structured summaries, case notes,
and support-shaped prose. Labels come from executable rules, with no separate
teacher model. All cases remain synthetic and share the four rule families.

V2 has 8,192 training records, half new and half original replay, half EN/half IT.
It has 1,024 dev, 1,024 calibration-fit, 1,024 calibration-policy and 2,048 final-test
records. The regression guard uses up to 32 bilingual pairs per original source.
Train for at most 1,024 updates, evaluate every 128, LR 1e-5 with 32-update warmup.
After at least 512 updates, stop if three evaluations bring no eligible improvement.
Eligibility keeps original-dev NLL within +.05 and each language accuracy within
-2 percentage points of the 74k control. Selection uses new-dev macro NLL, not test.

Temperature and confidence thresholds use separate facts and wording. Final test
is scored only after selection/calibration are frozen. Reports include EN/IT,
task and template breakdowns, confidence errors, coverage, latency, memory and
the GPU package environment. Eleven focused local v1/v2 tests passed. The GPU
results are recorded below; release artifact checks remain pending.

V2 submission: CPU preparation **22692572**, dependent GPU pilot **22692573**.
Remote run directory:
`/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/practical-pilot-v2`.
The journal is `jobs.json`; completion requires `results/report.json` with
`status: complete`. Submission is not proof that training has started.

Scheduling update, 10 October: at the user's request, the existing pending GPU
job **22692573** was moved in place from `small-g` to **`dev-g`**, which had idle
MI250 nodes. The one-GPU request and three-hour cap are unchanged. Slurm required
the time limit to be specified explicitly together with the partition update;
the initial partition-only change was rejected without modifying the job.
The successful override was `scontrol update JobId=22692573 Partition=dev-g
TimeLimit=03:00:00`. No duplicate job was submitted and the hashed batch/source
files were not changed. Before/after scheduler records are saved under the v2
run's `scheduling/` directory. Queue state must still be checked before claiming
that execution has begun.

Job **22692573 completed successfully in 50m13s** on `dev-g`. Training stopped
at **640 additional updates** because development NLL had not improved for three
evaluations after its best point. Development accuracy continued increasing;
the stopping criterion was NLL, not accuracy. All five evaluated snapshots passed
the original-task regression guard. The selection, frozen before final test,
was **74k + 256 updates**, with dev macro NLL **1.13358** versus **1.25061** for 74k
and **1.50905** for 142k.

Fresh final test: **1,024 cases per language**, 256 per task.

| Model | EN accuracy | IT accuracy | Combined accuracy |
|---|---:|---:|---:|
| Original 74k | 39.36% | 39.55% | 39.45% |
| Original 142k | 33.69% | 38.57% | 36.13% |
| Selected 74k + 256 updates | 43.75% | 45.90% | 44.82% |

The selected model improves over the 74k control by **4.39 EN / 6.35 IT percentage
points** on this panel. Do not compare these absolute scores directly to v1's
different final test or claim significance without a paired uncertainty analysis.

| Task | Selected model EN | Selected model IT |
|---|---:|---:|
| Routing | 30.08% | 34.38% |
| Refunds | 61.33% | 54.69% |
| Urgency | 33.59% | 42.97% |
| Escalation | 50.00% | 51.56% |

The calibrated temperature is **.73204**. **No confidence threshold qualified**
under the predeclared calibration policy for any candidate. Thus accepted
coverage is zero; this is an explicit abstention outcome, not zero prediction
errors or successful automation. Confidence remains unready: the selected
checkpoint has 48 wrong Italian predictions with calibrated confidence >=90%
on the final test, despite the policy correctly refraining from accepting them.

Selected-model latency: median **72.06 ms**, p95 **80.92 ms**, peak allocated
memory **2,035,772,928 bytes**, AMD MI250X, batch size 1, FP32/BF16 autocast,
same timing definition as v1. The checkpoint remains an experimental candidate;
no export or public upload was made as part of this run.

Evidence: [final report](evidence/practical-v2-report.json),
[training history](evidence/practical-v2-training.json), and
[environment](evidence/practical-v2-environment.json).
`evidence/practical-v2-completed.tar.gz` additionally preserves per-case logits,
the frozen scripts/recipe, manifests, scheduling changes and checkpoint metadata;
its members were verified against `evidence/practical-v2-archive-index.json`.
Archive SHA-256:
`7952999a510db7b5ab722d9048b4ecd935164f3462d867ad302c6461e2938b76`.

## Selected v2 comparison against Laya: completed 10 October

At the user's request, job **22697632** evaluated the selected **74k + 256**
checkpoint on the frozen Okapi and Decision Index panels and added pinned Laya
multilingual to the unchanged practical-v2 test. No new training or checkpoint
selection occurred. Earlier predictions were reused only after manifest/input
alignment checks. Job completed in **4m30s**, exit 0, dev-g node nid007977.

| Panel / metric | Selected v2 EN | Selected v2 IT | Laya EN | Laya IT |
|---|---:|---:|---:|---:|
| Practical v2, 1,024/language | 43.75% | 45.90% | 43.65% | 39.06% |
| Okapi common bilingual, 513/language, micro | 31.19% | 31.77% | 30.02% | 27.10% |
| Decision Index common bilingual, 378/language, micro | 24.34% | 25.66% | 30.16% | 32.01% |
| Decision Index common bilingual, task-macro | 28.44% | 27.86% | 27.17% | 30.83% |

The English practical difference from Laya is only **one answer**; treat it as
a tie. Italian improves by 70 answers (+6.84 points). Relative to original 74k,
practical gains are +4.39 EN / +6.35 IT points. Common Okapi differences from
74k are +.58 EN / +.39 IT points, descriptive changes on a small reused panel.
Laya remains clearly stronger on CLINC: 26.49% EN / 27.81% IT versus v2's
4.64% / 6.62%. Laya also leads ANLI; Nesso leads the When2Call subset.

Common support requires both languages to fit every model. Okapi retains 200 ARC,
88 HellaSwag and 225 MMLU per language; Decision Index retains 150 ANLI, 151 CLINC
and 77 When2Call. Full-panel results counting unsupported requests as wrong are
also preserved. The different denominators and task-macro versus micro weighting
must remain visible. No official leaderboard composite is claimed.

Laya uses its pinned native renderer, weights and shipped temperature, with
8192/8184 context/head limits and explicit no-truncation checks. Practical boolean
and ordinal decisions use native probabilities with argmax, not rounded expected
score. The pinned Decision Index validator lacks ordinal support, so the adapter
checks its type, keys and probability distribution explicitly. All 2,048 practical
requests fit; three rounded-probability ties use the first semantic key. CPU fallback
was zero. Four focused local scoring/alignment tests and the remote preflight passed.

All historical checkpoint and per-task tables are in [COMPARISON.md](COMPARISON.md).
Machine report: [latest comparison](evidence/latest-comparison-report.json).
The completed archive contains 35 files including all reused per-case baselines,
new predictions, source, manifests, and scheduler evidence. Every member was
verified against `evidence/latest-comparison-archive-index.json`.
`evidence/latest-comparison-completed.tar.gz` SHA-256:
`941cb2e354f76d520fe54e3c4c14064cb04ee773f12f0a59caac828a9c6e32f6`.
Remote run: `runs/bilingual-all-v1/practical-v2-benchmark-comparison-v1`.
The confidence-policy and public-release limitations above remain unchanged.

## Focused v3: authorized and prepared 11 October

User approved the next plan: targeted intent/routing adaptation, exactly 50/50
EN/IT, original-data replay, periodic regression checks, a fresh final test with
v2/Laya controls, and preparation for a public model/recipe. The concrete protocol
is [FOCUSED_V3.md](FOCUSED_V3.md); recipe is
[nesso2-focused-v3.json](../../recipes/nesso2-focused-v3.json).

Start from selected **v2 74k + 256**, not the final +640 snapshot. The 8,192-record
mix is 1,024 new routing, 1,024 synthetic 16-intent, 3,072 Banking77 replay and
3,072 other-source replay; every update is balanced by language. Final test has
512 fresh paired cases per language. Old v1/v2 routing facts and new intent test
utterances are excluded from training. This is controlled synthetic transfer,
not evidence of natural-traffic or CLINC generalization.

Maximum 1,024 updates; evaluate every 128; earliest stop 512 after three stale
evaluations. Both original-task and practical-v2-development retention guards
must pass separately. Select by new-development NLL before temperature fitting,
policy fitting and final test. If no eligible improvement exists, keep v2.

The dependent GPU pipeline includes Laya comparison and a private FP32 export
with merge/reload and final-test prediction checks. No public upload is scheduled.
Five focused local tests passed; CPU schema/admission audit and actual training
status must be checked before reporting success.

Staged source archive SHA-256:
`aff5c9d7505928c975baa53f5b6f723c040f2b44b06dfa9a482393e61684cbe0`.
Run directory: `runs/bilingual-all-v1/focused-pilot-v3` under the existing task root.
CPU preparation **22707765** and dependent single-GPU pipeline **22707766** were
submitted. The five tests also passed on the LUMI login Python before submission.
This entry is not a claim that training or evaluation has finished.

V3 progress check: preparation 22707765 completed in 1m38s. Nesso training,
selection, calibration and final evaluation completed (first GPU job step 55m42s).
Development selection chose **adapted-512**, i.e. 512 additional updates from v2.
On the **new synthetic intent/routing test** (512 examples/language), unchanged
v2 scored **23.63% EN / 25.00% IT** and selected v3 **54.88% / 62.89%**.
This is a different panel from practical-v2 and is not evidence of CLINC gains.
At this check the Laya stage had reached 800/1,024 and the overall GPU job was
still running; export and pipeline completion were not yet verified.

### Focused v3 completion verified

Job **22707766 completed in 58m52s**, exit 0. Training stopped at +896;
selected **v2 +512** passed both retention guards, while +640/+768/+896 were
ineligible. Fresh synthetic test (512/language): v2 **23.63% EN / 25.00% IT**,
v3 adapter **54.88% / 62.89%**, Laya **26.17% / 28.71%**. All cases fit all models.
This is a synthetic 16-intent/routing test; no new CLINC/Okapi gains are claimed.

Private FP32 export completed. Merge max probability delta 4.62e-6 on 40
questions, no argmax changes; isolated FP32 reload exact. Full-test BF16-autocast
inference changed 12/1,024 predictions after merging, giving exported accuracy
**54.69% EN / 62.50% IT**, three fewer correct answers overall. Preserve this
numeric difference rather than attributing adapter metrics to the shipped artifact.
Calibrated T=.81225; no confidence threshold qualified. No public upload occurred.

[Complete v3 results](FOCUSED_V3_RESULTS.md) link all readable evidence.
The local completed archive contains 97 individually verified files, plus selected
checkpoint/export SHA-256 hashes; model weights remain on project scratch.
Archive SHA-256:
`3aee6c64f0e12a48b0278265c7ab9c8edd45b9aae842e4dae0a22f517fe15c58`.

### V3 regression audit completed — 2026-10-11

At the user's request, evaluated the fixed selected v3 +512 adapter and its merged
export on all previously prepared panels: 1,256 Okapi (MMLU/HellaSwag/ARC),
902 Decision Index (ANLI/CLINC/When2Call) and 2,048 practical-v2 requests per model.
All are exactly half EN/IT. No training, checkpoint reselection or public upload.
LUMI job **22714887 completed in 8m34s**, exit 0. Six local comparison/pairing tests
passed. CPU preflight reproduced archived baselines after allowing 1e-12 float
summation differences between Python versions; IDs, labels and counts remain exact.

Full-panel v3 adapter vs v2: Okapi **30.41/31.85% vs 31.69/31.85%** EN/IT;
practical **47.75/46.88% vs 43.75/45.90%**. CLINC **4.64/11.92% vs 4.64/6.62%**.
Practical averages conceal regressions: routing gains **24.22/13.28 points**,
refund loses **9.38/3.91**, and urgency loses **5.47 IT** (EN unchanged).
MMLU changes -0.88/-1.32, HellaSwag -3.00/-0.50, ARC 0/+2.00,
ANLI -0.67/-0.67 points. Treat these as observed diagnostic changes, not claims
of population-level significance on small reused panels.

Merged export practical accuracy **48.73/46.58%**; refunds **52.73/50.39%**
and Italian urgency **37.89%**, confirming the same tradeoff. Export correctness
versus adapter gains/losses: Okapi 8/4, DI 6/2, practical 14/7; these are not
counts of every argmax change. The full report retains historical controls and
Laya on identical bilingual support. Laya still leads CLINC substantially.

Interpretation: retain v3 as a promising routing-focused candidate; do not claim
a universal improvement. A future general-purpose adaptation should add balanced
refund/urgency replay and per-task development guards. Do not pick checkpoints
using these test results. No additional training was launched in this audit.

[Regression report](V3_REGRESSION.md), machine-readable results, exact input panels,
per-case predictions, frozen runtime, scripts and model hashes are preserved in
70 locally hash-verified evidence files. Archive SHA-256:
`343ff137a7bb7d6b714c68377d8427cd0accd35b7352bbf6b5984b7da36fed4b`.
Remote run: `runs/bilingual-all-v1/focused-v3-regression-v1`.

### Two-variant release preparation — 2026-10-11

The user chose to preserve and describe both variants rather than continue
optimizing a single aggregate score: **v2 Practical** and **v3 Routing** are
working display labels. Public repository identifiers are not finalized.
No additional training or public upload was requested/performed in this step.

V2 previously had no standalone candidate export. New LUMI job **22717040**
completed in **3m04s**, creating a separate FP32 export and evaluating all 4,206
existing regression requests. Original checkpoints and v3 export were untouched.
FP32 merge maximum probability difference **3.3975e-6**, 16 questions in 11
requests, zero argmax changes; isolated same-dtype reload exact.
V2 actual export accuracy: Okapi **31.85% EN / 31.53% IT**; Decision Index full
panel **27.72% / 28.38%**; practical-v2 **44.14% / 45.51%**.
These differ from adapter scores and are recorded independently. The newly
exported v2 was not evaluated on v3's fresh synthetic panel; do not transfer its
adapter's fresh-panel score to that export.

V2 release evidence archive SHA-256:
`eb49678c77af3e43b66146a4f69399901841e835efc753cf5f6a4a8473829a07`.
Per-case correctness and aggregate results were recomputed locally, with source,
manifest and artifact metadata hashes checked. Exact parent revision metadata was
queried through Hugging Face: Apache-2.0 is declared, but the parent repository
has no separate LICENSE file. Standard Apache-2.0 text and preserved Kev notices
plus Nesso-specific attribution were added to the release draft.

[Release preparation](../../README.md) includes two model
cards, actual-export and adapter comparisons, the complete milestone narrative
(including rejected translations, distillation and confidence failures), archive
inventory, exact 17-file frozen inference runtime, base/v2/v3 recipes, data source
revisions and 40 recipe/provenance files. The historical reference implementation
still depends on the original run layout; a verified portable training entry
point and clean installation on another machine remain pending. These limitations
are explicitly recorded in the release status, not presented as completed work.

Candidate artifacts are assembled under `releases/preparation-v1/candidates` on
the existing LUMI scratch task root. Model weights/configuration are checked
against the evaluated sources; model cards and notices are added to copies.
The original artifacts and their evidence hashes remain unchanged.

Packaging validation: initial smoke **22717506** failed after 15s because the
harness replaced LUMI's dependency PYTHONPATH and could not import pydantic. The
corrected harness puts the isolated installed runtime first while retaining the
tested dependencies and verifies its actual import location. Retry **22717547**
completed in **1m52s**: pip wheel/install succeeded and offline English/Italian
examples ran against each staged candidate (four invocations). Both variants
selected shipping on the authored parcel example. This is an integration check,
not a new accuracy or warmed-up latency benchmark. No weights/runtime code changed.

The portable `tools/generate_synthetic.py` in the release package regenerates both
authored datasets using only the Python standard library. All eight dev,
calibration-fit, calibration-policy and final-test files match their original
SHA-256 exactly. Pairing and equal EN/IT counts pass. Synthetic train has 4,096
records for v2 and 2,048 for v3; replay must be added separately to reach 8,192.
Full base-data reconstruction and a portable training launcher remain separate
unfinished work; the package does not claim otherwise.

The source/document preparation archive is
`releases/nesso2-decision-preparation.tar.gz`, containing 89 manifest-listed files
plus its manifest. SHA-256:
`08a4b3be26543ac66ad448343e711e9f939769f3aeaf59aad04bb9b474a9047c`.
Weight files stay on LUMI. Final candidate file manifests identify all packaged
files; the previous assembly manifests are preserved before documentation refresh.

## What must accompany a public release

1. Selected model identity, parent revision, adapter/head configuration, final
   hashes and verified exported-runtime equivalence.
2. Full build recipe plus adaptation recipe, exact source snapshot/patches,
   data revisions, filters, split seeds, translation provenance and review scope.
3. Complete result tables with sample counts, metric definitions, chance levels,
   coverage exclusions, checkpoint-selection history and unsuccessful experiments.
4. Calibration protocol and distribution-shift limitations. Do not describe a
   softmax probability as a guaranteed probability of correctness.
5. Hardware, dependency versions, measured runtime conditions and compute budget.
6. Kev/parent attribution and dataset metadata, with redistribution terms resolved
   for any material actually included. Some source manifests record unknown terms.
7. A minimal build/inference example with site paths parameterized. The current
   LUMI scripts are operational wrappers, not yet a universal one-command release.

Do not silently choose a new winner using the final test, omit failed runs, or
replace old reports. Append newly verified results with their source artifacts.


## 2026-10-11 — Private Nev publication

Published both standalone evaluated variants to `giux78/nev` in `v2/` and `v3/`,
revision `c5c84121263b423f8846811a24790ab96e66cee3`. Remote weight sizes/LFS SHA-256 and repository privacy were
verified; evaluated core model hashes are unchanged. Code, model descriptions,
recipes and experiment evidence were published to the existing private
`mii-llm/nev` repository (initial code commit
`68ee8ae5642f99bd9c0e8636280cc1f7438e6abd`). The model receipt is retained in
`evidence/huggingface-publication.json`. Existing LUMI credentials worked; no
A100 transfer was needed. The initial upload launcher stalled in module setup;
using the same container without GPU-binding module startup resolved it.


## 2026-10-11 — Hugging Face download and LUMI command check

Downloaded both private variants from pinned HF revision
`c5c84121263b423f8846811a24790ab96e66cee3` to the scratch cache. New
`examples/hf_decide.py` and LUMI launchers ran the frozen runtime on one AMD
GPU per job (v2: 22720431; v3: 22720432). Both English/Italian parcel examples
selected shipping; all answer probabilities exactly matched the preceding
local-export smoke results. Raw outputs and job IDs are in
`evidence/hf-demo-results.json` and `evidence/hf-demo-jobs.json`.

This validates HF download plus the native decision runtime. The published
configurations have `model_type=decision_model` and no `auto_map`; direct
Transformers AutoModel support is not implemented. It would require a custom
configuration/model wrapper and equivalence checks, not additional training.
The helper accepts a custom state or a JSON state/questions request. These
four examples are an inference smoke check, not a benchmark score or latency
study.


## 2026-10-11 — Harder bilingual diagnostic examples

The user rejected the trivial parcel routing smoke example as uninformative.
Added 20 authored EN/IT requests with four simultaneous decisions and five
one-fact contrast pairs per language. Job 22720810 compares frozen v2/v3 with
native cached FP32 inference. V3 routing was 9/10 EN and 5/10 IT (v2 7/10 and
5/10). Both variants answered false on every refund and escalation case: 8/10
merely matches the always-no baseline and misses all positive cases. Correct
changed decisions on both sides: v2 0/7 EN, 1/7 IT; v3 1/7 EN, 0/7 IT.
High-confidence errors are retained. Full results are in
`evidence/scenario-results.json`. This tiny correlated diagnostic is not a new
representative benchmark. Do not train on these cases then report them as fresh
independent evaluation.

Before inspecting predictions, superseded job 22720790 to correct an irrelevant
60-days-since-delivery default that contradicted missing-parcel cases; replaced
with null, leaving answer keys unchanged. Correction provenance is retained.


## 2026-10-11 — Consolidated project README

Replaced the navigation-first README with a self-contained long-form account of
Zagreus pretraining from scratch, Nesso2 knowledge/context/agentic stages, and
Nev decision conversion, balanced bilingual training, adaptation experiments,
actual-export comparisons, policy-following failures, inference and LUMI usage.
Earlier-stage claims are attributed to the pinned Nesso2 card; retained decision
metrics were checked against machine-readable evidence. Three deep-dive links
remain, with historical documents preserved as supporting records.
