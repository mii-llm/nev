# V3 regression audit

Selected model: v2 +512 updates, fixed before this audit. Both the adapter and the merged FP32 export were scored with BF16 autocast on the original frozen bilingual panels. No training or checkpoint reselection occurred.

V3 improves the older practical panel overall, driven by routing, but regresses on refunds and Italian urgency. External benchmark changes are mixed; Italian CLINC improves while English HellaSwag falls. The merged export shows the same tradeoff. This supports retaining v3 as a routing-focused candidate, not claiming a universal improvement over v2. Before a general-purpose release, address retention with task-level development guards and balanced replay; do not select checkpoints on these reused tests.

## Changes from v2 on the full panels

Accuracy percentages; unsupported requests count as incorrect. Every comparison below uses the same examples for v2 and v3. EN and IT are reported separately. Changes are percentage points, not relative percentages.

| Panel/task | Language | N | V2 | V3 adapter | Change | V3 export |
|---|---|---:|---:|---:|---:|---:|
| okapi: ARC-Challenge | EN | 200 | 30.50% | 30.50% | +0.00 | 30.50% |
| okapi: ARC-Challenge | IT | 200 | 29.00% | 31.00% | +2.00 | 31.00% |
| okapi: HellaSwag | EN | 200 | 32.50% | 29.50% | -3.00 | 29.50% |
| okapi: HellaSwag | IT | 200 | 33.00% | 32.50% | -0.50 | 33.00% |
| okapi: MMLU | EN | 228 | 32.02% | 31.14% | -0.88 | 32.02% |
| okapi: MMLU | IT | 228 | 33.33% | 32.02% | -1.32 | 32.46% |
| decision_index: ANLI | EN | 150 | 31.33% | 30.67% | -0.67 | 30.00% |
| decision_index: ANLI | IT | 150 | 38.00% | 37.33% | -0.67 | 38.00% |
| decision_index: CLINC150+OOS | EN | 151 | 4.64% | 4.64% | +0.00 | 5.30% |
| decision_index: CLINC150+OOS | IT | 151 | 6.62% | 11.92% | +5.30 | 12.58% |
| decision_index: When2Call MCQ | EN | 150 | 48.00% | 46.00% | -2.00 | 46.00% |
| decision_index: When2Call MCQ | IT | 150 | 40.67% | 37.33% | -3.33 | 38.67% |
| practical_v2: practical_escalation | EN | 256 | 50.00% | 51.17% | +1.17 | 53.52% |
| practical_v2: practical_escalation | IT | 256 | 51.56% | 51.56% | +0.00 | 51.17% |
| practical_v2: practical_refund | EN | 256 | 61.33% | 51.95% | -9.38 | 52.73% |
| practical_v2: practical_refund | IT | 256 | 54.69% | 50.78% | -3.91 | 50.39% |
| practical_v2: practical_routing | EN | 256 | 30.08% | 54.30% | +24.22 | 55.08% |
| practical_v2: practical_routing | IT | 256 | 34.38% | 47.66% | +13.28 | 46.88% |
| practical_v2: practical_urgency | EN | 256 | 33.59% | 33.59% | +0.00 | 33.59% |
| practical_v2: practical_urgency | IT | 256 | 42.97% | 37.50% | -5.47 | 37.89% |

## Laya comparison on identical bilingual support

A paired English/Italian example is retained only if both versions fit every listed historical control and both v3 artifacts. These denominators can be smaller than the full-panel table, especially for HellaSwag and When2Call. Do not compare percentages across the two tables as though they used the same examples.

