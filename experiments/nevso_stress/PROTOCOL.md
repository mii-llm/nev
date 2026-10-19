# Nevso bilingual stress test — frozen protocol, 19 October 2026

Status at freeze: **no stress-test inference has been inspected**. This is a new
200-request development evaluation, not an official BFCL leaderboard submission
or an independently authored, contamination-free benchmark. Scores are not
expected to match the curated greenhouse demonstration.

## Data and sampling

Exactly 100 English/Italian pairs:

| Category | Pairs | Requests |
| --- | ---: | ---: |
| BFCL-derived single-call selection | 30 | 60 |
| Confusable functions / negation / distracting details | 20 | 40 |
| Missing required argument | 15 | 30 |
| Unsupported action or direct answer | 15 | 30 |
| Two dependent calls | 10 | 20 |
| Permanent tool error or exact date formatting | 10 | 20 |

External data come from BFCL `live_multiple` at the revision in
[source/provenance.json](source/provenance.json). Selection is seeded, restricted
to short single-user English requests and flat schemas with 2–6 tools, and
limited to one request per distinct catalog. Full filtering rules, original
selected rows and reference alternatives are retained. These restrictions make
this a small-model-compatible slice, not a representative BFCL sample. The
custom flat alternative checker is not BFCL's official AST evaluator.

English external requests are unchanged. Their Italian translations are
assistant-authored and preserve query literals, enum strings and identifiers.
External API descriptions remain English in both languages. Workflow tool
descriptions and requests are bilingual. Names and parameter keys remain stable.
The `dict` and `float` schema types are normalized to JSON Schema `object` and
`number`. External function calls are generated and checked only: no web search,
payment, account mutation or other real service is executed.

One source prompt (`live_multiple_808-175-14`) contradicts its explicit date with
a weekday. Keep it in raw results; report a sensitivity view excluding this pair.
Schema validity and reference agreement are separate because some upstream
optional reference alternatives do not conform to their schemas. English/Italian
proper-name localization is deliberately limited to keep API arguments stable.

The 70 authored pairs cover libraries, parcels, museums, bicycle stations and
laboratory records. Each uses six domain functions and six out-of-domain
functions. All tools are local read-only fixtures. Dependent cases hide the
second-call ID until the first tool returns it. Missing-argument cases require a
relevant clarification as the first response; this test does not simulate the
user's subsequent reply. Unsupported and direct-answer cases are distinct in
the case metadata. Five error cases use permanent `not_found`, not transient
retry recovery. Five format cases require only a YYYY-MM-DD date.

No exact request overlaps were found in the available local recipe/source scan;
the full training corpora were unavailable. See
[source/overlap_check.json](source/overlap_check.json). Pretraining/SFT exposure to
BFCL remains unknown. Fresh authored cases are not independent of the assistant
that designed this evaluation.

## Comparison

Three arms, three seeded tool orders, identical EN/IT order within each pair:
**1,800 trials**. Case order is seeded; arm execution order rotates.

1. Nesso3 sees all available tools.
2. Nev ranks all tools once before Nesso3 generation.
3. Nev selects one tool once before Nesso3 generation.

The controller, prompts, generation limits, model revisions and precision are
otherwise fixed. No prompt changes based on stress results. The selected arm
cannot access a second distinct tool: its dependent-task results describe this
architectural boundary, not a fair test of a dynamically rerouted agent. Report
that category separately. No hidden top-k fallback, answer-key routing or answer
templates are introduced.

Primary run: shared A100, Nesso3 BF16 and Nev v3 FP32, with the existing 4 GiB
process allocation cap. Timings include routing and generation, exclude loading
and warm-up, and are illustrative on a shared GPU. CPU Q8 is supported by the
same runner but is a separate measurement; do not label GPU results as CPU.
The 4-case pilot reuses old greenhouse examples and synthetic arithmetic; it is
not part of the 200 requests. It checks execution and result persistence, not
whether model accuracy is high enough to proceed.

## Scoring and reporting

Report by source/category, language and strategy; do **not** combine BFCL
call-only scores and workflow completion into one headline number.

- External: single correct function name, reference-argument agreement and
  schema-valid reference call. Whitespace/case/semantic rewrites are not silently
  normalized by our checker; this can differ from official BFCL scoring.
- Workflows: exact executed call sequence (dependent calls must occur in order
  on separate turns), final-answer assertions, exact output format when required.
- Clarification: no emitted or executed calls, nonempty final answer, a request
  for information and relevant missing-argument concepts.
- Unsupported: no emitted or executed calls and an explicit capability limit.
- Direct answer: no calls and the requested exact supplied label.
- Error: expected failed lookup and acknowledgment of unavailable data.
- Record emitted calls, controller-rejected calls, execution and final output
  separately. A rejected bad call is not a successful no-call decision.

Workflow completion and clarification/error phrase checks are **automatic
proxies**, not verified factual success. They may accept contradictory text or
reject a valid paraphrase. Preserve raw traces, review failure/success examples,
and label any later manual/assistant review separately. Do not call a substring
match a hallucination-free answer. Dates in words can fail the assertions even
when semantically correct; exact-format results remain a separate metric.

Use paired results: each strategy sees the same requests and starting order.
Report per-order results, counts of requests passing all three orders, and
paired improvements/regressions. Resampling should cluster by bilingual pair
(all languages and tool orders together), not treat 1,800 trials as independent.
Small category counts remain descriptive, even with intervals.

## Reproduce

From the GitHub checkout, use the existing GPU environment described in
[the GPU guide](../../docs/nevso/GPU_GUIDE.md):

```bash
python -m unittest discover -s experiments/nevso_stress -p test_eval.py -v
python experiments/nevso_stress/run_eval.py --engine cuda \
  --suite experiments/nevso_stress/pilot.json --orders 0 \
  --output results/nevso-stress-pilot
python experiments/nevso_stress/run_eval.py --engine cuda \
  --output results/nevso-stress-a100
```

For Mac CPU after the existing Q8 setup:

```bash
experiments/cpu_gguf/.venv/bin/python experiments/nevso_stress/run_eval.py \
  --engine gguf --threads 4 --output results/nevso-stress-q8
```

Use a fresh directory for a new run; `--resume` continues matching frozen inputs.
Each directory contains `metadata.json`, `rows.jsonl`, `summary.json` and readable
`traces.txt`. The freeze manifest is checked before inference; source edits need
a new version of the evaluation. The runner stops on infrastructure errors and
records the failure without treating it as a scored model response.

References: [BFCL](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard),
[ToolSandbox](https://github.com/apple-aiml-research/ToolSandbox). The latter
inspired tool-order/distractor and dependent-workflow checks; no ToolSandbox
score or data reuse is claimed. Upstream BFCL attribution/license is in `source/`.
