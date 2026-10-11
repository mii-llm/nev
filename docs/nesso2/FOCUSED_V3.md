# Focused v3: predeclared protocol

Date: 11 October 2026. Authorized follow-up to the completed v2/Laya comparison.
This document preserves the predeclared protocol. The run is now complete; see
[verified results](FOCUSED_V3_RESULTS.md).

## Starting point and training

Initialize selected practical v2 (original 74k + 256 updates), preserving its
adapter/head and all older results. Single LUMI AMD GPU; no external teacher.
Recipe: [nesso2-focused-v3.json](../../recipes/nesso2-focused-v3.json).

| Training component | Records | Purpose |
|---|---:|---|
| New synthetic routing | 1,024 | Priority, eligibility and boundary decisions |
| New synthetic intent | 1,024 | Latest-message intent with a distracting earlier request |
| Reviewed Banking77 training replay | 3,072 | Rebalance intent classes and practice 77-option decisions |
| Other original-source training replay | 3,072 | Retain broader decisions; balanced sampling across sources |
| Total | 8,192 | Exactly 4,096 EN and 4,096 IT |

The base model already trained on the full 713,198-record corpus. This is a
bounded adaptation, not a replacement for that training. The 6,144 replay records
are selected from original training data, not newly collected examples.
Every update has four English and four Italian records. The source mixture is
guaranteed over the corpus, not separately within each update.

Train LoRA + decision head with LR 1e-5, 32-update warmup, maximum 1,024 updates,
seed 20261011, FP32 weights/BF16 autocast. Save/evaluate every 128 updates.
Stop after at least 512 updates if three evaluations have no eligible dev-NLL
improvement. Preserve loss history, optimizer/RNG state and all evaluated snapshots.

## Data and limitations

Synthetic intent has **16 support intents**, with two-message conversations whose
final request determines the label. Choice order is shuffled identically across
an EN/IT pair. Each intent has two training utterances, another for development
and calibration, and an untouched final-test utterance. Earlier context in all
splits uses only training utterances. Distinct complete intent configurations
and distinct instruction banks are allocated to each split.

Synthetic routing excludes every complete fact configuration from every v1/v2
split. New facts and disjoint instruction banks are used for train/dev/calibration/
test. Its underlying rule family remains familiar. The state renderer is reused.
All bilingual wording is authored in the repository, not independently reviewed
natural customer traffic. Success on this 16-intent probe does not establish
transfer to the 151-option CLINC benchmark. No CLINC benchmark examples are trained.

Each development/calibration split contains 512 records (256/language). The
final test contains **1,024 records (512/language)**: 256 routing and 256 intent
per language. The final test is frozen before training and never scored for
checkpoint selection, temperature fitting, or threshold selection.

## Selection and regression guards

Compare development task/language macro NLL with unchanged v2. A candidate must
pass **both** guards independently relative to v2:

- Original development guard: up to 32 bilingual pairs per source (570 records).
- Practical v2 development guard: all 1,024 cases; the examined final test is not used.

For each guard, macro NLL may increase at most .05 and neither language's accuracy
may drop more than 2 percentage points. Lowest new-dev macro NLL wins among
eligible snapshots and unchanged v2; ties retain v2. If none qualifies, keep v2.
Final-test results do not retrospectively change this selection.

Temperature fitting and confidence-policy selection use separate 512-record
splits. The exploratory policy requires at least 30 accepted examples per
language and a Wilson upper error bound <=10%. No qualifying threshold means
abstain on every case, not zero model errors or deployment readiness.

## Automatic completion pipeline

After selection/calibration freeze, score v2 and the best eligible adaptation on
the new test. Run pinned Laya natively on the same cases, reject truncation and
report full and common bilingual support. Use its existing shipped temperatures;
do not tune Laya on our test. Any rounded-probability ties are recorded.

Prepare a **private FP32 merged export** of the dev-selected checkpoint on project
scratch, run merge and fresh-process reload checks, then measure its actual
predictions on the same final test and record argmax changes versus the adapter.
The export is a private candidate, not a public release. Confidence validation,
complete packaging/provenance and review of final results remain release gates.
No Hugging Face upload is part of the batch job.

Run directory:
`/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/focused-pilot-v3`.
`jobs.json` records submission. `training/progress.json` records training.
`results/report.json` means Nesso scoring completed; `results/comparison.json`
means Laya comparison completed; **`results/completion.json`** plus successful
Slurm exit is required to claim the entire pipeline completed.

All source/data/checkpoint hashes are frozen in manifests. The five local tests
cover pairing, label balance, untouched intent wording, exclusion of old routing
facts, request deduplication, disjoint instruction banks and regression rejection.
Full schema/token-capacity audits occur in the CPU preparation job before training.
