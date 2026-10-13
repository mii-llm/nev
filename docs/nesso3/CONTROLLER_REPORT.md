# Where Nesso3 fails, and a bounded application fix

## Result

For **an application that already knows the request is one supported read**, use
Nev to rank tools, Nesso3 to propose the call and arguments, Python to validate
and execute once, and a deterministic bilingual template to report the returned
facts. The new opt-in `--policy single_read` implements this. It does not train
or improve either model's weights, and it does not classify arbitrary requests
as safe or in scope. The unrestricted demo retains `baseline` as its default.

On 16 fresh authored requests fixed before this experiment (8 EN / 8 IT), the
controller executed the correct call and gave a complete answer in all 16.
The original loop gave 11 complete answers; a one-sentence prompt adjustment
gave 10. This is a small test over four read-only mock tools with similar
fixtures, not a production reliability estimate or representative benchmark.

## Failure pattern

Nev's top tool and Nesso3's first call with its arguments were correct on all
24 requests (the eight inspected development examples plus 16 new requests).
This holds under both prompts in this experiment. The bottleneck is mostly
what Nesso3 does after that choice, including extra calls emitted in the same
initial response, not just later turns:

| Observed pattern | Evidence | Application response |
|---|---|---|
| Duplicate calls in one generation | Italian invoice on the development set | Deduplicate before execution; preserve the original emitted calls in logs |
| Unrelated extra calls with invented or wrong-type IDs | Payments in both languages | Reject invalid/ungrounded calls; only one unique valid call may remain |
| Repeated calls after a correct observation | English guide lookups | End the single-read workflow after one execution |
| Incorrect copying of exact returned fields | `invoice_ORD-7482.pdf` becomes `ORD-7482.pdf` in Italian | Render identifiers and filenames directly from the observation |
| Refusal after successful data retrieval plus an error | Italian payments | Do not ask the generator to interpret mixed success/error feedback |
| Incomplete payment lists despite correct total | English payment replies | Render every returned payment and the returned total |
| Prompt sensitivity | The short prompt fixed English BZ-8 but invented a guide URL in Italian | Keep the original compact prompt; do not adopt the tested prompt as a general fix |

The prompt-only candidate replaces the system context with:

- EN: `Use only the necessary tool once, then answer using its result.`
- IT: `Usa solo lo strumento necessario una volta e poi rispondi usando il risultato.`

Schemas, native template, models, greedy decoding and validators stay the same.
It did not give a consistent gain and is retained as `--policy prompt_once`
for reproducibility, not recommended as the fix.

## Use and scope

On the prepared A100:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source

python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy single_read --format text --language it \
  --message "Elenca i miei pagamenti di 2026-06 e dimmi il totale in EUR."

python experiments/hybrid_agent/demo.py --generator nesso3 --arm nev_ranked \
  --policy single_read --format text --language en \
  --message "Find the guide reference for product PX-7."
