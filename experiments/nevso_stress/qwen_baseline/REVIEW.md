# Completed Qwen3-0.6B comparison

**All 600 trials completed without infrastructure failures** on the shared A100,
19 October 2026, 16:41:00–16:52:29 UTC (**11 minutes 29 seconds**). The suite,
controller, scoring and three starting tool-order draws match the earlier
Nesso3 evaluation. Qwen uses its own native tools template, thinking disabled,
greedy BF16 generation and the same 192-token cap. This is a comparison under
specified runtime limits, not Qwen's maximum-capability evaluation.

## Calls and answers are separate results

Each authored row below has 20 requests per language repeated under three tool
orders; each BFCL row has 30 requests repeated three times.

| Metric | Language | Nesso3 alone | Nev-ranked + Nesso3 | Nev-selected + Nesso3 | Qwen3 alone |
| --- | --- | ---: | ---: | ---: | ---: |
| Authored confusable: correct executed calls | EN | 17/60 (28.3%) | 40/60 (66.7%) | 56/60 (93.3%) | 44/60 (73.3%) |
| Authored confusable: correct executed calls | IT | 23/60 (38.3%) | 44/60 (73.3%) | 43/60 (71.7%) | 45/60 (75.0%) |
| Authored confusable: calls + answer checks | EN | 7/60 (11.7%) | 28/60 (46.7%) | 41/60 (68.3%) | 44/60 (73.3%) |
| Authored confusable: calls + answer checks | IT | 15/60 (25.0%) | 26/60 (43.3%) | 29/60 (48.3%) | 43/60 (71.7%) |
| BFCL-derived: schema-valid reference call | EN | 19/90 (21.1%) | 15/90 (16.7%) | 16/90 (17.8%) | 45/90 (50.0%) |
| BFCL-derived: schema-valid reference call | IT | 21/90 (23.3%) | 13/90 (14.4%) | 18/90 (20.0%) | 43/90 (47.8%) |

Answer checks are automatic proxies, not a factual audit. Tool-call metrics
check arguments too; they are not function-name-only accuracy. Repeated cached
calls do not add new executions to the executed-call metric. The three orders
are correlated repeats, not independent extra questions.

The results support three observations on this sample:

1. Nev-selected + Nesso3 has the strongest English executed-call score on the
   authored confusing-tool panel. Nev's routing benefit is useful there.
2. Qwen more often passes the answer checks after its successful calls. Nesso3
   generation/stopping is a bottleneck even when Nev picked the right tool.
3. Qwen has substantially higher BFCL point estimates. The difficulty cannot be
   explained by small parameter count alone, although this comparison does not
   isolate size from training, architecture or tokenizer. The selected BFCL data
   may overlap indirectly with training, and this is not an official BFCL score.

No blanket ranking follows: configurations differ, the categories are small and
Qwen does not improve every behavior or language.

## Clarification review

All 90 Qwen missing-information trials were reviewed by the assistant using the
same clean-clarification principle as Nesso: ask for relevant identifying
information without invented requirements or contradictory claims. The review
inspected 46 distinct no-call final outputs. Trials that emit a call or never
answer fail this contract. This is not an independent human audit.

| Language | Nesso3 alone | Nev-ranked + Nesso3 | Nev-selected + Nesso3 | Qwen3 alone |
| --- | ---: | ---: | ---: | ---: |
| EN, reviewed clean clarification | 0/45 | 0/45 | 16/45 | 20/45 |
| IT, reviewed clean clarification | 7/45 | 5/45 | 20/45 | 0/45 |

Two Qwen Italian responses identify the ticket category as missing and
conditionally offer help without explicitly asking for it. These are preserved
as borderline; accepting them would give **2/45**, not 0/45. Other Italian outputs
invented opening hours or instrument status instead of requesting the missing
ID. The original lexical proxy counted one different Italian response; its
1/45 score should not replace this reviewed interpretation. Labels and reasons
are in [clarification_review.json](evidence/a100/clarification_review.json).

## Shared workflow limitations

Qwen passed 0/60 dependent-task completion checks. A sampled museum case emitted
both a title lookup and a room lookup with the placeholder `exhibit_id` in one
batch, before an ID had been returned. The controller rejected the whole batch;
Qwen then incorrectly claimed the exhibit had been found. This is a failure of
the current model/controller workflow. It does not prove no alternative prompting
or orchestration can solve the task. Initial Nev single-tool selection has an
additional architectural restriction: a different second tool is unavailable.

Qwen handled missing-record errors better in the automatic checks (10/15 EN,
3/15 IT), but remained weak on exact dates (1/15 EN, 7/15 IT) and unnecessary-tool
avoidance (exact direct answers 4/15 in each language). Unsupported-action
proxies were 18/30 EN and 3/30 IT; unlike clarification, those were not exhaustively
reviewed. Preserve these counterexamples alongside the BFCL gains.

## Evidence

- [Full automatic comparison](evidence/a100/COMPARISON.md) and
  [comparison JSON](evidence/a100/comparison.json). The generated table retains
  the original raw clarification proxy; use the reviewed table above for that
  category.
- [Raw rows](evidence/a100/rows.jsonl), [readable traces](evidence/a100/traces.txt),
  [metadata](evidence/a100/metadata.json), [clarification review](evidence/a100/clarification_review.json).
- [Protocol](PROTOCOL.md), [original result explanation](../EXPLAINED.md).

Nev + Qwen was not tested. Such a follow-up could separate the routing benefit
from Nesso3's final-answer behavior, but is not a result of this run.
