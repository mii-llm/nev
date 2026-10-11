# Focused v3 results — completed

The subsequent [external and practical regression audit](V3_REGRESSION.md) is also
complete. It finds stronger routing but weaker refunds and Italian urgency versus
v2, in both the adapter and export. The fresh synthetic gains below must not be
read as improvement across every task.

GPU job **22707766** completed successfully in **58m52s**. Preparation 22707765 completed in 1m38s. All pipeline stages passed; no public upload occurred.

Selected checkpoint: **v2 + 512 updates**, where v2 was original 74k + 256. Training stopped at +896 because of development plateau/regression. Snapshots +640, +768 and +896 failed eligibility; +512 passed both retention guards and was selected before final test.

## Fresh synthetic test

Exactly 512 examples/language: 256 routing and 256 intent. The intent task has **16 classes** and a distracting earlier customer message. The final utterance wording and complete routing configurations are held out. These are controlled synthetic tasks, not CLINC or independent real customer traffic. All examples fit every model; common/full support are identical.

| Model | English | Italian |
|---|---:|---:|
| Unchanged v2 | 23.63% | 25.00% |
| Selected v3 adapter | 54.88% | 62.89% |
| Laya multilingual | 26.17% | 28.71% |
| V3 merged export (BF16 autocast) | 54.69% | 62.50% |

## Per-task accuracy

| Task/language | V2 | V3 adapter | Laya |
|---|---:|---:|---:|
| focused_intent/en | 12.11% | 60.94% | 19.92% |
| focused_intent/it | 15.23% | 74.22% | 27.34% |
| focused_routing/en | 35.16% | 48.83% | 32.42% |
| focused_routing/it | 34.77% | 51.56% | 30.08% |

## Export and confidence

Private merged FP32 export prepared on LUMI scratch. On 19 export-check requests / 40 questions, maximum FP32 merge probability difference was **4.62e-6** (tolerance 3e-5), with no argmax changes. Fresh-process same-dtype reload was exact (maximum difference 0).

The full test uses FP32 parameters with BF16 autocast. In that mode the merged export changed **12/1,024 predictions** versus the unmerged adapter, with three fewer correct answers overall. This is distinct from the exact FP32 serialization check. Report the exported artifact’s measured accuracy separately; do not attach adapter scores to it.

V3 calibrated temperature: **0.81225**. **No confidence threshold qualified** for v2 or v3 under the predeclared policy. Zero accepted coverage is abstention, not error-free automation. Public release and real-traffic confidence validation remain uncompleted.

## Development selection

| Additional updates | Dev macro NLL | Dev accuracy | Both guards passed |
|---|---:|---:|---|
| adapted-128 | 1.67615 | 27.15% | True |
| adapted-256 | 1.46119 | 34.18% | True |
| adapted-384 | 1.34804 | 41.41% | True |
| adapted-512 | 1.30217 | 44.92% | True |
| adapted-640 | 1.30883 | 46.48% | False |
| adapted-768 | 1.39398 | 46.29% | False |
| adapted-896 | 1.38778 | 47.85% | False |

## Evidence

[Comparison](evidence/focused-v3-comparison.json), [training history](evidence/focused-v3-training.json), [export evaluation](evidence/focused-v3-export-evaluation.json), [export equivalence](evidence/focused-v3-export-conversion.json), [completion marker](evidence/focused-v3-completion.json).

`evidence/focused-v3-completed.tar.gz` preserves 97 files, verified individually against `focused-v3-evidence-index.json`. Selected checkpoint and private export file hashes are preserved in `focused-v3-artifact-sha256.json`. Model weights remain under project scratch.

Archive SHA-256: `3aee6c64f0e12a48b0278265c7ab9c8edd45b9aae842e4dae0a22f517fe15c58`.

[Protocol and recipe](FOCUSED_V3.md). [Earlier benchmark results](COMPARISON.md). No new CLINC, ANLI or Okapi results are claimed for v3.
