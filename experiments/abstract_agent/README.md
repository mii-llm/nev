# Schema-driven Nesso3 + Nev experiment

This separate experiment tests the models without the earlier shipping/invoice
grammar or deterministic answer templates. The controller receives a request,
language, runtime tool schemas, and an executor callback. It receives no task
category, expected plan, answer anchor, or case ID. All final prose is generated
by Nesso3. The mock executor is deliberately separate from the evaluation labels.

## Run

In the prepared A100 environment, with both pinned models already cached:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source
python -m pip install -r experiments/abstract_agent/requirements.txt

python experiments/abstract_agent/demo.py --toolset sensors --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'

python experiments/abstract_agent/demo.py --toolset sensors --language it \
  --message 'Trova il sensore di temperatura in Studio, poi leggi la sua temperatura.'

python experiments/abstract_agent/run_eval.py \
  --output "../results/abstract-$(date +%Y%m%d-%H%M%S).json"

python -m unittest discover -s experiments/abstract_agent -p 'test_*.py' -v
```

All commands use simulated, read-only tools. A fresh output path is required.
`--arm nesso_only`, `--arm shuffled`, `--arm nev_ranked`, or `--arm nev_gated`
selects a configuration. `--toolsets /path/to/custom.json --toolset name` selects
another registry without changing the controller. A production integration would
replace `FixtureExecutor` with an application-owned dispatcher and add its own
authorization rules; this mock pilot does not validate real side effects.

## What is abstract, and what is supplied by an application?

`runtime.py` contains parsing, schema validation, generic argument provenance,
batch handling, caching, and the bounded inference loop. `backend.py` loads and
prompts the pinned models. Neither file contains a tool name or task grammar.
`fixtures.py` dispatches exact calls to a mock response catalog. `toolsets.json`
supplies tool names, localized descriptions, JSON schemas, and mock observations.
`cases.json` supplies evaluation requests and gold labels; only the evaluator
reads its gold labels, **after** model inference. `build_cases.py` records how the
54 requests and fixture registries were authored before the first scored run.

Schema-driven does not mean descriptions can be removed: the models still need
the meaning of each tool. Three toolkits (notes, sensors, media) exercise the same
engine. An opaque-name control replaces tool names with `tool_a7` etc., retaining
descriptions and parameter names. These are new fixtures in this project, not
proof of absence from model training data.

## Frozen protocol

- 42 requests: seven scenarios in three toolkits, each paired in English/Italian.
  The scenarios are direct read, another tool/argument selection, two-step
  lookup→read dependency, two independent reads, missing required value,
  unavailable action, and a simple answer needing no tool.
- 12 additional requests: direct and dependent scenarios under opaque tool
  names. Total **54 requests, 27 per language**, each run under all four arms.
- `nesso_only`: original tool order, no Nev inference.
- `shuffled`: deterministic per-case shuffled order, no Nev inference.
- `nev_ranked`: Nev orders all tools before every generation, using the request
  and accumulated calls/results. No tool is removed.
- `nev_gated`: the same ranking, plus answer/clarify/unsupported choices. If Nev
  selects one of these and Nesso proposes a call, execution stops. No replacement
  answer is fabricated. A blocked call is **not** a successful clarification.
- Arms rotate execution order by case index. Same native Nesso template, greedy
  generation, compact schemas, and generic validation in every arm. Four turns,
  192 generated tokens per turn, at most four calls per batch/eight executions.
- Strict JSON and schema checks precede execution. A batch is rejected in full
  if any call fails; errors are returned for possible repair. Argument scalars
  must occur in the user input, a prior successful observation, or schema enums.
  This restricts inventions but cannot prove user intent or correct field binding.
  Enum values are allowed by schema even if the user did not specify one. This
  literal-provenance policy may reject legitimate paraphrases or computed values.
- Duplicate exact calls return cached observations without another execution.
  Errors and repeated generations remain in the trace. A lookup-dependent read
  must occur on a later turn using the returned opaque ID, absent from the request.
- No prompt adaptation, training, or fixture replacement after inspecting results.
  All failures remain in the raw report. This is a small authored diagnostic
  pilot, not a representative public benchmark or an estimate of broad accuracy.

## Scoring and deployment limits

Report exact executed plans separately from complete answers. Parallel plans are
order-insensitive; dependent plans require correct order on separate turns.
`completion_proxy` additionally requires the expected answer anchors and an
answered status. It is a mechanical screen, not a semantic judge: inspect traces
for unsupported claims, contradictions, incomplete answers, and false positives.
The raw `first_call_exact` field checks whether the first emitted call is a member
of the expected plan; it does not require the first dependency step. Use the
full-plan metric for ordered correctness. Missing-value/unsupported language is
explicitly left for manual audit. Returning
no call, blocking a call, and explaining a limitation correctly are distinct.

Both models remain resident for every arm to compare warm request timings; the
Nesso-only arm makes no Nev inference but is not a standalone memory measurement.
Model allocation after each load and peak PyTorch allocation are recorded. The
backend checks for four GiB free VRAM and caps its CUDA allocator to four GiB;
CUDA context and other non-PyTorch allocations are not included in that cap.
Latency includes generation, Nev ranking where used, validation, and mock dispatch
on a shared A100. It does not include model loading or real tool IO.

The Nesso weights run in BF16 and Nev in FP32. No quantization, CPU, phone, edge
GPU, battery, or thermal test has been performed. A good result here would support
further device testing, not establish on-device readiness.