```

The payment response, formatted by code from the tool observation, is:

> Pagamenti di 2026-06: 24,50 EUR, 39,25 EUR. Totale: 63,75 EUR.

The Nesso3-generated unrelated invoice call is still recorded and rejected.
It is not executed. The renderer uses actual observation fields, not expected
answers or case IDs. A unit test substitutes different amounts and GBP to check
that behavior.

The caller must establish the single-read workflow, for example a product
screen restricted to one lookup request. This prototype has **no general
intent/scope gate**. Do not point the single-read endpoint at unrestricted chat
and assume it will detect cancellation, refund, changing an address, a hidden
second intent or an arbitrary unsupported action. In particular, Nev/generator
agreement and a grounded identifier do not prove that the tool matches the
user's actual request. Detecting those cases requires a separately evaluated
routing layer or application workflow, not a confidence threshold invented
from this test.

Use a separate workflow for:

- Multi-step or multiple-operation requests: execute an explicit application
  plan, or hand off to a separately evaluated planner.
- Missing or multiple references: clarify before acting. The controller defers
  on absent calls, multiple recognized references or multiple valid operations.
- Unsupported actions or broad free-form requests: route outside this narrow
  endpoint; no capability for these is established here.
- Unseen tools or schemas without an approved result renderer: validate a new
  integration before enabling it.

## Controller behavior

1. Keep all four tools available; Nev ranks them once.
2. Ask Nesso3 for one generation using the original compact contract.
3. Reject malformed, truncated, unknown, extra-key, invalid or ungrounded calls.
   For a well-formed list of calls, retain rejection events and deduplicate exact
   valid repeats.
4. Require exactly one unique valid call, agreement with Nev's first choice,
   and exactly one explicit recognized identifier/month in the request.
   Otherwise execute nothing and return an application deferral.
5. Execute the single permitted mock read once. Produce the answer from its
   returned fields, in the user's language. No second generation is run.

Both dropped calls and duplicate calls remain in `emitted_calls`, `errors` and
`policy_events`; execution is separately recorded in `executed_calls`.
`answer_source` is explicitly `application_template` or `application_deferral`.
The normal and prompt-only loops use `answer_source=generator`.

This is deliberately a controller improvement. Nesso3's raw generated calls
still sometimes contain errors. No claim of perfect raw tool calling follows
from the completed application responses.

## Results

Every request was run under all three policies in rotating order, with both
models resident on a shared A100. The generator is Nesso3 at
`56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`; Nev is v3 at
`c5c84121263b423f8846811a24790ab96e66cee3`. No threshold or model training was
introduced. Re-running the eight development examples with the original policy
exactly reproduced their prior calls, executed actions, errors and final text.

**Reviewed task completion** means the executed call matches the request and
the final response includes the requested facts. Rejected extra calls do not
by themselves invalidate this user-facing measure; the raw strict metric
below still penalizes them. The assistant reviewed all 72 outputs against the
requests and observations. This is not independent human or blinded grading.

| Policy | Development EN /4 | Development IT /4 | Fresh EN /8 | Fresh IT /8 | Fresh total /16 |
|---|---:|---:|---:|---:|---:|
| Original loop | 2 | 3 | 6 | 5 | 11 |
| Short prompt | 1 | 2 | 6 | 4 | 10 |
| Single-read controller + templates | 4 | 4 | 8 | 8 | 16 |

The automatic completion proxy checked exact execution and answer anchors. It
incorrectly accepted three incomplete payment lists: development English under
both original/prompt policies, and fresh English `payments_b` under the prompt
policy. These were marked incomplete in the reviewed table without modifying
any original metric or trace. Full audit decisions are retained.

For comparison, the historical **strict mechanical check**, which also requires
no extra emitted calls and no recorded error, gives:

| Policy | Development /8 | Fresh /16 |
|---|---:|---:|
| Original loop | 4 | 9 |
| Short prompt | 3 | 9 |
| Single-read controller + templates | 5 | 12 |

The last row includes an application-written final answer. Seven controller
runs still generated invalid extras or a duplicate (three development, four
fresh); they were filtered, not counted as clean model generations. All 24
single-read runs completed without deferral because this deliberately in-scope
set elicited correct first calls. Deferral behavior was tested with CPU fixtures;
its frequency/accuracy on real out-of-scope model requests is unmeasured.

| Policy | Fresh median EN | Fresh median IT |
|---|---:|---:|
| Original loop | 1.85 s | 1.37 s |
| Short prompt | 1.26 s | 1.44 s |
| Single-read controller | 0.73 s | 0.76 s |

Timing includes Nev routing and mock execution, excludes model loading and real
API latency. 72 trials took 101.3 seconds after warmup; peak allocation was
2,562.7 MiB (~2.50 GiB). The result suggests avoiding a second generation when
answering exact lookup facts. It does not measure how much Nev improves over
Nesso3 alone; this comparison keeps Nev enabled in all policies.

## Reproduction and evidence

```bash
python -m unittest discover -s experiments/hybrid_agent -p test_agent.py
python experiments/hybrid_agent/run_controls.py \
  --output "../results/nesso3-controls-$(date +%Y%m%d-%H%M%S).json"
```

Nine CPU tests cover the original boundary and scoring plus single-read
execution, duplicate suppression, invalid extra calls, model disagreement,
multiple references/operations, malformed/truncated/ungrounded outputs and
rendering different observation values. Both local and A100 runs passed.

- [Every readable trace](CONTROL_TRACES.md)
- [All 72 raw runs, source hashes and automatic metrics](evidence/a100-controls.json)
- [Complete answer audit](evidence/a100-controls-audit.json)
- Frozen requests: `experiments/hybrid_agent/control_cases.json`
- Implementation: `experiments/hybrid_agent/single_read.py` and `agent.py`

The 16 fresh examples were authored before this run but after inspecting the
eight development failures. They use new wording and references over the same
four tools and fixed mock response shapes. They are not independent domains,
new tool families, adversarial prompts or a test of business authorization.
