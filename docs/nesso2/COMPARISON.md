# Nesso2 and Laya: complete comparison

Generated from preserved results, 10 October 2026.

The latest selected candidate is **74k + 256 practical-v2 updates**. The training run ended at +640; +256 was selected by development NLL before its final test. No checkpoint was reselected from the comparisons below.

All numbers are accuracy. EN and IT are shown separately. These are frozen diagnostic subsets, not official full-suite leaderboard scores. The panels were reused during development. Italian benchmark translations are synthetic; Decision Index Italian received partial review.

## Main findings

The selected v2 model reaches **43.75% EN / 45.90% IT** on the practical test, versus Laya's **43.65% / 39.06%**. English differs by only one correct answer out of 1,024: treat it as tied. Italian differs by 70 correct answers (+6.84 percentage points). Relative to original 74k, v2 gains +4.39 EN / +6.35 IT points.

On the 513 common Okapi cases per language, v2 scores 31.19% EN / 31.77% IT, compared with 74k's 30.60% / 31.38% and Laya's 30.02% / 27.10%. This is a small change from 74k, with no aggregate regression on this panel.

Laya is stronger on ANLI and much stronger on CLINC intent classification. Nesso is stronger on the When2Call subset. Consequently the Decision Index aggregate depends on task weighting and coverage: read the per-task scores rather than declaring one universal winner. Practical improvements do not establish general reasoning capability.

All 2,048 practical requests fit Laya. Three native probability ties were recorded and resolved by the documented first-semantic-key rule; native output probabilities are rounded to four decimal places. This reinforces treating the one-answer English difference as a tie.

GPU job 22697632 completed with exit code 0 in 4m30s on one LUMI dev-g MI250X allocation. The 35 archived evidence files were verified individually after download.

## Practical v2: unseen wording and facts

Full panel: 2,048 requests. Bilingual common support: 2,048 requests. Common support keeps a source case only if both EN and IT fit every listed model. Full-panel accuracy counts unsupported requests as wrong.

Four synthetic rule families, 256 cases/task/language. Uniform random choice averages 35.42%. These results do not establish production readiness.

### Same supported bilingual cases

| Model | EN micro | IT micro | EN answered | IT answered |
|---|---|---|---|---|
| Nesso2 74000 | 39.36% | 39.55% | 1024/1024 | 1024/1024 |
| Nesso2 142000 | 33.69% | 38.57% | 1024/1024 | 1024/1024 |
| Selected v2: 74k + 256 | 43.75% | 45.90% | 1024/1024 | 1024/1024 |
| Laya multilingual | 43.65% | 39.06% | 1024/1024 | 1024/1024 |

Per-task scores (same denominator for all models within this table):

| Task/language | Model | N | Accuracy |
|---|---|---|---|
| practical_escalation/en | Nesso2 74000 | 256 | 55.47% |
| practical_escalation/en | Nesso2 142000 | 256 | 45.70% |
| practical_escalation/en | Selected v2: 74k + 256 | 256 | 50.00% |
| practical_escalation/en | Laya multilingual | 256 | 45.31% |
| practical_escalation/it | Nesso2 74000 | 256 | 50.78% |
| practical_escalation/it | Nesso2 142000 | 256 | 50.00% |
| practical_escalation/it | Selected v2: 74k + 256 | 256 | 51.56% |
| practical_escalation/it | Laya multilingual | 256 | 45.31% |
| practical_refund/en | Nesso2 74000 | 256 | 44.53% |
| practical_refund/en | Nesso2 142000 | 256 | 37.50% |
| practical_refund/en | Selected v2: 74k + 256 | 256 | 61.33% |
| practical_refund/en | Laya multilingual | 256 | 62.11% |
| practical_refund/it | Nesso2 74000 | 256 | 48.83% |
| practical_refund/it | Nesso2 142000 | 256 | 44.53% |
| practical_refund/it | Selected v2: 74k + 256 | 256 | 54.69% |
| practical_refund/it | Laya multilingual | 256 | 51.17% |
| practical_routing/en | Nesso2 74000 | 256 | 20.31% |
| practical_routing/en | Nesso2 142000 | 256 | 17.97% |
| practical_routing/en | Selected v2: 74k + 256 | 256 | 30.08% |
| practical_routing/en | Laya multilingual | 256 | 33.20% |
| practical_routing/it | Nesso2 74000 | 256 | 24.22% |
| practical_routing/it | Nesso2 142000 | 256 | 26.17% |
| practical_routing/it | Selected v2: 74k + 256 | 256 | 34.38% |
| practical_routing/it | Laya multilingual | 256 | 26.95% |
| practical_urgency/en | Nesso2 74000 | 256 | 37.11% |
| practical_urgency/en | Nesso2 142000 | 256 | 33.59% |
| practical_urgency/en | Selected v2: 74k + 256 | 256 | 33.59% |
| practical_urgency/en | Laya multilingual | 256 | 33.98% |
| practical_urgency/it | Nesso2 74000 | 256 | 34.38% |
| practical_urgency/it | Nesso2 142000 | 256 | 33.59% |
| practical_urgency/it | Selected v2: 74k + 256 | 256 | 42.97% |
| practical_urgency/it | Laya multilingual | 256 | 32.81% |

