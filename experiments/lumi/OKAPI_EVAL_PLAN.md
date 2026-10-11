# Small external bilingual evaluation

The October 3 diagnostic uses the best checkpoint selected by the existing
training development loss. It copies that checkpoint before scoring external
data. Training continues unchanged on its own GPU. These external labels must
not enter training, calibration, or checkpoint selection.

## Frozen panel

| Task | Source split | Questions per language | Sampling |
|---|---|---:|---|
| MMLU | Okapi test | 228 | Four per each of 57 subjects |
| HellaSwag | Okapi val | 200 | Deterministic hash sample |
| ARC-Challenge | Okapi test | 200 | Deterministic hash sample |

There are 628 matched source IDs and 1,256 requests, exactly half English and
half Italian. Only source IDs present in both languages are eligible. Seed is
20261003. Malformed records exclude the whole pair before sampling. Each
language retains its own answer order and gold label: Okapi translations can
reorder options, so equal question IDs do not imply equal answer letters.

Sources are the existing `alexandrainst/m_mmlu`, `m_hellaswag`, and `m_arc`
datasets referenced by `lm_eval/tasks/okapi`. No new translations are generated.
Data revisions, downloaded file hashes, selected IDs, exclusions, copied model
hashes and code revisions are recorded in the manifest. All remote files remain
under `/scratch/project_465002563/decision-models/kev-nesso2/`.

## Interface and comparisons

- Decision Index's actual `choice_row` builder creates the typed requests; its
  actual `Engine` interface and `validate` check the responses.
- The custom decision engine uses the frozen training renderer and saved
  LoRA/pointer head, FP32 parameters with BF16 autocast and temperature 1.
- The unchanged Nesso parent uses Decision Index's stock TransformersEngine,
  BF16 and its fixed chat template, scoring option-key log likelihoods. This is
  an end-to-end baseline, not an architecture-controlled experiment.
- Okapi's pinned preprocessing functions clean ARC and HellaSwag. MMLU keeps
  its source question/options. HellaSwag adds one fixed language-appropriate
  continuation instruction; its activity labels may remain English as upstream.
- No few-shot examples, prompt tuning, truncation or option filtering. Capacity
  refusals remain in the denominator as wrong. Unexpected runtime failures stop
  the job rather than silently dropping questions.

Report task-by-language accuracy, Wilson 95% intervals, chance accuracy,
chance-corrected accuracy, coverage, and uncalibrated NLL. Preserve per-question
predictions. With roughly 200 questions per cell, differences of a few percentage
points are noisy; intervals also do not account for translation/subject effects.

This is a **custom exploratory subset**, not a complete Decision Index score or
an official lm-evaluation-harness result. In particular, it does not compute
lm-eval's continuation-length-normalized `acc_norm` for HellaSwag/ARC, and the
MMLU subject-balanced sample differs from full-test micro weighting. MMLU and ARC
are reported by Decision Index but excluded from its current composite index.
No composite leaderboard score will be generated or published.

Exact normalized whole-field matches against our decision-training inputs are
checked before the run. This does not rule out partial/semantic duplication or
unknown parent pretraining contamination. Okapi translation quality is not
certified; results are diagnostics, not native-Italian benchmark certification.

## Execution

`prepare_okapi_eval.py` freezes the data and best checkpoint. `okapi_eval.sbatch`
runs a 12-request smoke test for both models, then the complete small panel on
one separate LUMI GPU with a 90-minute allocation limit. The output directory is
`runs/bilingual-all-v1/decision-index-okapi-v1/`; predictions and reports are under
`smoke/` and `results/`. Reusing an existing output directory is rejected to avoid
mixing runs. Further runs require explicit new output directories.

Four local unit tests cover language-specific answer permutations, missing
option slots, multiline source JSON/duplicate IDs and coverage-adjusted scoring.
The GPU smoke test additionally checks real model loading and response schemas.

## Submitted run

LUMI job **22507706** evaluates the copied **step-74,000** checkpoint. Preparation
produced all 1,256 requests and found zero exact training-field overlaps. Pair
validation excluded 29 MMLU, two HellaSwag and two ARC pairs before sampling.
The job completed successfully in 4 minutes 37 seconds with full coverage for
both models. Accuracy by language is recorded below (checkpoint step 74,000).

| Task | Decision EN | Parent EN | Decision IT | Parent IT |
|---|---:|---:|---:|---:|
| MMLU | 31.14% | 24.12% | 33.77% | 26.75% |
| HellaSwag | 32.00% | 27.00% | 31.50% | 23.00% |
| ARC-Challenge | 30.00% | 21.50% | 29.00% | 22.50% |

## Laya multilingual comparison

