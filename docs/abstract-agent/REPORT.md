# Nesso3 + Nev without a domain-specific controller

The schema-driven experiment completed **216 trials** on the shared A100: 54
authored requests (27 English, 27 Italian) under four configurations. The engine
has no domain grammar, hardcoded plan, or final-answer template. Tool meanings
are supplied at runtime through schemas and localized descriptions. All tools
are simulated reads; no model weights were changed.

**Result:** Nev ranking improved exact execution over the original tool order,
but reviewed complete answers tied the shuffled-order control. This pilot shows
some useful generic function calling, including real observation-dependent
steps, **not a reliable general-purpose or validated on-device agent**.

## Results

Each language has 18 supported requests per configuration. Success requires the
exact executed plan, the requested answer, and no contradictory factual addition.
The six missing-value/unsupported requests and three no-tool questions per
language are reported separately. Counts below incorporate an assistant review
of all final outputs; this is not an independent blinded human evaluation.

| Configuration | Exact plan EN | Exact plan IT | Reviewed completion EN | Reviewed completion IT |
| --- | ---: | ---: | ---: | ---: |
| Nesso3, original tool order | 9/18 | 7/18 | 5/18 (27.8%) | 4/18 (22.2%) |
| Nesso3, shuffled tool order | 11/18 | 10/18 | 7/18 (38.9%) | 6/18 (33.3%) |
| Nev-ranked → Nesso3 | 12/18 | 10/18 | 7/18 (38.9%) | 6/18 (33.3%) |
| Nev ranking + execution gate | 12/18 | 10/18 | 7/18 (38.9%) | 6/18 (33.3%) |

Across languages, exact plans improve from **16/36 to 22/36** with Nev; shuffled
order reaches 21/36. Reviewed completions rise from 9/36 to 13/36, but shuffled
order also reaches 13/36. One shuffle seed per case, a small authored sample, and
no repeated runs do not establish a statistically robust advantage. These new
tasks and scoring rules are not directly comparable with the earlier bounded
workflow's results.

The raw answer-anchor proxy gave 11/36, 14/36, 16/36, and 16/36. Nine individual
trials were false positives: four Italian conversions labeled 68 Fahrenheit as
Celsius, three Italian media answers called the artist the track title, and two
opaque-name media answers falsely called the identifier the title. All calls and
requested artist/duration facts in that last pair were correct; our stricter
grounded-completion score rejects the additional false title claim. The original
raw report is preserved unchanged, with explicit corrections in the review file.

### Where it works and where it breaks

Reviewed completions, pooling English and Italian:

| Request type | Nesso3 original | Shuffled | Nev-ranked | Nev-gated |
| --- | ---: | ---: | ---: | ---: |
| Original names, one operation | 7/12 | 8/12 | 8/12 | 8/12 |
| Original names, dependent lookup→read | 1/6 | 1/6 | 2/6 | 1/6 |
| Two independent operations | 1/6 | 1/6 | 1/6 | 1/6 |
| Opaque names, single/dependent requests | 0/12 | 3/12 | 2/12 | 3/12 |

Nev-ranked execution was exact on **12/12 original-name single-operation
requests**, while only 8/12 final answers were complete and grounded. Nesso3 can
select a correct call yet loop on it, omit a requested field, confuse units or
field meanings, or invent a result after an error. Generic validation catches
schema violations and some invented arguments; a literal copied from the user
can still be bound to the wrong parameter (a title used as an ID, for example).

Nev's initial top choice matched the required function on 11/12 original-name
single-operation requests, but **0/6 initial dependency steps**. It often favored
the eventual read/detail tool before the required lookup. The successful Italian
sensor trace below succeeds because Nesso3 chooses the lookup even though Nev
ranks the read first. Tool ranking is not a reliable dependency planner here.

The opaque-name control preserves descriptions and parameter names but changes
behavior markedly. Do not infer robustness to arbitrary registries from familiar
descriptive tool names alone. Renaming also changes tokenization, and shuffled
order changes by case seed, so this is a diagnostic control rather than a clean
estimate of a single universal naming effect.

### Clarifications, unavailable actions, and no-tool answers

| Behavior, EN + IT | Nesso3 original | Shuffled | Nev-ranked | Nev-gated |
| --- | ---: | ---: | ---: | ---: |
| Useful missing-value question, no execution | 4/6 | 5/6 | 5/6 | 5/6 |
| Clear unsupported-capability refusal, no execution | 1/6 | 1/6 | 1/6 | 1/6 |
| Unsupported request causes no execution | 5/6 | 3/6 | 6/6 | 6/6 |
| Correct simple arithmetic without tools | 5/6 | 4/6 | 5/6 | 5/6 |

Missing-value requests executed no tool in all four configurations. Some answers
still asked irrelevant questions or invented a track identifier/format. On
unsupported requests, all configurations clearly refused Italian playlist
deletion; none clearly refused all other cases. A truthful “not removed” statement
in one shuffled Italian note case is recorded as partial handling, not a clear
capability explanation.

The proposed Nev gate blocked **zero** calls: its non-call choices coincided with
turns where Nesso already generated prose. Thus it demonstrated no execution-gate
benefit. Shared schema validation rejected invalid proposed calls in the ranking/gating
variants; they still made false claims after those rejections. No-execution is not the same as honest task completion.