Full-panel and common-support results are identical here; no requests were excluded.

## Okapi: ARC-Challenge, HellaSwag, MMLU

Full panel: 1,256 requests. Bilingual common support: 1,026 requests. Common support keeps a source case only if both EN and IT fit every listed model. Full-panel accuracy counts unsupported requests as wrong.

### Same supported bilingual cases

| Model | EN micro | IT micro | EN answered | IT answered |
|---|---|---|---|---|
| Original Nesso2 parent | 24.37% | 23.78% | 513/513 | 513/513 |
| Nesso2 74000 | 30.60% | 31.38% | 513/513 | 513/513 |
| Nesso2 102000 | 29.43% | 27.49% | 513/513 | 513/513 |
| Nesso2 123500 | 30.21% | 28.85% | 513/513 | 513/513 |
| Nesso2 142000 | 29.43% | 28.46% | 513/513 | 513/513 |
| Nesso2 154000 | 30.21% | 28.27% | 513/513 | 513/513 |
| Nesso2 178300 | 29.43% | 28.27% | 513/513 | 513/513 |
| Selected v2: 74k + 256 | 31.19% | 31.77% | 513/513 | 513/513 |
| Laya multilingual | 30.02% | 27.10% | 513/513 | 513/513 |

Per-task scores (same denominator for all models within this table):