The same frozen panel and existing predictions are reused. Laya native code is
pinned to `fa9a2a7070b1789912a49ae24603bbfb1a78b001`; the requested
`convaiinnovations/laya-multilingual` model is pinned to
`e4e9ddf21a7b1903b7acffd8814ad4307bf63a67`. Files, caches, predictions and audit
reports remain on LUMI scratch. No dependency changes are made to the training
environment: the Laya checkout is imported directly in the evaluation process.

`laya_okapi_eval.py` uses the official inference API, shipped temperatures and
fixed public overrides `max_len=8192`, `head_max_len=8184`. It retains Laya's
hardcoded 48-token option cap. These larger context budgets do not change model
weights or rendering; they differ from its shipped 1024/256 budget defaults.
Before inference, actual native token IDs are compared with an untruncated
reconstruction of the native layout. Any difference is a capacity refusal, not
a shortened model input. All requested options remain intact or the whole request
is refused. Refusals count as wrong in the full-panel metric.

The real-tokenizer preflight checked short inputs, long options, and long
instructions. Coverage before model inference:

| Task | EN supported | IT supported |
|---|---:|---:|
| MMLU | 228/228 | 225/228 |
| HellaSwag | 142/200 | 88/200 |
| ARC-Challenge | 200/200 | 200/200 |

Reports include full-panel accuracy/coverage, comparison on the exact Laya-supported
rows for every model, and a bilingual common subset requiring both translations
to fit. That final subset allows EN/IT comparison on matched source IDs, but its
shorter options make it a selected sample rather than the full benchmark.
Outputs are in `decision-index-okapi-v1/laya-results/`. The live trainer and the
prior Nesso evaluation artifacts remain unchanged.

Submitted as LUMI job **22508012** with one GPU and a 45-minute allocation cap.
The first scheduler check showed `PENDING (Priority)`; no Laya model scores were
available at that check.

## October 4 checkpoint repeat

LUMI job **22523244** evaluates the copied **step-102,000** checkpoint, selected
solely by the existing training dev NLL (0.54233). The original panel is copied
byte-for-byte into `runs/bilingual-all-v1/okapi-checkpoint-review-20261004/`.
The new manifest binds the copied checkpoint, evaluator source and baseline
artifacts by SHA256. `repeat_okapi_eval.py` runs the existing evaluator and writes
`comparison.json` with the current and step-74,000 decision models, original
Nesso, and Laya. The latter baselines reuse their saved predictions on identical
IDs and gold labels, checked before aggregation. The original parent is also
rerun by the existing evaluator, with its new results retained separately.

Both full-panel and bilingual common-supported comparisons are produced. This
is a repeated external diagnostic, not a new independent test. One separate GPU
is requested with a 30-minute allocation cap. Live training is unchanged.

## Latest-snapshot degradation check

Job **22531933** uses the actual latest recovery snapshot captured at step
**123,500**, rather than the dev-selected best at step 118,000. Output directory:
`runs/bilingual-all-v1/okapi-latest-review-20261004/`. The atomic snapshot is copied
through an open file handle, hashed, and checked against the frozen code/data
identity. The evaluator restores its exact trainable tensors and saves an adapter
for the unchanged evaluation path. No optimizer updates are performed.

The comparisons include both earlier checkpoints, 74,000 and 102,000. Accuracy
change intervals use 10,000 deterministic bootstrap resamples of source pairs,
keeping English and Italian translations together. These quantify uncertainty
within this diagnostic sample and do not establish a population-wide benchmark
claim. A regression test verifies that opposite EN/IT changes within every pair
produce a zero-width combined interval and that mismatched IDs are rejected.

Before the latest run, the observed step-102,000 minus step-74,000 accuracy change
was -2.87 percentage points (paired 95% interval -4.78 to -0.96). English changed
-1.91 points (-4.46 to +0.48); Italian changed -3.82 (-6.53 to -1.27). The initial
scheduler state for the latest run was pending for priority; latest model scores
were not yet available at that check. Training continues unchanged.

## October 5 latest-snapshot evaluation

Job **22546142** evaluates the actual recovery snapshot at **step 154,000** on
the same 1,256 requests. Output directory:
`runs/bilingual-all-v1/okapi-latest-review-20261005/`. The frozen manifest includes
the previous step-123,500 predictions as well as 74,000, 102,000, parent and Laya
results. It checks matching input hashes, record IDs and gold labels before
comparison. Full-panel EN/IT scores, bilingual common-supported scores, and
paired accuracy-change intervals are generated by the existing evaluator.
Training is not modified; the job requests one separate GPU for up to 30 minutes.

References:
- https://github.com/apolinario/decision-index/tree/87d4650b42b377c0291a89c1f1a879f9b31082bf
- https://github.com/EleutherAI/lm-evaluation-harness/tree/d6de81643928d653435c431bae19945d41d32520/lm_eval/tasks/okapi
