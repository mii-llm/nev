# Use Nevso from Python

Supply Python functions with JSON schemas. Nev chooses or orders tools, Nesso3
proposes a call, and the existing controller validates it before invoking your
function. The function's result returns to Nesso3 for the answer.

This is a **source-checkout API**, using the same model backends and controller
as the demos. It does not merge weights or add a newly trained model.

## Install

Follow the [Linux/macOS CPU quick start](QUICKSTART.md). The setup command now
also installs `nevso-preview` editable in `experiments/cpu_gguf/.venv`. For an
already prepared checkout, install just the new API:

```bash
# From the Nev repository root, after updating the checkout:
experiments/cpu_gguf/.venv/bin/python -m pip install --no-deps -e .
```

For the [native CUDA environment](GPU_GUIDE.md), activate that environment and
run `python -m pip install --no-deps -e .` instead. Runtime dependencies and
model downloads come from the relevant setup guide, not this small API package.
Keep the checkout: it contains the controller, CPU binary and downloaded files.
Importing `nevso` alone does not load models or change environment variables.

## Run the Python-function example

```bash
experiments/cpu_gguf/.venv/bin/python examples/nevso_api.py \
  --output "results/nevso-api-$(date +%Y%m%d-%H%M%S).json"
```

The [example source](../../examples/nevso_api.py) registers three ordinary Python
functions: soil pH, soil moisture and tank level. It executes two requests,
Italian and English, prints readable traces and saves JSON. All three functions
use local mock data. Add `--strategy select` to expose one tool, or `--strategy
none` to compare Nesso3 alone. Native GPU users run the same script with
`--engine cuda` in the CUDA environment.

## Register your own tools

Here is the minimal registration pattern. Use several tools to make tool
selection meaningful; this one-tool snippet illustrates the handler contract.

```python
from nevso import Agent, Tool, format_trace

def read_soil_ph(bed_id):
    # Replace this mock with your application's read operation.
    return {"soil_ph": 6.4} if bed_id == "B-73" else {"error": "not_found"}

ph_tool = Tool(
    name="read_soil_ph",
    description={
        "en": "Read the soil pH measurement for a planting bed.",
        "it": "Leggi il valore del pH del terreno in un’aiuola.",
    },
    parameters={
        "type": "object",
        "properties": {"bed_id": {"type": "string"}},
        "required": ["bed_id"],
        "additionalProperties": False,
    },
    handler=read_soil_ph,
)

with Agent([ph_tool], engine="gguf", strategy="rank") as agent:
    result = agent.run("Leggi il pH del terreno nell’aiuola B-73.", language="it")
    print(result["status"], result["final"])
    print(format_trace(result))
```

Handlers receive keyword arguments, so their parameter names must match the
schema. Return JSON-serializable values. A single description string is also
accepted and is used in both languages; a dictionary must provide both `en`
and `it`. Tool names must be unique identifiers. Schemas and descriptions are
copied at registration, so later changes to the input dictionaries do not alter
the active agent.

## Choose a strategy

| Strategy | What Nesso3 sees | Tradeoff |
| --- | --- | --- |
| `rank` (default) | All tools, ordered by Nev | Keeps alternatives; more prompt tokens |
| `select` | Only Nev's top tool | Shorter prompt; wrong selection hides the correct tool |
| `none` | Your original tool order | Nesso3-only baseline; skips Nev ranking |

Nev ranks **once at the start of each request**, matching the launch comparison.
It does not rerank after each observation. You can override the default on a
call: `agent.run(text, language="en", strategy="select")`. Both models remain
loaded in all modes, including `none`. Compare modes on your own catalog rather
than assuming selection is always best.

The `with` block loads models once and closes owned resources even if a handler
raises an exception. Requests on one agent must be sequential; overlapping use
fails explicitly. Each request has a fresh history and duplicate-call cache;
this API does not implement conversational memory. The native backend uses its
existing pinned checkpoints. GGUF defaults are Q8 and four threads; `precision`
and `threads` apply only to GGUF. Native CUDA uses Nev FP32 and Nesso3 BF16.

## Interpret results and failures

`run()` returns a dictionary containing:

- `final`, `status` and `errors` from the controller.
- `initial_ranking`: Nev's choice and probabilities, or `None` for the baseline.
- `executed_calls` and `trace`: tool order, generated text, validation and results.
- `strategy`, `engine`, `precision`, `rank_ms` and `total_ms`.

`status="answered"` means Nesso3 produced an answer, not that the answer is
factually correct. Validation errors may remain even if a later turn answers.
The wrapper does not assign a success score to arbitrary user requests. Timings
include initial ranking and the controller, exclude model loading, and include
first-request warmup unless you warm the instance separately. Probabilities
are not a calibrated production acceptance threshold.

The controller checks JSON schemas and argument provenance before execution.
Arguments must be grounded in the request, earlier observations or schema
enums. Arbitrary inferred strings and reformatted dates can therefore be
rejected. It retains the existing limits: four model turns, at most four calls
per batch and eight executions per request. Identical calls are cached within
a request. Invalid batches execute no handlers.

Handler exceptions and non-JSON outputs propagate to your Python caller;
the wrapper does not automatically retry them. Any earlier calls may already
have executed: there is no transaction or rollback. Your application supplies
permissions, timeouts and any confirmation needed for real tool operations.
Use read-only functions first. Final prose is not independently verified, and
general multi-step or unsupported-action handling remains outside the validated
launch scope.

## Tests and implementation

```bash
experiments/cpu_gguf/.venv/bin/python -m unittest discover \
  -s tests -p test_nevso_api.py -v
```

The tests use a scripted backend with the real controller, covering dispatch,
batch validation, hidden tools, caching, exceptions and resource cleanup.
The real-inference regression is separate:

```bash
experiments/cpu_gguf/.venv/bin/python tests/check_nevso_api_inference.py \
  --output "results/nevso-api-parity-$(date +%Y%m%d-%H%M%S).json"
```

This checks six Linux Q8 launch outputs against the saved CLI run. Different
hardware or kernels may change generation; inspect any mismatch rather than
interpreting this as a broad accuracy test.

### Verified on Linux, 3 November 2026

In the [previously validated Seeweb CPU environment](LINUX_VALIDATION.md), the
editable install succeeded and `from nevso import Agent, Tool` also worked from
outside the checkout. All **nine API tests passed**, both requests in the new
three-function example answered correctly, and all **six parity trials matched
the saved CLI outputs** for executed calls, final answers, statuses and errors.
Baseline failures were preserved. This establishes wrapper parity on those
examples, not a model-quality improvement. The native CUDA backend is supported
by the wrapper, but this API revision was tested with GGUF CPU, not rerun on GPU.

- [Example results](evidence/python-api-20261103/api-example.json).
- [Six parity trials](evidence/python-api-20261103/api-parity.json).
- [Unit-test output](evidence/python-api-20261103/unit-tests.txt).
- [Validation summary and source hashes](evidence/python-api-20261103/validation.json).

Source: [API](../../nevso/api.py), [example](../../examples/nevso_api.py),
[existing controller](../../experiments/cpu_gguf/abstract_agent/runtime.py).
Advanced integrations can supply a `backend` implementing `generate`, `rank`
and `synchronize`; it is borrowed and must be closed by its owner. An explicit
`repo_root="/path/to/nev"` selects a prepared checkout if the API package is
installed elsewhere. Standalone wheel installation does not bundle model
backends, binaries or weights.