| Task/language | Model | N | Accuracy |
|---|---|---|---|
| ARC-Challenge/en | Original Nesso2 parent | 200 | 21.50% |
| ARC-Challenge/en | Nesso2 74000 | 200 | 30.00% |
| ARC-Challenge/en | Nesso2 102000 | 200 | 28.00% |
| ARC-Challenge/en | Nesso2 123500 | 200 | 28.50% |
| ARC-Challenge/en | Nesso2 142000 | 200 | 27.00% |
| ARC-Challenge/en | Nesso2 154000 | 200 | 27.50% |
| ARC-Challenge/en | Nesso2 178300 | 200 | 28.00% |
| ARC-Challenge/en | Selected v2: 74k + 256 | 200 | 30.50% |
| ARC-Challenge/en | Laya multilingual | 200 | 26.50% |
| ARC-Challenge/it | Original Nesso2 parent | 200 | 22.50% |
| ARC-Challenge/it | Nesso2 74000 | 200 | 29.00% |
| ARC-Challenge/it | Nesso2 102000 | 200 | 24.00% |
| ARC-Challenge/it | Nesso2 123500 | 200 | 25.50% |
| ARC-Challenge/it | Nesso2 142000 | 200 | 26.50% |
| ARC-Challenge/it | Nesso2 154000 | 200 | 25.50% |
| ARC-Challenge/it | Nesso2 178300 | 200 | 26.00% |
| ARC-Challenge/it | Selected v2: 74k + 256 | 200 | 29.00% |
| ARC-Challenge/it | Laya multilingual | 200 | 30.00% |
| HellaSwag/en | Original Nesso2 parent | 88 | 31.82% |
| HellaSwag/en | Nesso2 74000 | 88 | 30.68% |
| HellaSwag/en | Nesso2 102000 | 88 | 27.27% |
| HellaSwag/en | Nesso2 123500 | 88 | 28.41% |
| HellaSwag/en | Nesso2 142000 | 88 | 30.68% |
| HellaSwag/en | Nesso2 154000 | 88 | 30.68% |
| HellaSwag/en | Nesso2 178300 | 88 | 30.68% |
| HellaSwag/en | Selected v2: 74k + 256 | 88 | 30.68% |
| HellaSwag/en | Laya multilingual | 88 | 31.82% |
| HellaSwag/it | Original Nesso2 parent | 88 | 19.32% |
| HellaSwag/it | Nesso2 74000 | 88 | 31.82% |
| HellaSwag/it | Nesso2 102000 | 88 | 31.82% |
| HellaSwag/it | Nesso2 123500 | 88 | 30.68% |
| HellaSwag/it | Nesso2 142000 | 88 | 30.68% |
| HellaSwag/it | Nesso2 154000 | 88 | 31.82% |
| HellaSwag/it | Nesso2 178300 | 88 | 30.68% |
| HellaSwag/it | Selected v2: 74k + 256 | 88 | 35.23% |
| HellaSwag/it | Laya multilingual | 88 | 25.00% |
| MMLU/en | Original Nesso2 parent | 225 | 24.00% |
| MMLU/en | Nesso2 74000 | 225 | 31.11% |
| MMLU/en | Nesso2 102000 | 225 | 31.56% |
| MMLU/en | Nesso2 123500 | 225 | 32.44% |
| MMLU/en | Nesso2 142000 | 225 | 31.11% |
| MMLU/en | Nesso2 154000 | 225 | 32.44% |
| MMLU/en | Nesso2 178300 | 225 | 30.22% |
| MMLU/en | Selected v2: 74k + 256 | 225 | 32.00% |
| MMLU/en | Laya multilingual | 225 | 32.44% |
| MMLU/it | Original Nesso2 parent | 225 | 26.67% |
| MMLU/it | Nesso2 74000 | 225 | 33.33% |
| MMLU/it | Nesso2 102000 | 225 | 28.89% |
| MMLU/it | Nesso2 123500 | 225 | 31.11% |
| MMLU/it | Nesso2 142000 | 225 | 29.33% |
| MMLU/it | Nesso2 154000 | 225 | 29.33% |
| MMLU/it | Nesso2 178300 | 225 | 29.33% |
| MMLU/it | Selected v2: 74k + 256 | 225 | 32.89% |
| MMLU/it | Laya multilingual | 225 | 25.33% |

### Full panel, including capacity failures

| Model | EN micro | IT micro | EN answered | IT answered |
|---|---|---|---|---|
| Original Nesso2 parent | 24.20% | 24.20% | 628/628 | 628/628 |
| Nesso2 74000 | 31.05% | 31.53% | 628/628 | 628/628 |
| Nesso2 102000 | 29.14% | 27.71% | 628/628 | 628/628 |
| Nesso2 123500 | 30.57% | 29.30% | 628/628 | 628/628 |
| Nesso2 142000 | 29.94% | 28.82% | 628/628 | 628/628 |
| Nesso2 154000 | 30.89% | 28.34% | 628/628 | 628/628 |
| Nesso2 178300 | 30.25% | 28.50% | 628/628 | 628/628 |
| Selected v2: 74k + 256 | 31.69% | 31.85% | 628/628 | 628/628 |
| Laya multilingual | 26.75% | 22.13% | 570/628 | 513/628 |

Per-task scores (same denominator for all models within this table):