| Panel/task | Language | N | V2 | V3 adapter | V3 export | Laya |
|---|---|---:|---:|---:|---:|---:|---:|
| okapi: ARC-Challenge | EN | 200 | 30.50% | 30.50% | 30.50% | 26.50% |
| okapi: ARC-Challenge | IT | 200 | 29.00% | 31.00% | 31.00% | 30.00% |
| okapi: HellaSwag | EN | 88 | 30.68% | 27.27% | 27.27% | 31.82% |
| okapi: HellaSwag | IT | 88 | 35.23% | 37.50% | 37.50% | 25.00% |
| okapi: MMLU | EN | 225 | 32.00% | 30.67% | 31.56% | 32.44% |
| okapi: MMLU | IT | 225 | 32.89% | 31.56% | 32.00% | 25.33% |
| decision_index: ANLI | EN | 150 | 31.33% | 30.67% | 30.00% | 43.33% |
| decision_index: ANLI | IT | 150 | 38.00% | 37.33% | 38.00% | 40.00% |
| decision_index: CLINC150+OOS | EN | 151 | 4.64% | 4.64% | 5.30% | 26.49% |
| decision_index: CLINC150+OOS | IT | 151 | 6.62% | 11.92% | 12.58% | 27.81% |
| decision_index: When2Call MCQ | EN | 77 | 49.35% | 49.35% | 48.05% | 11.69% |
| decision_index: When2Call MCQ | IT | 77 | 38.96% | 36.36% | 37.66% | 24.68% |
| practical_v2: practical_escalation | EN | 256 | 50.00% | 51.17% | 53.52% | 45.31% |
| practical_v2: practical_escalation | IT | 256 | 51.56% | 51.56% | 51.17% | 45.31% |
| practical_v2: practical_refund | EN | 256 | 61.33% | 51.95% | 52.73% | 62.11% |
| practical_v2: practical_refund | IT | 256 | 54.69% | 50.78% | 50.39% | 51.17% |
| practical_v2: practical_routing | EN | 256 | 30.08% | 54.30% | 55.08% | 33.20% |
| practical_v2: practical_routing | IT | 256 | 34.38% | 47.66% | 46.88% | 26.95% |
| practical_v2: practical_urgency | EN | 256 | 33.59% | 33.59% | 33.59% | 33.98% |
| practical_v2: practical_urgency | IT | 256 | 42.97% | 37.50% | 37.89% | 32.81% |

## Overall panel accuracy

These are per-panel micro averages. No overall score combines the three different datasets.

| Panel | Support | N/language | V2 EN / IT | V3 EN / IT | Export EN / IT | Laya EN / IT |
|---|---|---:|---:|---:|---:|---:|
| okapi | full | 628/628 | 31.69% / 31.85% | 30.41% / 31.85% | 30.73% / 32.17% | 26.75% / 22.13% |
| okapi | common_bilingual | 513/513 | 31.19% / 31.77% | 30.02% / 32.36% | 30.41% / 32.55% | 30.02% / 27.10% |
| decision_index | full | 451/451 | 27.94% / 28.38% | 27.05% / 28.82% | 27.05% / 29.71% | 26.39% / 26.83% |
| decision_index | common_bilingual | 378/378 | 24.34% / 25.66% | 24.07% / 26.98% | 23.81% / 27.78% | 30.16% / 32.01% |
| practical_v2 | full | 1024/1024 | 43.75% / 45.90% | 47.75% / 46.88% | 48.73% / 46.58% | 43.65% / 39.06% |
| practical_v2 | common_bilingual | 1024/1024 | 43.75% / 45.90% | 47.75% / 46.88% | 48.73% / 46.58% | 43.65% / 39.06% |

## Correctness transitions after merging

Counts below compare exported versus adapter correctness, not all argmax changes: a changed answer can be wrong in both artifacts.

| Panel | N | Newly correct | Newly wrong | Accuracy change (points) |
|---|---:|---:|---:|---:|
| okapi | 1256 | 8 | 4 | +0.318 |
| decision_index | 902 | 6 | 2 | +0.443 |
| practical_v2 | 2048 | 14 | 7 | +0.342 |

## Reproducibility and limits

- LUMI job **22714887** completed successfully in **8m34s**, one MI250X GPU device. All remote files are under the authorized project scratch directory. The local archive contains 70 individually verified evidence files; SHA-256 `343ff137a7bb7d6b714c68377d8427cd0accd35b7352bbf6b5984b7da36fed4b`.
- Run: `runs/bilingual-all-v1/focused-v3-regression-v1`. Inputs, frozen runtime, selected adapter and export weights were SHA-256 checked. All historical baseline metrics reproduced (floating summation tolerance 1e-12 across Python versions).
- Each v3 artifact was scored on 1,256 Okapi, 902 Decision Index, and 2,048 practical-v2 requests. Half are English, half Italian. Practical native choice/boolean/ordinal tasks use packed logits; external choice tasks retain the previous rows renderer, T=1.
- These are previously inspected diagnostic subsets, not official full-suite leaderboard scores or new independent selection tests. Italian text is synthetic and partially reviewed; pretraining contamination is unknown.
- No confidence guarantee follows from accuracy, and the v3 confidence policy still has no qualifying threshold. No public upload occurred.
- [Machine-readable report](evidence/focused-v3-regression-report.json), [manifest](evidence/focused-v3-regression-manifest.json), and complete evidence archive (`evidence/focused-v3-regression-completed.tar.gz`, retained experiment archive). The report retains all historical controls, support counts and paired correctness gains/losses.
