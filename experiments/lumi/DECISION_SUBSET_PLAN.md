# Broader bilingual evaluation preparation — 6 October 2026

The trained run is complete. On the original repeated Okapi diagnostic, checkpoint
74,000 scored 31.3% overall, while the dev-selected 142,000 and final 178,300 both
scored 29.4%. Those observations motivate a new panel; they do not make this panel
an unbiased final test if it is also used to choose a checkpoint.

## Panel and model selection

| Task | English source cases | Italian counterparts | Selection / confirmation pairs |
|---|---:|---:|---:|
| ANLI | 300 | 300 | 150 / 150 |
| CLINC150+OOS | 302 | 302 | 151 / 151 |
| When2Call MCQ | 300 | 300 | 150 / 150 |
| Total | 902 | 902 | 451 / 451 |

There are 1,804 requests in total, exactly 50% in each language. Each panel has
902 requests. English requests come from the existing Decision Index normalizers
at commit `87d4650b42b377c0291a89c1f1a879f9b31082bf`; only the three required
upstream datasets are downloaded. This is a custom stratified diagnostic, not an
official Decision Index composite or a full lm-eval run.

Sampling uses a fixed SHA256 order with seed 20261006: 100 cases per ANLI test
round, two per CLINC intent including OOS, and 100 per observed When2Call gold
class. CLINC is therefore intent-balanced, including a much lower OOS prevalence
than the original test set. When2Call has four options but only three gold classes
in this pinned test source: direct answer never occurs as gold. This limitation
is retained, not repaired by inventing examples.

Repeated premises, utterances or user questions cannot cross the selection and
confirmation panels. Exact benchmark text is checked against complete training
state/instruction fields. This limited check does not establish the absence of
paraphrase overlap or parent pretraining contamination.

The initial checkpoint comparison is 74,000 versus 142,000, with original Nesso2
and `convaiinnovations/laya-multilingual` as references. Choose using the equal
task-weighted mean of English and Italian selection accuracy, considering paired
uncertainty and coverage. Freeze that choice before opening confirmation results.
Do not refit temperatures on either panel. If confirmation disappoints, report it;
do not repeatedly select another model against the same confirmation cases.

## Italian and review

The existing LUMI vLLM setup serves the cached, pinned Qwen3.6-35B-A3B translator.
Only input strings are sent to it: no gold labels, checkpoint predictions or
scoring metadata. Tool names, parameter keys, schema types, enum values and
option IDs stay fixed. All 300 JSON tool-call answer strings remain byte-for-byte
unchanged; their argument literals are protected in surrounding prose too. Tool
descriptions, user questions and prose candidate responses are translated, with
placeholders protecting identifiers and inline code. There are 4,063 unique
label-free translation strings.

Automatic checks cover numbers, question marks, protected strings, request
schemas, pairing, option keys, unchanged gold labels, token capacity and duplicate
translated option descriptions. They cannot establish semantic equivalence.
Review `translation-review-sample.jsonl` (ten pairs per task), the complete shared
CLINC label vocabulary and any flagged strings/collisions before approving the
panel. Check negations and entailment relations particularly carefully. Italian
must remain labelled as a synthetic, partially reviewed extension.

`quality-review.json` must record `status: approved_for_diagnostic`, the exact
`panel_sha256` mapping from `manifest.json`, the reviewer, cases reviewed and any
remaining limitations. The agent can perform and record this review; this is an
artifact integrity requirement, not an extra user permission requirement.

## Implementation and preparation jobs

All remote files are under:

`/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/decision-index-bilingual-v1`

Scripts are staged in its `preparation-source/` directory. The existing training
source and completed evaluation artifacts are untouched.

- CPU acquisition/preparation: **22572352**, completed successfully in 20 seconds.
- Translation repair: **22573534**.
- CPU pairing/capacity/integrity audit, dependent on translation: **22573535**.

