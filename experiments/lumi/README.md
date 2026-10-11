# LUMI Nesso2 decision-model experiments

Current project record: [Nesso2 experiment log](../../docs/nesso2/EXPERIMENT_LOG.md).
The full run and practical v1 are complete. Practical v2 addresses wording
generalization and uses disjoint temperature/threshold calibration splits.
The log and [build record](../../docs/nesso2/BUILD_RECIPE.md) supersede dated job
status statements below while preserving the historical record for publication.

## Full-corpus launch, October 1

GPU proof `22466453` completed in 14m05s: resumed and uninterrupted training
matched exactly across all 452 trainable tensors (`max_parameter_delta=0.0`),
with matching scheduler/RNG/progress. Initial launcher `22466532` failed before
submitting jobs because LUMI's host Python 3.6 does not support `subprocess(text=)`.
The compatibility fix uses `universal_newlines`; the first training job is gated
by the verified proof artifact rather than a completed Slurm ID that can expire.
The empty submission journal was explicitly recovered without duplicating jobs.

Full gold training was submitted as segments `22472039`, `22472040`, `22472043`,
`22472044`, `22472045`, `22472046`, `22472047`, `22472048`, followed by finalization
job `22472049`. The durable job journal is `runs/bilingual-all-v1/full-training-plan.json`.
These are continuation segments of one two-epoch run, not eight separate models.

Translation job `22442675` completed in 22h05m. Its original `data/` contains
714,608 training records (357,304 per language). All outputs remain under
`/scratch/project_465002563/decision-models/kev-nesso2/`.

A semantic spot review inspected 36 EN/IT pairs across the nine train/dev source
families. It found `returns` mistranslated as `residui`, a BoolQ brass-knuckles
question translated as boxing gloves, and unchanged English NLI hypotheses inside
Italian prompts. The separate `review_full.py` stage preserves the original data,
corrects exact known schema strings (also bare entailment/contradiction labels),
and excludes whole paired groups with untranslated quoted NLI hypotheses of at
least four words. It does not subjectively change source labels. Suspicious SST5
labels were checked against the cached pinned dataset and match its `label_text`.
This is limited machine-assisted semantic review, not native-speaker certification.

Review job `22466271` completed. `data-reviewed/` has 713,198 training records
(356,599 EN + 356,599 IT), 102,298 dev, 102,472 calibration, 104,950 test,
344 showcase and 570 unseen. Its manifest is
`6410cdcf4157ec1e849dd62f7afec217a9fe7e27342d8509ecc749030464f6da`.
The review log and manifest record all exclusions and correction counts.

`train_full.py` uses the existing Kev loss, augmentation, LoRA/head and pinned
Nesso2 parent. The first full run is gold-only, the stronger pilot variant. Every
optimizer update remains exactly balanced IT/EN, and all retained train records
are visited once per epoch for two epochs. The natural source mixture is about
72% MNLI; source balance is not claimed. Checkpoint selection uses a fixed paired
dev sample of up to 64 pairs per source and macro source/language record NLL.
It evaluates at step zero, every 2,000 updates and epoch boundaries. Test and
calibration are never loaded by this trainer.

Atomic `latest.pt` snapshots every 500 updates and at planned pauses save all
trainable weights, optimizer moments, OneCycle scheduler, progress and CPU/GPU
random states. Per-epoch order and option permutations are deterministic. Resume
rejects different code, recipe, reviewed manifest or dev samples. Long jobs stop
after 22 hours within a 24-hour allocation and continue from the next update.

Eight CPU regression tests passed, including exact interrupted/uninterrupted
dropout+AdamW equality and split/translation guards. Actual-model GPU proof job
`22466453` compares 16 updates, process restart, and 16 more updates against an
uninterrupted 32-update run, with LoRA dropout enabled. Full training must depend
on successful completion of this proof. No multi-GPU speedup is assumed.
The first GPU proof (`22466314`) stopped before training because `/scratch` and
its resolved `/pfs/lustrep4/scratch` alias were mixed in the code-hash path check;
the trainer now resolves both consistently. Its three resume/selection tests
passed again after the fix. A separate launcher regression also passed: a partial
Slurm submission is journaled and a repeated launch cannot duplicate jobs.