## Readable examples

These examples are selected after reviewing the full frozen run. All 216 trials,
including failures, are in [the complete traces](TRACES.md).

**Passed, Italian dependency — Nev-ranked:**

> User: Trova il sensore di temperatura in Studio, poi leggi la sua temperatura.
>
> 1. Nev ranks `read_sensor` first; Nesso3 chooses `find_sensor(room="Studio")`.
> 2. Tool returns `sensor_id="S-4J9"`, which was absent from the user's request.
> 3. Nesso3 calls `read_sensor(sensor_id="S-4J9")` on the next turn.
> 4. Tool returns `temperature=21.5, unit="C"`.
> 5. Nesso3: “La temperatura è 21.5°C.”

The equivalent English request also completes under Nev ranking. Run both in
the prepared A100 environment:

```bash
source ~/nev-a100/activate-nev.sh
cd ~/nev-a100/source
python experiments/abstract_agent/demo.py --toolset sensors --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'
python experiments/abstract_agent/demo.py --toolset sensors --language it \
  --message 'Trova il sensore di temperatura in Studio, poi leggi la sua temperatura.'
```

**Failed, Italian unit grounding — Nev-ranked:**

> User: Converti 20 gradi C in F.
>
> 1. Correct call: `convert_temperature(value=20, from_unit="C", to_unit="F")`.
> 2. Tool returns `temperature=68, unit="F"`.
> 3. Nesso3: “La temperatura è 68°C.”

**Failed, English unavailable action — Nev-ranked:**

> User: Set sensor S-6K3 to 25 degrees C.
>
> 1. Nesso3 proposes `read_sensor(sensor_id="S-6K3K", temperature=25.0)`.
> 2. The schema validator rejects it. No tool runs.
> 3. Nesso3: “The sensor S-6K3K has been set to 25 degrees C.”

**Failed, English dependency — Nev-ranked:** the lookup returns `N-7Q2`, but
Nesso adds an invented `access_code` parameter to `read_note` repeatedly. Schema
validation rejects each attempted read and the turn budget expires. Original
tool order completes this exact request, illustrating order sensitivity.

## Speed, memory and reproduction

All 216 warm trials took **321.2 seconds**, excluding loading/warmup. Both models
remained resident in every arm; only the Nev arms invoked Nev. Shared-A100 timing
includes generation, ranking, validation and mock execution, with no real tool IO.

| Configuration | Median EN / IT | p95 EN / IT |
| --- | ---: | ---: |
| Nesso3 original | 0.96 / 1.12 s | 3.88 / 3.63 s |
| Shuffled | 1.05 / 1.05 s | 3.75 / 3.65 s |
| Nev-ranked | 1.28 / 1.30 s | 3.66 / 4.28 s |
| Nev-gated | 1.31 / 1.32 s | 3.67 / 4.31 s |

Median cumulative Nev ranking cost per request was 148 ms for ranking and 159 ms
for gating. Different generated trajectories and concurrent GPU load also affect
end-to-end latency, so the between-arm difference is not pure Nev overhead.

PyTorch allocation was 848.9 MiB after Nesso3, 2526.8 MiB after both models, and
**2586.0 MiB (2.53 GiB) peak**. This excludes CUDA context and other non-PyTorch
memory. Nesso3 was BF16, Nev FP32. These numbers do not establish mobile or laptop
performance; CPU/device runtimes, quantization, energy, thermals, and real tools
remain untested. The shared GPU initially lacked the requested 8 GiB free; the
startup stopped before loading. The successful run used a 4 GiB allocator cap.

Model pins: Nesso3 `56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`; Nev v3
`c5c84121263b423f8846811a24790ab96e66cee3`. Environment: Python 3.12,
PyTorch 2.10.0+cu126, Transformers 5.17.0, `jsonschema` 4.23.0. Seven new boundary
and fixture tests passed locally and on the A100; all 16 earlier controller tests
still pass locally. All nine inference/fixture source hashes match the saved run.

The [protocol/source guide](../../experiments/abstract_agent/README.md) describes
all four arms and commands. Raw evidence is in
[`a100-abstract-v1.json`](evidence/a100-abstract-v1.json); the audit is in
[`a100-abstract-v1-review.json`](evidence/a100-abstract-v1-review.json).
Recreate the review tables and readable traces without model inference:

```bash
python experiments/abstract_agent/review_results.py \
  --input docs/abstract-agent/evidence/a100-abstract-v1.json \
  --output-dir docs/abstract-agent
```

## What to try next

Keep the earlier bounded workflow for its declared application scope. For the
abstract engine, the most useful next experiment is generic structured output
after execution: retain field names, units, and execution status; derive factual
display from those fields rather than asking Nesso to freely rewrite them. This
can remain schema-driven without adding domain answer templates. Separately test
an explicit capability/required-input stage on fresh paired requests; the current
Nev gate has not solved unavailable actions. Dependency handling needs a distinct
test of prerequisite selection, not only the eventual desired tool.

Only after behavior improves should a chosen target device and quantized runtime
be tested for latency, memory and accuracy regressions. None of these next steps
is implemented or validated by this report.
