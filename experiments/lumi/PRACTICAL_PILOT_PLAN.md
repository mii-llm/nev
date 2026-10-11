# Practical bilingual pilot, 9 October 2026

User authorized a fresh practical evaluation, confidence and runtime measurements,
and a bounded targeted experiment from checkpoint 74k. Default application is
support routing and explicit policy/action rules, pending any user preference.
Use LUMI only; all remote artifacts stay under project 465002563 scratch.

This first pilot uses controlled synthetic rules, not real customer traffic.
Four equally weighted families cover routing with priority rules, refund approval
and missing information, deadline urgency, and human escalation. Bilingual
templates are authored together with executable gold. They include boundary
conditions and negation. No teacher service or new model download is needed.

Each family has 256 training, 64 development, 128 calibration and 128 final-test
fact configurations, each in both languages. Complete fact configurations are
disjoint across splits. Test instructions use held-out paraphrases; all splits
share the same four rule families. This does not establish generalization to
unseen rule families, arbitrary prose, or real-world class frequencies.

The training set combines 2,048 new records and 2,048 original-training replay
records sampled approximately equally across the nine original sources. Exactly
half of every optimizer update is English and half Italian. There are 512
updates, accumulation 8, one pass, LR 1e-5 with 32-update warmup, FP32 weights
and BF16 autocast. Both LoRA and the head are explicitly trainable; loader
equivalence and first-update parameter changes are checked before proceeding.
The original model, training data and existing checkpoints are not modified.

Evaluate at 0, 128, 256, 384 and 512 additional updates. Checkpoints 74k and 142k
are controls. Follow-up eligibility requires original-dev task/language macro
NLL no more than .05 above 74k and no language accuracy drop over 2 percentage
points, on a fixed guard sample of up to 16 bilingual pairs per source. Among
eligible snapshots and controls, select minimum new-dev task/language macro NLL.
Ties prefer 74k. Failed follow-ups do not replace either original checkpoint.

Fit temperature only on calibration, with one value shared across languages.
Select the highest-coverage threshold from a fixed grid that has at least 30
accepted calibration cases per language and a Wilson upper error bound <=10%
for each language. If none qualifies, report escalation for all cases. This is
an exploratory calibration policy, not a production risk guarantee, especially
after threshold search. No larger-model escalation is actually executed.

Freeze selection and calibration before opening test for scoring. Report both
controls and the best eligible adaptation: accuracy, NLL, ECE, confident mistakes,
accepted coverage/error rate, separate English/Italian results, single-request
median/p95 latency and peak allocated GPU memory. Timing includes tokenization,
excludes loading/network, and uses warmup on the allocated LUMI GPU. Test outcomes
are confirmatory for the preselected candidate, not another selection round.

CPU preparation checks exact-request overlap against original training, paired
splits, schema/context admission, data hashes, runtime and checkpoint hashes.
GPU execution depends on successful preparation. One GPU, 3-hour allocation cap;
this cap is not an ETA. Restart snapshots save optimizer/scheduler/RNG every 128
updates. Results and checkpoints remain private in the isolated experiment.

Local checks: six focused regression tests for gold boundaries, bilingual split
isolation, calibration/abstention and per-language regression guards; Python and
batch-shell syntax checks. GPU correctness remains subject to the actual run.

Submitted on LUMI: preparation **22672695**, dependent GPU pilot **22672696**.
Remote directory:
`/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/practical-pilot-v1`.
`jobs.json` journals submission; `manifest.json` appears after CPU preparation.
GPU outputs are `training/progress.json`, `results/selection.json`,
`results/calibration.json` and, only on full completion, `results/report.json`.
Logs are `kev-nesso2/logs/practical-prepare-22672695.log` and
`kev-nesso2/logs/practical-pilot-22672696.log`.