| Task/language | Model | N | Accuracy |
|---|---|---|---|
| ARC-Challenge/en | Original Nesso2 parent | 200 | 21.50% |
| ARC-Challenge/en | Nesso2 74000 | 200 | 30.00% |
| ARC-Challenge/en | Nesso2 102000 | 200 | 28.00% |
| ARC-Challenge/en | Nesso2 123500 | 200 | 28.50% |
| ARC-Challenge/en | Nesso2 142000 | 200 | 27.00% |
| ARC-Challenge/en | Nesso2 154000 | 200 | 27.50% |
| ARC-Challenge/en | Nesso2 178300 | 200 | 28.00% |
| ARC-Challenge/en | Selected v2: 74k + 256 | 200 | 30.50% |
| ARC-Challenge/en | Laya multilingual | 200 | 26.50% |
| ARC-Challenge/it | Original Nesso2 parent | 200 | 22.50% |
| ARC-Challenge/it | Nesso2 74000 | 200 | 29.00% |
| ARC-Challenge/it | Nesso2 102000 | 200 | 24.00% |
| ARC-Challenge/it | Nesso2 123500 | 200 | 25.50% |
| ARC-Challenge/it | Nesso2 142000 | 200 | 26.50% |
| ARC-Challenge/it | Nesso2 154000 | 200 | 25.50% |
| ARC-Challenge/it | Nesso2 178300 | 200 | 26.00% |
| ARC-Challenge/it | Selected v2: 74k + 256 | 200 | 29.00% |
| ARC-Challenge/it | Laya multilingual | 200 | 30.00% |
| HellaSwag/en | Original Nesso2 parent | 200 | 27.00% |
| HellaSwag/en | Nesso2 74000 | 200 | 32.00% |
| HellaSwag/en | Nesso2 102000 | 200 | 27.50% |
| HellaSwag/en | Nesso2 123500 | 200 | 30.50% |
| HellaSwag/en | Nesso2 142000 | 200 | 31.50% |
| HellaSwag/en | Nesso2 154000 | 200 | 32.50% |
| HellaSwag/en | Nesso2 178300 | 200 | 32.50% |
| HellaSwag/en | Selected v2: 74k + 256 | 200 | 32.50% |
| HellaSwag/en | Laya multilingual | 200 | 20.50% |
| HellaSwag/it | Original Nesso2 parent | 200 | 23.00% |
| HellaSwag/it | Nesso2 74000 | 200 | 31.50% |
| HellaSwag/it | Nesso2 102000 | 200 | 29.50% |
| HellaSwag/it | Nesso2 123500 | 200 | 30.00% |
| HellaSwag/it | Nesso2 142000 | 200 | 30.00% |
| HellaSwag/it | Nesso2 154000 | 200 | 30.00% |
| HellaSwag/it | Nesso2 178300 | 200 | 30.00% |
| HellaSwag/it | Selected v2: 74k + 256 | 200 | 33.00% |
| HellaSwag/it | Laya multilingual | 200 | 11.00% |
| MMLU/en | Original Nesso2 parent | 228 | 24.12% |
| MMLU/en | Nesso2 74000 | 228 | 31.14% |
| MMLU/en | Nesso2 102000 | 228 | 31.58% |
| MMLU/en | Nesso2 123500 | 228 | 32.46% |
| MMLU/en | Nesso2 142000 | 228 | 31.14% |
| MMLU/en | Nesso2 154000 | 228 | 32.46% |
| MMLU/en | Nesso2 178300 | 228 | 30.26% |
| MMLU/en | Selected v2: 74k + 256 | 228 | 32.02% |
| MMLU/en | Laya multilingual | 228 | 32.46% |
| MMLU/it | Original Nesso2 parent | 228 | 26.75% |
| MMLU/it | Nesso2 74000 | 228 | 33.77% |
| MMLU/it | Nesso2 102000 | 228 | 29.39% |
| MMLU/it | Nesso2 123500 | 228 | 32.02% |
| MMLU/it | Nesso2 142000 | 228 | 29.82% |
| MMLU/it | Nesso2 154000 | 228 | 29.39% |
| MMLU/it | Nesso2 178300 | 228 | 29.39% |
| MMLU/it | Selected v2: 74k + 256 | 228 | 33.33% |
| MMLU/it | Laya multilingual | 228 | 25.00% |

## Decision Index: ANLI, CLINC, When2Call

Full panel: 902 requests. Bilingual common support: 756 requests. Common support keeps a source case only if both EN and IT fit every listed model. Full-panel accuracy counts unsupported requests as wrong.

151 CLINC intents and 150 cases each for ANLI and When2Call per language. This is not the official Decision Index composite. When2Call was later deprioritized; it remains here for completeness.

### Same supported bilingual cases