`launch_full.py` requires a passing proof tied to the exact reviewed manifest,
review file and trainer code. It freezes the source and batch environment under
`training-source/`, journals every submitted job, and can chain up to eight
22-hour training segments plus final calibration/export/evaluation. All segments
resume one run; once its two epochs are complete, later segments exit without
additional updates. Failed dependencies cancel later stages instead of silently
continuing from incomplete work.

`finish_full.py` requires completed training, calibrates using only the separate
calibration split, exports and checks the merged BF16 artifact, and evaluates both
the original pilot test/unseen panels (for comparison with released Kev results)
and the full reviewed test/unseen panels. It does not upload or publish the model.

## Training audit and larger-data work

The user requested an audit of the large accuracy gap and training on all available
source data. The 1,684-record run was a compatibility/quality pilot, not full training.
It cannot establish Nesso2's attainable performance with a complete training corpus.

Audit job `22436518` completed its checks. On 72 source/language-stratified training
records (120 questions), selected-checkpoint accuracy was 40.8% in FP32, 41.7% with
BF16 autocast, and 41.7% for the BF16 export. Eight predictions changed on export,
so precision is measurable, but does not explain the overall gap. Packed/rows/cached
probability differences were below 6e-7 on the checked request.
All 448 adapter tensors and four head tensors updated, with finite nonzero gradients
(LoRA A starts with zero gradient when B is zero, then receives nonzero gradients).
The actual loss/augmentation/forward path memorized eight clean IT/EN examples:
100% accuracy and NLL 0.00245 by 100 constant-LR 5e-5 updates; at 5e-4, 100% and
NLL 0.000430 by 25 updates. These are diagnostic training-set results, not quality
estimates or a basis for choosing a final learning rate.

The five Llama reserved delimiter embeddings are nearly identical (pairwise L2
distances 0.004–0.012, each norm about 3.57). This is a possible optimization concern,
not a demonstrated training bug: the unchanged model still passes memorization.
No definitive training implementation error has been identified by these checks.
The saved audit and source snapshot are in `runs/training-audit-22436518/`.

`prepare_full.py` first built the complete checked-in recipe in
`runs/bilingual-full-v1/`: 8,119 English train records, 1,417 dev, 1,146 calibration,
2,359 test, 200 showcase and 300 unseen. Pairing would yield up to 16,238 training
records before Italian quality/context filtering. Translation job `22436592` completed
in 36m04s using the existing 35B vLLM setup, reviewed pilot cache and 44 overrides.
It translated 14,442 pending strings in 1,722 seconds (8.39 strings/second).
After automatic filtering, train has 7,495 EN + 7,495 IT records (14,990 total);
984 groups across all splits were rejected. Manual quality review is still pending.
This expanded recipe remains a sampled-source stage, not the final all-source corpus.

After the user's instruction to use more data, CPU job `22436613` was submitted
with `prepare_full.py --all-source-rows`, output `runs/bilingual-all-v1/`. It considers
every raw training row in the six pinned public sources, with no public-source
training cap; retains label/context and official-overlap filtering and grouped
70/10/10/10 splits; checks exact duplicate requests/conflicting labels; and expands
finite policy generation tenfold. Prior pilot holdout groups, normalized source
text hashes and source-row identities are excluded from new training. Test/unseen
examples remain excluded. Actual accepted counts are recorded when preparation ends.
Cached pinned source metadata supports offline CPU preparation on LUMI.

