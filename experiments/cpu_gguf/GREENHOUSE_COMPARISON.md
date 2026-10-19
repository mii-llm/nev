# A new domain: greenhouse operations

This example applies **Nev selection → Nesso3 call → controller validation →
mock result → Nesso3 answer** to a greenhouse tool catalog. No models are
retrained. The inference prompts, routing method, call validation and mock
executor are unchanged from the earlier notes/sensors/music comparison.

The domain was selected before writing the cases or running inference:
`random.Random(20261017).choice(...)` over museum visitor services, bicycle rental,
greenhouse monitoring, airport information and public library. This is one
sampled application example, not evidence from a random sample of all domains.
Some operations, such as temperature lookup, overlap semantically with earlier
sensor examples; the schemas, vocabulary and fixtures are newly authored.

The 12 tools read air temperature, humidity, soil moisture, soil pH, light,
irrigation schedules, tank levels, crop names, planting dates, harvest dates,
ventilation state and fertilizer schedules. They do not actuate equipment or
provide agricultural recommendations. Every tool is a local read-only mock.

For the same frozen example on NVIDIA GPUs, see the [GPU guide](../../docs/nevso/GPU_GUIDE.md). GPU measurements use native BF16/FP32 models and are kept separate from these Q8 results.

## Run on Mac CPU

After the existing setup, from `experiments/cpu_gguf`:

```bash
# Needed only if the two Q8 models and CPU runtime are not installed yet.
./setup.sh --model both --precision q8

RUN="results/greenhouse-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python compare_routing.py \
  --suite greenhouse_suite.json --precision q8 \
  --output "$RUN.json"

# Read the model calls, tool results and final answers for all three arms.
cat "$RUN.txt"
```

`--language en` or `--language it` runs one language. `--case` accepts any case ID
from the suite, such as `get_irrigation_schedule-it`. Filtered runs retain the
full suite's tool order. The command creates a JSON report and readable text
traces without overwriting previous runs.

## How the domain is supplied

The [suite JSON](greenhouse_suite.json) contains:

- `toolsets`: English/Italian function schemas and synthetic tool responses.
- `cases`: requests, expected calls and answer fragments for evaluation.
- `scope` and `domain_selection`: provenance and limits.

The runner takes `--suite path/to/another_suite.json`; no domain-specific routing
code is needed. Only the request and tool schemas reach Nev and Nesso3. Expected
calls and answer fragments are used after inference for scoring. Fixture results
reach Nesso3 only through a tool call. This experiment covers supported requests
requiring one tool, with required identifiers explicitly supplied.

## Evaluation method

All **24 requests** (12 parallel English/Italian pairs) were frozen before
inference, and all results are retained. Three arms use the same requests:
Nesso3 with all 12 tools; all tools ordered by Nev; and only the tool selected by
Nev. Model precision is Q8, with four CPU threads on the same Apple M3 Pro.
Both models remain resident in every arm. Warm request timings include routing,
generation and validation, but exclude initial model loading.

Exact-call accuracy is checked automatically. Answer fragments are only a
proxy; final-answer review separately checks that facts and units match the
mock results and that the request was fully answered. These authored examples
are a development demonstration, not a representative benchmark or independent
human evaluation.

## Recorded Mac results — 17 October 2026

All 24 requests were run in each arm: **72 trials**, with no candidate removed.

| Approach | Exact calls EN | Exact calls IT | Factually successful tasks | Strict task success | Median request |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nesso3, all 12 tools | 6/12 | 6/12 | 10/24 | 9/24 | 2.92 s |
| **Nev orders all 12 tools** | **12/12** | **11/12** | **22/24** | **19/24** | 4.16 s |
| Nev selects one tool | 9/12 | 10/12 | 18/24 | 15/24 | **1.88 s** |

In this domain, **ranking the full catalog has the best accuracy**. Exact calls
improve from 12/24 to 23/24. Nesso3 can recover a correct tool even when Nev's
first choice is wrong. Restricting the catalog to one tool is faster, but locks
in more routing mistakes. This differs from the previous domain's best tradeoff:
there is no demonstrated universally best strategy.

Factual success comes from assistant review of all 72 traces, accepting correct
dates written in words. Strict success also requires the explicitly requested
`YYYY-MM-DD` date format. This is not an independent human audit. The raw report
retains the mechanical answer-anchor scores separately; those scores miss some
errors and reject some semantically correct date renderings.

### Remaining failures and limits

- Ranking-only, Italian irrigation schedule: the correct call is followed by
  unrelated calls, and there is no final answer.
- Ranking-only, Italian fertilizer schedule: the correct tool and time are used,
  but the answer calls the operation irrigation. This fails factual review.
- Single-tool selection: Nev confuses English air humidity with soil moisture,
  both irrigation requests with crop lookup, English planting date with crop
  lookup, and Italian fertilizer scheduling with irrigation scheduling.
- Single-tool selection, Italian crop name: the answer contains the unsupported
  word “Basilar” beside “basilico.” English uses the Italian crop name in an
  otherwise English sentence; its factual answer is correct but fluency is imperfect.
- Correct dates are sometimes returned in words despite the format instruction.

These results establish a useful configuration-driven demonstration with a new
catalog. They do not establish broad domain generalization, production accuracy,
reliable unsupported-action handling, or safe equipment control. The chosen
registry order is seeded; additional tool orders and fresh requests remain to be
tested. Timing is one local measurement per case, not a controlled speed study.

## Bilingual example: soil pH

These examples are selected from the complete recorded candidate set after
review. The full report also retains cases where Nev makes the wrong choice.

**English request:** “Read the soil pH in bed B-73.”

- Nesso3 alone calls `get_ventilation_status(zone_id="B-73")` and says the pH
  measurement was not found.
- Nev selects `read_soil_ph`; Nesso3 generates
  `read_soil_ph(bed_id="B-73")`; the mock returns `soil_ph: 6.4`.
- Final combined answer: “The soil pH in bed B-73 is 6.4.”

**Richiesta italiana:** “Leggi il pH del terreno nell’aiuola B-73.”

- Nesso3 da solo chiama `read_soil_moisture(bed_id="B-73")` e risponde con
  l’umidità del terreno, **38%**, invece del pH.
- Nev seleziona `read_soil_ph`; Nesso3 costruisce la chiamata con `bed_id="B-73"`.
- Risposta combinata: “Il valore del pH del terreno nell’aiuola B-73 è 6.4.”

Run the Italian example alone, comparing all three approaches:

```bash
RUN="results/greenhouse-ph-it-$(date +%Y%m%d-%H%M%S)"
.venv/bin/python compare_routing.py --suite greenhouse_suite.json \
  --precision q8 --case read_soil_ph-it --output "$RUN.json"
cat "$RUN.txt"
```

## Evidence and source

- [New greenhouse suite](greenhouse_suite.json) and [generic runner](compare_routing.py).
- [Full result JSON](results/greenhouse-q8.json), including suite contents, model
  pins, source hashes, per-case reviews and all three arms.
- [All readable traces](results/greenhouse-q8.txt).
- [Single Italian pH rerun](results/greenhouse-ph-it-q8.json) and its
  [readable trace](results/greenhouse-ph-it-q8.txt).

Verification: the isolated Italian pH run reproduced the full run's tool order,
executed calls, final text and scores in all three arms. The original Italian
note example was rerun after adding `--suite` and also reproduced its previous
results ([regression record](results/greenhouse-default-regression.json)). Original backend, controller, model pins and fixtures remain unchanged.