| Model | EN micro | IT micro | EN answered | IT answered |
|---|---|---|---|---|
| Original Nesso2 parent | 12.17% | 11.90% | 378/378 | 378/378 |
| Nesso2 74000 | 24.07% | 24.34% | 378/378 | 378/378 |
| Nesso2 142000 | 23.28% | 23.81% | 378/378 | 378/378 |
| Selected v2: 74k + 256 | 24.34% | 25.66% | 378/378 | 378/378 |
| Laya multilingual | 30.16% | 32.01% | 378/378 | 378/378 |

| Model | EN task-macro | IT task-macro |
|---|---|---|
| Original Nesso2 parent | 10.43% | 10.21% |
| Nesso2 74000 | 28.43% | 26.76% |
| Nesso2 142000 | 26.92% | 27.58% |
| Selected v2: 74k + 256 | 28.44% | 27.86% |
| Laya multilingual | 27.17% | 30.83% |

Per-task scores (same denominator for all models within this table):

| Task/language | Model | N | Accuracy |
|---|---|---|---|
| ANLI/en | Original Nesso2 parent | 150 | 28.67% |
| ANLI/en | Nesso2 74000 | 150 | 30.67% |
| ANLI/en | Nesso2 142000 | 150 | 32.67% |
| ANLI/en | Selected v2: 74k + 256 | 150 | 31.33% |
| ANLI/en | Laya multilingual | 150 | 43.33% |
| ANLI/it | Original Nesso2 parent | 150 | 28.67% |
| ANLI/it | Nesso2 74000 | 150 | 38.00% |
| ANLI/it | Nesso2 142000 | 150 | 34.00% |
| ANLI/it | Selected v2: 74k + 256 | 150 | 38.00% |
| ANLI/it | Laya multilingual | 150 | 40.00% |
| CLINC150+OOS/en | Original Nesso2 parent | 151 | 1.32% |
| CLINC150+OOS/en | Nesso2 74000 | 151 | 3.97% |
| CLINC150+OOS/en | Nesso2 142000 | 151 | 2.65% |
| CLINC150+OOS/en | Selected v2: 74k + 256 | 151 | 4.64% |
| CLINC150+OOS/en | Laya multilingual | 151 | 26.49% |
| CLINC150+OOS/it | Original Nesso2 parent | 151 | 0.66% |
| CLINC150+OOS/it | Nesso2 74000 | 151 | 3.31% |
| CLINC150+OOS/it | Nesso2 142000 | 151 | 1.99% |
| CLINC150+OOS/it | Selected v2: 74k + 256 | 151 | 6.62% |
| CLINC150+OOS/it | Laya multilingual | 151 | 27.81% |
| When2Call MCQ/en | Original Nesso2 parent | 77 | 1.30% |
| When2Call MCQ/en | Nesso2 74000 | 77 | 50.65% |
| When2Call MCQ/en | Nesso2 142000 | 77 | 45.45% |
| When2Call MCQ/en | Selected v2: 74k + 256 | 77 | 49.35% |
| When2Call MCQ/en | Laya multilingual | 77 | 11.69% |
| When2Call MCQ/it | Original Nesso2 parent | 77 | 1.30% |
| When2Call MCQ/it | Nesso2 74000 | 77 | 38.96% |
| When2Call MCQ/it | Nesso2 142000 | 77 | 46.75% |
| When2Call MCQ/it | Selected v2: 74k + 256 | 77 | 38.96% |
| When2Call MCQ/it | Laya multilingual | 77 | 24.68% |

### Full panel, including capacity failures

| Model | EN micro | IT micro | EN answered | IT answered |
|---|---|---|---|---|
| Original Nesso2 parent | 10.64% | 10.64% | 451/451 | 451/451 |
| Nesso2 74000 | 28.60% | 27.94% | 450/451 | 445/451 |
| Nesso2 142000 | 26.16% | 26.61% | 450/451 | 445/451 |
| Selected v2: 74k + 256 | 27.94% | 28.38% | 450/451 | 445/451 |
| Laya multilingual | 26.39% | 26.83% | 396/451 | 382/451 |

| Model | EN task-macro | IT task-macro |
|---|---|---|
| Original Nesso2 parent | 10.66% | 10.67% |
| Nesso2 74000 | 28.66% | 27.99% |
| Nesso2 142000 | 26.22% | 26.66% |
| Selected v2: 74k + 256 | 27.99% | 28.43% |
| Laya multilingual | 26.39% | 26.83% |

Per-task scores (same denominator for all models within this table):