The first all-source job failed after 11m13s on the active split-isolation guard:
tenfold contrastive generation repeated a normalized state across train and dev.
An opt-in policy filter now drops every whole generated group involved in such
cross-split collisions, records the excluded group IDs/counts, and then runs the
unchanged guard. It never moves records across splits; public/custom collisions
still fail. Three regression tests passed on LUMI, including the actual tenfold
generator. The corrected preparation was resubmitted as job `22437801`.
Raw public training sizes total 546,128 rows: AG News 120,000; TREC 5,452;
Banking77 10,003; BoolQ 9,427; MNLI 392,702; SST5 8,544.

Provisional runtime estimate at the September 29 status check: preparation about
15–25 minutes after allocation, full translation roughly 18–30 hours based on the
measured rate (unique-string count still pending), and one two-epoch student run
roughly 100–130 hours at the pilot's single-GPU rate. These are extrapolations,
not a scheduled completion time; queue delays, quality review, teacher targets,
resumable-training changes and different sequence lengths can change the total.
An initial full-run planning range is 6–8 days excluding queue delays. Multi-GPU
student scaling has not been implemented or measured and is not assumed here.

September 30 (Europe/Rome) follow-up: job `22437801` passed split isolation but
failed after 13m42s at conflicting gold labels for an identical MNLI request
(`mnli/train/131771`). No student training or full-source translation ran during
the resulting gap. `corpus_filters.py` now excludes every group involved in an
identical-request label conflict, including siblings; it also applies prior
holdout exclusions to whole groups. No labels are guessed or overwritten.
Five regression tests passed on LUMI. Job `22442668` resumes postprocessing of
the saved English corpus after verifying all file checksums and recipe identity.
Translation job `22442675` was submitted with an `afterok:22442668` dependency,
the existing eight-GPU 35B vLLM setup, and a 36-hour allocation. Successful
preparation therefore automatically releases translation to the scheduler.
Training remains unsubmitted; translation quality review is still required.
The resumed preparation completed successfully in 1m12s: 398,021 English train
records, 57,153 dev, 57,151 calibration, 58,535 test, 200 showcase and 300 unseen.
English manifest SHA256: `5ead4d2a10abf65211ebad5b5f523c90095f0510c4b9cc7fce05224c1b85de9d`.
Translation job `22442675` has started its allocation. The paired training corpus
will contain up to 796,042 records before Italian quality/context exclusions.

All new data and caches remain under project scratch. No full-size student training
has been launched yet: the expanded translations need review first. Large-corpus
training also needs a bounded validation schedule and resumable jobs sized from
measured token counts; the pilot's two-hour job and frequent full-dev passes must
not be reused unchanged for hundreds of thousands of examples.

## Published Kev reference evaluation

