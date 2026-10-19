# Completed A100 evaluation and trace review

All **1,800 trials completed** on 19 October 2026, from 15:32:13 to 16:19:33 UTC
(**47 minutes 20 seconds**), without infrastructure failures. The model revisions,
200 requests, prompts, controller and scoring stayed frozen. Three tool orders
repeat each request; counts below are trials, not independent examples.

## Tool calls: where Nev helps and where it does not

| Panel | Language | Nesso3 alone | Nev-ranked | Nev-selected |
| --- | --- | ---: | ---: | ---: |
| Authored confusable functions: exact executed calls | EN | 17/60 (28.3%) | 40/60 (66.7%) | 56/60 (93.3%) |
| Authored confusable functions: exact executed calls | IT | 23/60 (38.3%) | 44/60 (73.3%) | 43/60 (71.7%) |
| BFCL-derived: schema-valid reference calls | EN | 19/90 (21.1%) | 15/90 (16.7%) | 16/90 (17.8%) |
| BFCL-derived: schema-valid reference calls | IT | 21/90 (23.3%) | 13/90 (14.4%) | 18/90 (20.0%) |

Nev helps distinguish the authored nearby operations. That improvement does not
transfer to better point estimates on the external BFCL subset. The paired
intervals for external differences include zero; this small selected sample
cannot establish a general regression either. Correct calls are not automatically
correct complete answers. On confusable cases the final-answer completion proxy
is 7/60, 28/60, 41/60 EN and 15/60, 26/60, 29/60 IT, respectively.

## Clarification proxy required correction by trace review

The frozen lexical proxy counted some refusals and wrong questions as successful
clarification. For example, it accepted a response asking the user to supply the
battery percentage instead of identifying the bicycle. It also accepted bogus
requests for `additionalProperties`, which is a JSON Schema keyword, not a tool
argument. Do not quote the raw 71.1% EN / 62.2% IT selected-arm proxy as successful
clarification rates.

The assistant reviewed **all 270 missing-information trials**, grouping identical
case/answer outputs into 66 distinct no-call responses. Any emitted call or
nonanswered outcome fails the original clarification contract. A clean
clarification requests relevant identifying information without fabricated
schema requirements or contradictory capability claims. Asking for an entity's
name or label is accepted, but subsequent resolution is not tested.

| Language | Nesso3 alone | Nev-ranked | Nev-selected |
| --- | ---: | ---: | ---: |
| EN, reviewed clean clarification | 0/45 (0.0%) | 0/45 (0.0%) | 16/45 (35.6%) |
| IT, reviewed clean clarification | 7/45 (15.6%) | 5/45 (11.1%) | 20/45 (44.4%) |

These are assistant review labels, not an independent human audit. All labels,
reasons, trial mappings and the broader relevant-clarification metric are in
[evidence/a100/clarification_review.json](evidence/a100/clarification_review.json).
The original automatic scores remain unchanged for reproducibility.

## Other limits seen in the traces

- Dependent workflows: completion proxy was 1/60 for both standalone and ranking,
  and 0/60 for initial single-tool selection. A reviewed museum example finds the
  exhibit ID and stops without retrieving its room. Initial single-tool selection
  cannot access a second distinct function; this is an architectural restriction.
- Exact date format: all arms scored 0/30. Some reviewed ranked/selected responses
  returned the correct date in words, such as “February 13, 2027”, while the
  request demanded only `2027-02-13`. Zero format compliance is not zero factual
  date accuracy; a full semantic date audit has not been performed.
- Direct answers: 0/30 under the strict no-call/exact-label contract for each arm.
  Sample traces show unnecessary calls or refusals even when the label is supplied.
- Missing records: completion proxy was 0/30 standalone, 1/30 ranked and 0/30
  selected. Repeated cached calls and unrelated tool attempts occurred after
  `not_found`; execution caching prevents rerunning a tool but does not teach the
  generator to stop.
- Unsupported actions: the automatic proxy improved with selection (18/30 EN,
  21/30 IT), but these outputs have not received the exhaustive clarification
  review above. Treat them as provisional behavioral scores.

The narrow supported conclusion is improved tool selection on these authored
catalogs, with improved but still unreliable clarification when one tool is
shown. The experiment does not establish a general-purpose agent or uniform
improvements across datasets. No model/prompt changes were made during the run.

## Complete evidence

- [Frozen automatic results](evidence/a100/RESULTS.md), including all strategies,
  categories, paired intervals and scoring limitations.
- [Raw JSONL](evidence/a100/rows.jsonl), [readable traces](evidence/a100/traces.txt),
  [metadata](evidence/a100/metadata.json) and [analysis](evidence/a100/analysis.json).
- [Protocol](PROTOCOL.md) and [training-exposure disclosure](TRAINING_EXPOSURE.md).

Results use native A100 BF16/FP32 inference, not Mac Q8. Earlier successful
CPU demonstrations remain valid for their particular cases; they do not predict
this broader test's performance.