| Task/language | Model | N | Accuracy |
|---|---|---|---|
| ANLI/en | Original Nesso2 parent | 150 | 28.67% |
| ANLI/en | Nesso2 74000 | 150 | 30.67% |
| ANLI/en | Nesso2 142000 | 150 | 32.67% |
| ANLI/en | Selected v2: 74k + 256 | 150 | 31.33% |
| ANLI/en | Laya multilingual | 150 | 43.33% |
| ANLI/it | Original Nesso2 parent | 150 | 28.67% |
| ANLI/it | Nesso2 74000 | 150 | 38.00% |
| ANLI/it | Nesso2 142000 | 150 | 34.00% |
| ANLI/it | Selected v2: 74k + 256 | 150 | 38.00% |
| ANLI/it | Laya multilingual | 150 | 40.00% |
| CLINC150+OOS/en | Original Nesso2 parent | 151 | 1.32% |
| CLINC150+OOS/en | Nesso2 74000 | 151 | 3.97% |
| CLINC150+OOS/en | Nesso2 142000 | 151 | 2.65% |
| CLINC150+OOS/en | Selected v2: 74k + 256 | 151 | 4.64% |
| CLINC150+OOS/en | Laya multilingual | 151 | 26.49% |
| CLINC150+OOS/it | Original Nesso2 parent | 151 | 0.66% |
| CLINC150+OOS/it | Nesso2 74000 | 151 | 3.31% |
| CLINC150+OOS/it | Nesso2 142000 | 151 | 1.99% |
| CLINC150+OOS/it | Selected v2: 74k + 256 | 151 | 6.62% |
| CLINC150+OOS/it | Laya multilingual | 151 | 27.81% |
| When2Call MCQ/en | Original Nesso2 parent | 150 | 2.00% |
| When2Call MCQ/en | Nesso2 74000 | 150 | 51.33% |
| When2Call MCQ/en | Nesso2 142000 | 150 | 43.33% |
| When2Call MCQ/en | Selected v2: 74k + 256 | 150 | 48.00% |
| When2Call MCQ/en | Laya multilingual | 150 | 9.33% |
| When2Call MCQ/it | Original Nesso2 parent | 150 | 2.67% |
| When2Call MCQ/it | Nesso2 74000 | 150 | 42.67% |
| When2Call MCQ/it | Nesso2 142000 | 150 | 44.00% |
| When2Call MCQ/it | Selected v2: 74k + 256 | 150 | 40.67% |
| When2Call MCQ/it | Laya multilingual | 150 | 12.67% |

## Earlier practical v1: a different test

512 requests per language. This panel uses different cases and wording from v2; compare models within a panel, not absolute scores between versions.

| Model | EN | IT |
|---|---|---|
| Nesso2 74000 | 33.01% | 31.64% |
| Nesso2 142000 | 36.91% | 31.05% |
| 74k + 512 (v1) | 40.23% | 35.35% |

Laya and the selected v2 model were not run on the v1 panel.

### Practical v1 development history (not final test)

| Additional updates | Dev EN | Dev IT | Dev macro NLL | Guard passed |
|---|---|---|---|---|
| adapted-128 | 61.33% | 52.73% | 0.90343 | True |
| adapted-256 | 67.97% | 68.36% | 0.72386 | True |
| adapted-384 | 79.30% | 75.00% | 0.57552 | True |
| adapted-512 | 80.47% | 75.78% | 0.48971 | True |

### Practical v2 development history (not final test)

| Additional updates | Dev EN | Dev IT | Dev macro NLL | Guard passed |
|---|---|---|---|---|
| adapted-128 | 37.50% | 37.70% | 1.15173 | True |
| adapted-256 | 36.33% | 41.02% | 1.13358 | True |
| adapted-384 | 37.70% | 40.82% | 1.15202 | True |
| adapted-512 | 39.65% | 44.92% | 1.14419 | True |
| adapted-640 | 42.77% | 46.09% | 1.15092 | True |

## Full-data model: original-domain and unseen-source panels

These are the exported **142k** model's scores, not the latest practical-v2 model. Laya was not measured on these panels. Training used 713,198 records, exactly half EN/half IT.

