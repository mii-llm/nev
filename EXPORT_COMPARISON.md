# Comparison of the two actual exports

All values are accuracy percentages. Both artifacts have FP32 parameters; these benchmark runs use BF16 autocast. Each table uses identical examples across its listed models. Native serving examples use a different execution form; see INFERENCE.md.

## Full panels

Unsupported requests count as wrong. The Laya comparison below uses common support to avoid conflating admission limits with answer quality.

| Task | N/language | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|---:|
| ARC-Challenge | 200 | 31.00% | 29.00% | 30.50% | 31.00% |
| HellaSwag | 200 | 33.00% | 33.00% | 29.50% | 33.00% |
| MMLU | 228 | 31.58% | 32.46% | 32.02% | 32.46% |
| ANLI | 150 | 30.67% | 38.00% | 30.00% | 38.00% |
| CLINC150+OOS | 151 | 4.64% | 6.62% | 5.30% | 12.58% |
| When2Call MCQ | 150 | 48.00% | 40.67% | 46.00% | 38.67% |
| practical_escalation | 256 | 51.95% | 51.56% | 53.52% | 51.17% |
| practical_refund | 256 | 61.33% | 52.73% | 52.73% | 50.39% |
| practical_routing | 256 | 29.69% | 34.77% | 55.08% | 46.88% |
| practical_urgency | 256 | 33.59% | 42.97% | 33.59% | 37.89% |

## Common bilingual support with Laya

| Panel | N/language | V2 EN / IT | V3 EN / IT | Laya EN / IT |
|---|---:|---:|---:|---:|
| okapi | 513 | 31.19% / 31.19% | 30.41% / 32.55% | 30.02% / 27.10% |
| decision_index | 378 | 24.07% / 25.66% | 23.81% / 27.78% | 30.16% / 32.01% |
| practical_v2 | 1024 | 44.14% / 45.51% | 48.73% / 46.58% | 43.65% / 39.06% |

The complete per-task common-support metrics, denominators and source archive hashes are in `export-comparison.json`. Original adapter comparisons remain in `COMPARISON.md` and `results.json`. The new v3 16-intent/routing test is a separate synthetic panel; v2 export was not scored on it in this preparation, so no fresh-panel v2-export score is claimed.
