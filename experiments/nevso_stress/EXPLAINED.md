# What the Nev + Nesso3 results mean

**Nev improved choosing the right function on our authored catalogs. The
complete agent is less reliable than that tool-call score suggests.**

## There are three jobs in a request

1. Choose the function: Nev can help here by ranking the catalog or exposing
   only its first choice to Nesso3.
2. Supply its arguments: Nesso3 writes the call, such as a book or sample ID.
3. Use the returned facts and finish: Nesso3 must answer the actual question,
   avoid inventing facts and stop when appropriate. Multi-step tasks also require
   choosing another function after seeing the first result.

A correct executed-call score checks the function and arguments. It does not
prove that the final answer is correct, complete or well formatted. Repeated
cached calls are not counted as new executions, so a model can execute the right
function and then get stuck repeating it.

## A real failure makes the difference clear

Request: **“Leggi l’acidità di SA-521 come pH, non la temperatura.”**

In the recorded order-0, Nev-selected run:

```text
Nev selects:    get_sample_ph
Nesso3 calls:   get_sample_ph(sample_id="SA-521")
Tool returns:  {"ph": 6.8}
Nesso3 answers: “La temperatura è 6.8°C.”
```

The call is correct. The answer is wrong: it turns a pH reading into a
temperature. This is a final-answer failure, not a wrong function choice.
The trace is preserved in `evidence/a100/rows.jsonl`, case
`lab-confusable-0-it`, arm `nev_selected`, order `0`.

Another example asks for available copies and a library branch. The tool returns
three copies at Levante, but Nesso3 answers only “Levante”. The route and
arguments are right; the answer omits part of what the user requested.

## Read the authored-tool results at both levels

There were 20 distinct confusing-tool requests per language, each tested with
three starting tool orders: **60 trials per language and configuration**.

| Metric | Language | Nesso3 alone | Nev ranks all tools | Nev selects one tool |
| --- | --- | ---: | ---: | ---: |
| Correct executed calls | EN | 17/60 (28.3%) | 40/60 (66.7%) | 56/60 (93.3%) |
| Correct executed calls | IT | 23/60 (38.3%) | 44/60 (73.3%) | 43/60 (71.7%) |
| Calls + automatic final-answer checks | EN | 7/60 (11.7%) | 28/60 (46.7%) | 41/60 (68.3%) |
| Calls + automatic final-answer checks | IT | 15/60 (25.0%) | 26/60 (43.3%) | 29/60 (48.3%) |

The lower two rows are automatic completion proxies, not an independently
reviewed factual-accuracy score. They can miss errors or reject valid wording.
The three tool orders repeat the same requests; they are not 60 independent
questions. Ranking and selecting one tool are different strategies, and neither
wins every metric or language.

## Why BFCL is a different result

Both panels check function names and arguments. The BFCL-derived panel uses
external APIs with different names, schemas, defaults, date/location conventions
and reference alternatives. Its 30 requests per language are checked as calls
only; no final-answer accuracy is measured. It is a filtered adapted subset,
not the official full BFCL benchmark.

On that panel, Nesso3 alone scored 19/90 EN and 21/90 IT. Nev-selected scored
16/90 EN and 18/90 IT. There is no improvement in these point estimates, although
the small paired comparison does not establish a general regression. The
success on authored catalogs does not automatically transfer to these APIs.
Qwen3-0.6B completed the same test and scored **45/90 EN (50.0%) and 43/90 IT
(47.8%)** on BFCL calls. Small parameter count alone therefore does not explain
the gap; this comparison still does not isolate size from training or
architecture. On the authored panel Qwen made 44/60 correct calls in English
and 45/60 in Italian, while passing answer checks on 44/60 and 43/60. Nev-selected
+ Nesso3 has stronger English tool-call accuracy, but Qwen more often turns
successful calls into complete answers under these checks. See the
[full Qwen comparison](qwen_baseline/REVIEW.md).

## Other scores need care

- **Missing input:** the first lexical scorer sometimes mistook a refusal or
  wrong question for a good clarification. Reviewed clean clarification for
  Nev-selected is 16/45 EN (35.6%) and 20/45 IT (44.4%), not the original proxy's
  71.1% and 62.2%. These review labels were produced by the assistant.
- **Multiple steps:** initial single-tool selection cannot expose a different
  second function. Even when all tools remain visible, Nesso3 often stops after
  finding an ID or repeats calls. These results describe the current workflow.
- **Dates:** `February 13, 2027` can be factually correct while failing an explicit
  request for only `2027-02-13`. A zero format score does not mean every date was
  factually wrong.
- **Tool errors:** the model often repeats calls after `not_found` instead of
  explaining that the data are unavailable.

This supports using Nev as a tool-selection component for suitable small
catalogs, while testing answer generation and workflow completion separately.
It does not yet support a broad claim of reliable autonomous task completion.

[Full review and evidence](REVIEW.md) · [Qwen comparison setup](qwen_baseline/README.md)