| Panel | Questions/language | EN | IT |
|---|---|---|---|
| prior_pilot_test | 341 | 75.95% | 73.02% |
| prior_pilot_unseen | 57 | 52.63% | 56.14% |
| full_test | 70049 | 88.29% | 86.87% |
| full_unseen | 285 | 59.30% | 60.70% |

## Earlier pilot and published Kev references

Historical figures below come from the preserved LUMI README. The small pilot used only 1,684 training records. Published Kev uses larger backbones and may have seen some reserved training-pool examples. Its FP32 inference differs from the Nesso2 BF16 exports; this compares finished systems, not architectures in isolation.

| Model | Pilot test EN (341) | Pilot test IT (341) | Unseen EN (57) | Unseen IT (57) |
|---|---|---|---|---|
| Small Nesso2 gold pilot | 38.4% | 36.4% | 42.1% | 33.3% |
| Small Nesso2 distilled pilot | 37.0% | 34.6% | 38.6% | 33.3% |
| Published Kev-0.8B | 80.4% | 73.6% | 66.7% | 45.6% |
| Published Kev-4B | 84.8% | 80.1% | 75.4% | 73.7% |
| Full-data Nesso2 142k | 75.95% | 73.02% | 52.63% | 56.14% |

Pilot common eligible panel, excluding Banking77 from every model (303 questions per language):

| System | EN | IT |
|---|---|---|
| Original Nesso2, cyclic LM scoring | 41.9% | 41.3% |
| Small gold decision pilot | 42.9% | 40.9% |
| Small distilled decision pilot | 40.9% | 38.9% |
| Nesso-4B teacher, cyclic LM scoring | 74.6% | 71.6% |

Official test/validation-only pilot subset (129 questions/language): gold pilot 42.6% EN / 38.8% IT; Kev-0.8B 85.3% / 81.4%; Kev-4B 83.7% / 79.8%. Pretraining exposure remains unknown.

Teacher selection development panel (298 questions/language, not test): Nesso-4B 72.5% EN / 72.1% IT, macro record NLL 1.0894; Qwen-4B 72.8% / 69.8%, NLL 4.0458. Nesso-4B was selected, but that small distillation run did not establish an improvement over gold-only training.

## Confidence and runtime

Practical v2: no confidence threshold qualified for any Nesso candidate. Accepted coverage is zero; this does not mean zero prediction errors. Selected-model calibrated temperature is .73204, with 48 wrong Italian test predictions at confidence >=90%. Laya's confidence policy was not fitted on this panel.

Practical v1: its .7 threshold failed on changed wording (EN accepted-case error 59.57%, IT 67.31%). The earlier confidence policy must not be used for deployment.

Selected v2 batch-1 latency on AMD MI250X: median 72.06 ms, p95 80.92 ms, peak allocated memory 1.90 GiB. Includes tokenization, excludes model loading and networking; FP32 parameters with BF16 autocast. No matched Laya latency claim is made.

## Provenance and interpretation

- Reused diagnostic panels; not new independent model-selection tests

- Full scores count unsupported as wrong; common scores retain both languages supported by every listed model

- Separate datasets and averaging conventions must not be merged into one overall score

- Practical v2 is synthetic; no claim of production readiness or a valid confidence policy

- Laya uses native renderer, pinned weights and shipped temperatures, with 8192/8184 context/head limits and no truncation

- Laya discrete score/noul decisions use native rounded probabilities (argmax, first semantic key for ties); ties are recorded per case

- Nesso external evaluations use the same frozen native rows engine and T=1 as prior comparisons

- Scores near each other on these small samples are descriptive differences, not established improvements.

- Nesso2 parent is a language-model scoring baseline; the fine-tuned checkpoints use the learned decision head.

- Laya is convaiinnovations/laya-multilingual, pinned model revision e4e9ddf21a7b1903b7acffd8814ad4307bf63a67 and code revision fa9a2a7070b1789912a49ae24603bbfb1a78b001.

Evidence: [machine-readable comparison](evidence/latest-comparison-report.json), [experiment log](EXPERIMENT_LOG.md), [original full-data report](evidence/full-training-report.json), [v1 report](evidence/practical-v1-report.json), [v2 report](evidence/practical-v2-report.json), [early experiments](../../experiments/lumi/README.md).