Translation job 22572620 processed all 4,063 strings in 10m58s including server
startup, then stopped on 143 flags: 110 number-format changes, 22 question-mark
changes and 11 protected-identifier changes. Its dependent audit was cancelled.
Inspection also found 3,726 valid JSON-string wrappers around translations. The
repair preserves all raw outputs and the prior scripts/manifest under
`preparation-history/before-translation-format-repair/`, decodes only valid JSON
string serialization, rechecks every string, and retranslates only flagged
strings. Numeric literals are now protected before translation and restored
verbatim afterwards. Benchmark inference remains unsubmitted.

English preparation is complete with 902 source cases and zero exact training
field overlaps. The English file SHA256 is
`34e4e2355c96b86138558f50579647892e1c01f65e2ae8a81ca045b6be5a402a`.
`preparation-jobs.json` records the current job chain on LUMI.

The first preparation attempt, 22572112, stopped on the expected-count assertion
when the source revealed only three When2Call gold classes. Its dependent jobs
22572115 and 22572269 were cancelled automatically. Downloads were reused; no
benchmark inference or GPU translation occurred in that failed chain.
The second CPU attempt, 22572289, exposed structured instruction fields in the
existing training corpus. The exact-overlap scanner now recursively visits text
inside those fields, with a regression test; dependent jobs 22572291 and 22572294
were cancelled. These were preparation failures, not training/model failures.
Attempt 22572317 completed the overlap scan and checkpoint copies but exposed
LUMI's `/scratch` versus resolved `/pfs/lustrep4/scratch` alias while recording
file hashes. Paths are now resolved consistently and identical checkpoint copies
are reused, with a regression test. Job 22572352 then completed successfully.
Before translation, a label-free review of actual When2Call options showed JSON
tool-call answers. The old translation chain was cancelled before GPU use; its
manifest, translation input and scripts are preserved in
`preparation-history/before-json-toolcall-protection/`. Only translation extraction
was revised; English rows, sampling, labels and checkpoints are unchanged, with
the previous manifest hash recorded in the updated manifest.

The corrected chain stops at semantic review. No benchmark scoring jobs have
been submitted. Queue time is unknown. Translation uses the existing 8-GPU setup
with a one-hour time limit; this is an allocation cap, not a runtime estimate.

The standalone HTTP approach remains possible for exported models. For checkpoint
selection, the prepared adapter instead uses Decision Index's existing runner
with native Nesso checkpoint loading, preserving FP32 parameters, BF16 autocast,
native row inference and T=1 from the earlier comparison. This avoids exporting
or changing the serving API solely for evaluation. Laya reuses the already-pinned
native loader and byte-for-byte token truncation audit. Unsupported requests count
as incorrect in the full panel; compare models additionally on the intersection
of source pairs supported in **both** languages by every model, with coverage.

After translation review, run these commands **on LUMI**, from the experiment root:

```bash
task_subset_dir=/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/decision-index-bilingual-v1
sbatch "$task_subset_dir/preparation-source/eval_decision_subset.sbatch" "$task_subset_dir" 74000 selection
sbatch "$task_subset_dir/preparation-source/eval_decision_subset.sbatch" "$task_subset_dir" 142000 selection
sbatch "$task_subset_dir/preparation-source/eval_decision_subset.sbatch" "$task_subset_dir" parent selection
sbatch "$task_subset_dir/preparation-source/eval_decision_subset.sbatch" "$task_subset_dir" laya selection
```

These jobs resume using the upstream runner. Any inference error prevents a
completed report; context refusals are retained explicitly. Reports and per-case
predictions are under `results/selection/<model>/`. The runner checks panel,
checkpoint, script and frozen-runtime hashes, including when resuming.

Confirmation requires a `selection-decision.json` with `checkpoint_step` and
`selection_sha256`, plus the selection result references and rationale. The runner
then permits only the selected checkpoint and fixed baselines on confirmation.
Use the same batch command with `confirmation` after freezing the choice.

Validation completed locally: ten new regression tests, four existing Okapi
tests, and shell syntax checks. Real dataset preparation and the subsequent CPU
audit validate the actual pinned inputs. GPU evaluation adapters still need their
first runtime check when evaluation is launched; no performance claim is made
from preparation or unit tests.
