# Harder bilingual diagnostic results

Job `22720810`; pinned release `c5c84121263b423f8846811a24790ab96e66cee3`. Native cached FP32 inference on LUMI. Inputs and answer keys were fixed before reviewing predictions. No weights or prompts were tuned against these outputs.

20 authored requests per model (10/language), with four decisions each. Five one-fact contrast pairs per language. These small, correlated examples are a diagnostic, not a representative benchmark.

| Correct answers | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|
| route | 7/10 | 5/10 | 9/10 | 5/10 |
| refund | 8/10 | 8/10 | 8/10 | 8/10 |
| urgency | 4/10 | 6/10 | 6/10 | 5/10 |
| escalate | 8/10 | 8/10 | 8/10 | 8/10 |
| All four decisions correct | 2/10 | 2/10 | 2/10 | 0/10 |
| Changed decision correct on both sides | 0/7 | 1/7 | 1/7 | 0/7 |

Both models predicted `false` for **every** refund and escalation decision. Thus the 8/10 scores on these tasks merely equal the always-no baseline; neither model handled any positive case correctly. The always-routine urgency baseline is 5/10; the most common route is shipping at 4/10. These baselines describe this fixture only.

V3 handles more English routing cases than v2 here, but policy-sensitive decisions remain weak. Neither model got a complete contrast pair correct across all four decisions in either language. The tiny set does not support broad model-ranking claims.

Concrete v3 failures:

- English, a third unsuccessful support contact: policy requires escalation; v3 says no with probability 0.9885.
- English, confirmed duplicate charge not yet refunded: policy requires reimbursement; v3 says no with probability 0.8869.
- Italian, an unopened return 29 days after delivery: policy allows it, but v3 denies reimbursement and routes to shipping; changing 29 to 31 days does not fix its interpretation.

The assigned probabilities are model outputs, not measured correctness probabilities. These examples expose failures in following the supplied rules and distinguishing relevant facts from distracting text. They should guide future diagnostics; they must not become an undisclosed training set reused as an independent test.

Full requests: [examples/scenarios.json](examples/scenarios.json). Full unfiltered outputs: [scenario-results.json](docs/nesso2/evidence/scenario-results.json). Commands: [scenario guide](examples/SCENARIOS.md).

Fixture preparation: job 22720790 was superseded before its predictions were inspected. An irrelevant default of 60 days since delivery contradicted the missing-parcel scenarios; it was changed to null. Answer keys were unchanged. The correction and original input hash are recorded in [scenario-input-correction.json](docs/nesso2/evidence/scenario-input-correction.json). The corrected fixture SHA-256 matches the result report.