The IluvatarLabs checkout does not contain pretrained reference weights. The
requested comparison uses published models from the separate
[`jaredpalmer/kev`](https://github.com/jaredpalmer/kev) implementation:

- `jaredpalmer/kev-0.8b@9a45d25eb2ab761841196625383fa1dff0e56c1e`
- `jaredpalmer/kev-4b@139fdd94f1b6a6ad80cc15e08fcb99cac885a101`

Runtime source is pinned to `0fe8fc97c2bcc247fa3efb6e5c32af4e99770e91`, stored
under the scratch workspace's `references/jaredpalmer-kev/`. The model manifest
there pins each adapter, head and base revision. All downloads use the project's
existing scratch cache. `eval_kev_reference.py` uses the reference renderer and
checkpoint loader with FP32 weights, SDPA math, no autocast and the shipped
temperature. It does not refit or train on our test data. Strict encoding prevents
silent truncation; rejected records and common question coverage are reported.

Evaluation jobs `22436239` (0.8B, 2m23s) and `22436240` (4B, 4m15s) completed
successfully on the unchanged `bilingual-v2` test and unseen splits. Neither
model rejected any record. The runtime used its correct PyTorch DeltaNet fallback
because flash-linear-attention was absent. Summary job `22436246` was cancelled
while pending; the brief CPU-only aggregation was run directly on the login node.
Artifacts go to `runs/bilingual-v2/kev-reference/`, including per-question outputs,
`comparison.json`, paired group bootstrap intervals and `comparison.md`.

The comparison separates the full test, official-public-test-only and unseen-source
panels. Our reserved training-pool rows may overlap released Kev training, so full
test scores are not guaranteed independent for the references. Even official test
rows cannot rule out pretraining or prior evaluation exposure. Published Kev has a
larger backbone and much more training data. Its FP32 inference also differs from
our BF16 exports. This is a comparison of finished models, not an architecture or
training-recipe ablation. Italian remains synthetic.

Measured question accuracy (full test: 341 questions per language, including
Banking77; unseen: 57 questions per language):

| Model | Test EN | Test IT | Unseen EN | Unseen IT |
|---|---:|---:|---:|---:|
| Nesso2 gold-only | 38.4% | 36.4% | 42.1% | 33.3% |
| Nesso2 distilled | 37.0% | 34.6% | 38.6% | 33.3% |
| Published Kev-0.8B | 80.4% | 73.6% | 66.7% | 45.6% |
| Published Kev-4B | 84.8% | 80.1% | 75.4% | 73.7% |

On official test/validation rows only (129 questions per language), accuracy is
42.6% EN / 38.8% IT for Nesso2 gold-only, 85.3% / 81.4% for Kev-0.8B, and
83.7% / 79.8% for Kev-4B. Thus the large gap is also present after excluding our
reserved training-pool, policy and custom records; it does not rely only on that
potential overlap. The 0.8B/4B ordering varies by panel, so this is not a universal
ranking. Peak GPU allocations were 3.20 GiB (0.8B) and 16.47 GiB (4B).

## Representative bilingual pilot (bilingual-v2)

The first corpus (`bilingual-v1`) was **rejected for training** after a paired
review found changed negations and premise/hypothesis semantics in 4B-model
translations. It remains on scratch for diagnosis. No larger training run used it.
The replacement uses the user's existing vLLM setup and cached
`Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`.
Translation job `22433700` completed successfully on 2026-09-29 in 11m05s.
The final corpus has 842 EN + 842 IT training records, 173+173 development,
108+108 calibration, 247+247 test, 49+49 showcase and 57+57 unseen records.
111 semantic groups were excluded by translation/context checks. A paired
sample of 36 train/dev records was reviewed, and 44 reviewed terminology/text
corrections in `italian_schema.json` were applied. The review is explicitly for
this exploratory pilot, not exhaustive semantic verification. Its manifest SHA
is `d03e35cc394154c244658b4182e2b31835fa063d1649df15fa4a3bc118fa0b54`.
The small calibration split has no compositional-policy examples.
Teacher comparison/target collection completed successfully as job `22434162`
in 6m09s. All 1,684 training records were processed; target scoring evaluated
8,376 option layouts / 1,555,332 tokens in 166 seconds.
The distilled student (`22434201`, 19m02s), gold-only control (`22434203`, 18m43s),
language-model baselines (`22434204`, 3m42s) and CPU summary (`22434392`, 5s)
all completed with exit code 0. Both students completed 422 updates / two epochs,
with 5.52 GiB peak training GPU allocation. Calibration, BF16 export and evaluation
completed. `summary.json`, `summary.md` and `SELECTED_MODEL.txt` are in the experiment
directory. Development selection chose **gold-only**, with exported raw macro
record NLL 1.4713 versus 1.4775 for distillation.

Held-out accuracy on the common eligible questions (303 per language, excluding
Banking77 from every system for comparability):

| System | English | Italian |
|---|---:|---:|
| Original Nesso2, cyclic language-model scoring | 41.9% | 41.3% |
| Gold-only decision model | 42.9% | 40.9% |
| Nesso-4B-distilled decision model | 40.9% | 38.9% |
| Nesso-4B teacher, cyclic language-model scoring | 74.6% | 71.6% |

Full test accuracy including Banking77 (341 questions per language) is 38.4% EN /
36.4% IT for gold-only and 37.0% / 34.6% for distillation. On unseen sources (57
questions per language), gold-only scores 42.1% / 33.3%, distillation 38.6% / 33.3%.
The full-test paired bootstrap intervals for distilled-minus-gold accuracy include
zero in both languages. There is no demonstrated accuracy gain over the original
Nesso2 baseline and no clear distillation benefit in this pilot. Multiple-choice
decisions are especially weak; gold-only Banking77 accuracy is 1/76 questions.
The adaptation runs successfully, but these artifacts are not ready for deployment.

The selected artifact is `runs/bilingual-v2/gold/model/`. FP32 adapter merge and
same-dtype save/reload checks passed. BF16 conversion changed one argmax among
20 export-check questions for each model; maximum probability changes were 0.0554
(distilled) and 0.0734 (gold). Reported accuracy measures the actual BF16 exports.
Before scaling, diagnose learning on a small clean training subset and compare
training-set accuracy, optimization settings and FP32/BF16 inference. The current
results do not establish whether data size, optimization or model capacity is the
main limitation.

The completed development comparison selected **Nesso-4B** on 298 eligible
questions per language. Its source/language macro record NLL was 1.0894 versus
Qwen-4B's 4.0458. Question accuracy was 72.5% EN / 72.1% IT for Nesso and
72.8% EN / 69.8% IT for Qwen. These are development results used for selection,
not final test estimates; Qwen's similar accuracy but higher NLL reflects more
costly probability errors under this scoring setup.

`prepare_pilot.py` retains Kev's six public training sources, executable policy
families, custom support tickets, and three unseen evaluation sources. It uses
160 candidate train rows per public source, at most 100 accepted training rows
per source, a 160-record policy training cap, and smaller held-out panels.
Dataset revisions remain those pinned by the original recipe.

| Source | Decision task | Role |
|---|---|---|
| AG News | News topic and topic membership | Training and held-out splits |
| TREC | Question/answer type | Training and held-out splits |
| Banking77 | 77 banking intents | Training and held-out splits; gold-only |
| BoolQ | Passage-based yes/no QA | Training and held-out splits |
| MNLI | Entailment, neutral, contradiction | Training and held-out splits |
| SST-5 | Five-level sentiment | Training and held-out splits |
| Kev composition/contrastive generators | Executable policy decisions | Grouped splits and held-out rule structures |
| `data/custom/support_tickets.jsonl` | Customer-support decisions | Training and held-out splits |
| PAWS, QNLI, Emotion | Paraphrase, answer containment, emotion | Unseen-source evaluation only |

Before translation filtering, the English pool has 909 train, 179 development,
118 calibration, 274 test, 54 showcase and 60 unseen records. Accepted records
are paired with Italian, so the final counts depend on translation/context checks.

`bilingual_data.py` pairs each English record with Italian in the same split and
group. `vllm_translate.py` translates human-readable values with the pinned 35B model;
question/option IDs, order, types, labels and metadata are preserved. Null choice
descriptions become explicit descriptions from the ID in both languages.
Compositional-policy Italian is rendered from executable gold certificates.
Failed numeric, question-punctuation, structural or context checks remove the entire semantic group
in both languages. A cache supports restarting translation, and a deterministic
train/dev audit sample is written before teacher selection. Translation prompt
`vllm-quoted-fewshot-v3` includes explicit examples of translating questions without
answering them and preserving numeric formatting. It tests previously failing
question strings before translating the remaining corpus. The initial prompt's
outputs are retained for diagnosis and excluded from the active dataset.
After translation, finalization applies reviewed terms and removes JSON quote
escapes introduced by the server when they were absent from the source text.

Italian is synthetic. Number/schema checks and a manual sample review cannot
prove every translation preserves the gold label. Translation style may bias
the teacher comparison. This is a pilot, not a
native-Italian benchmark or a production release.

`run_bilingual_pilot.py compare` compares Qwen against public `mii-llm/nesso-4B`
(revision `282a4a108541d2260a8bd721744e89fe5b7c8340`) on development data only.
Selection minimizes NLL averaged within records, then equally over source and
language cells. Both teachers must cover the same questions. Banking77 retains
all 77 options and is gold-only because Kev's teacher supports at most 26.

The `distilled` and `gold` stages use identical seeds, data and two-epoch schedules;
the former uses 50% gold/50% teacher loss on eligible questions. Both retain 50%
Italian/50% English **record/loss weight in every optimizer update**, not equal
token counts. Each selects a checkpoint on dev, fits temperature on calibration,
exports with merge/reload equivalence checks, and evaluates the BF16 export on
dev, locked test and unseen panels. Reports include per-language/source/primitive
accuracy, NLL, Brier score and ECE. The `baselines` stage evaluates the original
Nesso2 language model and selected teacher using cyclic label scoring; comparisons
with these baselines must use only their common eligible questions.

New artifacts are under the remote workspace's `runs/bilingual-v2/`. Translation
reuses `training/sbatch-vllm-qwen36.sh`'s native-container/TP=8 setup on one full
LUMI node. The actual installed native vLLM is `0.22.1+lumi_aif_gfx90a_0decac0`,
with Transformers 5.10.1. The serving process does not import Kev's overridden
Transformers environment. All 26 model shards are already cached under
`/scratch/project_465002563/training/hf_cache/`; the existing vLLM/Triton caches
are reused there. The server binds localhost and exits when the translation job
finishes. Training/comparison jobs each request one GPU, 48 GB RAM and at most
two hours; the translation job requests eight GPU devices and 480 GB RAM.

```sh
# From the remote workspace, after CPU preparation and model downloads:
sbatch src/experiments/lumi/translate_vllm.sbatch
# Inspect the preflight, translation-audit.jsonl and data/manifest.json.
# A completed quality review must record status=approved_for_pilot and the
# exact manifest SHA-256 in data/quality-review.json before comparison/training.
sbatch src/experiments/lumi/bilingual_pilot.sbatch compare
# After comparison and target collection complete:
sbatch src/experiments/lumi/bilingual_pilot.sbatch distilled
sbatch src/experiments/lumi/bilingual_pilot.sbatch gold
sbatch src/experiments/lumi/bilingual_pilot.sbatch baselines
# Once all three reports exist (or submit with their afterok dependencies):
sbatch src/experiments/lumi/summarize_pilot.sbatch
```

The scripts refuse to overwrite a nonempty training run. Keep completed outputs;
use a new experiment directory when changing data or training settings.

## Compatibility probes and environment

Use LUMI only, per the user's instruction. SSH uses the existing key:

```sh
ssh -i ~/.ssh/id_ed25519 ercolani@lumi.csc.fi
```

Remote workspace: `/scratch/project_465002563/decision-models/kev-nesso2`.
New experiment downloads, dependencies, temporary files, logs and outputs
belong under that workspace. The larger translator reuses the user's existing
model and serving caches under the same project scratch allocation. Reuse the
installed LUMI container read-only. Do not
change existing training environments, interrupt other jobs, or use the A100 host.

The copied Kev code is under `src/`; `env/` overrides Transformers and PEFT while
reusing the container's ROCm PyTorch and shared dependencies. `environment.sh`
specifies both package paths and container environment overrides. The container
image is pinned to the actual image inspected, rather than its `latest` symlink.

This probe loads the pinned Nesso2 checkpoint. The original exploratory mode
directly constructs the model and overrides delimiters in its own process;
`--integrated` (used by the current batch script) exercises the supported
`DecisionModel.from_parent` API and the automatic Llama delimiter profile.
It validates delimiter escaping, teacher label tokenization,
packed/rows/cached execution parity, question isolation, and finite nonzero
LoRA/head gradients. Training uses eight manually written examples, four in each
language, for ten gold-only optimizer updates. These are smoke-test examples,
not a development or test benchmark, and their loss is not evidence of task accuracy.
Integrated mode also tests checkpoint reload, LoRA merge and BF16 artifact reload.

`teacher_pilot.py` exercises the actual `targets.collect` and `train.train`
entry points with a separately pinned Qwen3-4B-Instruct-2507 teacher. It uses
eight train and eight development records (four per language in each split),
keeps translations together, and performs ten optimizer updates with 50% gold
and 50% teacher supervision. It is a pipeline test, not a teacher comparison or
held-out quality benchmark. Its exported model is uncalibrated and diagnostic.

After the model has been downloaded into the workspace cache:

```sh
cd /scratch/project_465002563/decision-models/kev-nesso2
sbatch src/experiments/lumi/probe.sbatch
# After caching the teacher and writing configs/teacher-qwen3-4b.json:
sbatch src/experiments/lumi/teacher_pilot.sbatch
```

The job requests one GPU on `small-g`, seven CPU cores, 32 GB host memory and a
15-minute maximum. It runs without Hub network access. Inspect
`logs/probe-JOBID.log` and `runs/probe-JOBID/report.json`; the latter records
versions, parameter count, parity deltas, gradients, losses and peak GPU memory.

Installation used an isolated virtual environment and `pip install --no-deps
transformers==5.17.0 peft==0.21.0 tokenizers==0.23.1`. Do not run the repository's default Linux
`uv sync` here: it selects NVIDIA PyTorch wheels. Validate imports before running
the probe, since package compatibility with the inherited container matters.

## Completed validation

- Combined model-port and bilingual-data regression suite: **10 tests passed**
  on LUMI, including preservation of IDs/labels, certificate-based Italian policy
  rendering, balanced sampling, independent teachers, and teacher-selection weighting.
- After adding the vLLM handoff, all four bilingual-pilot tests passed, including
  an additional cache-only finalization and review/checksum gate test (11 unique
  port/pilot regression tests in total).
- Exploratory probe: job `22400260`, completed in 1m59s; finite gradients, loss
  0.9371 → 0.7973 over ten updates; peak allocated GPU memory 2.75 GiB.
- Integrated probe: job `22419448`, completed in 2m28s including seven passing
  regression tests; maximum packed/rows/cached probability difference 1.44e-6,
  checkpoint reload difference 0, FP32 merge difference 1.12e-6 and BF16
  same-dtype reload difference 0. Measured on AMD Instinct MI250X, ROCm 7.0,
  PyTorch 2.10.0, Transformers 5.17.0 and PEFT 0.21.0.
- Independent-teacher pilot: job `22419480`, completed in 1m24s. Qwen3-4B-Instruct-2507
  revision `cdbee75f17c01a7cc42f958dc650907174af0554` supplied all 24 teacher targets
  across 56 option layouts. The normal Kev trainer completed ten updates with
  equal Italian/English record weight and a 50/50 gold/teacher mixture. Tiny-dev
  NLL decreased from 0.9366 after the first update to 0.8579 after the tenth;
  peak GPU allocation during student training was 2.72 GiB (excludes the earlier
  teacher collection phase). The checkpoint and uncalibrated diagnostic export
  are in `runs/teacher-22419480/`, with the exported files under `model/`.

These measurements cover short diagnostic requests only, not maximum contexts,
large batches, full bilingual accuracy, CPU deployment or quantized inference.

## Configuration additions

An independent teacher uses `teacher.model` and `teacher.revision`; omit both
to preserve the original parent-as-teacher behavior. Explicit teacher caches
include model identity, revision and input/settings hashes. The student remains
the top-level `parent` and `revision`.

Set `train.language_balance: {it: 0.5, en: 0.5}` for equal record/loss weight in
every update. This requires equal nonzero post-filtering record counts, `language`
tags on every record and an even `accumulation`; it fails rather than silently
dropping or duplicating data. Token counts are not guaranteed equal.

Custom JSONL accepts `language` and `group_id`. Give both translations the same
`group_id` within the same source family to keep them in one split. The default
English corpus does not become bilingual automatically; building and validating
the full bilingual corpus remains separate work.
