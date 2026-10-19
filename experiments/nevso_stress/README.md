# Stronger bilingual evaluation for Nev + Nesso3

**200 requests, 100 English + 100 Italian, three strategies and three seeded
starting tool-order draws: 1,800 trials.** The native-GPU run completed all 1,800 trials on
19 October 2026 in 47 minutes 20 seconds. **Read the [results and trace review](REVIEW.md)**:
Nev improves the authored tool-selection cases, but does not improve the
external BFCL subset. The clarification proxy overcounted successes; reviewed
clarification scores are provided separately.

The [frozen protocol](PROTOCOL.md) defines the data, comparison and scoring.
[suite.json](suite.json) contains the exact inputs and references, and
[FREEZE.json](FREEZE.json) pins the evaluation source files by SHA-256.

| Panel | Requests | Main question |
| --- | ---: | --- |
| BFCL-derived tool calls | 60 | Does tool selection transfer to external API catalogs? |
| Confusable functions | 40 | Does the model distinguish nearby operations and negation? |
| Missing arguments | 30 | Does it ask for the required information? |
| Unsupported actions / direct answers | 30 | Does it avoid unnecessary calls? |
| Dependent calls | 20 | Can it use an ID returned by the first call? |
| Missing records / date formatting | 20 | Does it acknowledge tool errors and follow output format? |

Workflow domains: libraries, parcels, museums, bicycles and laboratory records.
All are local simulations. External BFCL cases are call-generation checks only;
no API is executed. [Training overlap is possible](TRAINING_EXPOSURE.md), and the
Italian BFCL requests are translations with English API descriptions.

The existing strategies are preserved: Nesso3 alone, Nev ranking the full catalog,
and Nev selecting one initial tool. Selecting one tool limits dependent
workflows; that category will be reported separately. Three seeded order draws
can repeat a permutation for very small external catalogs (some have two tools).

## Run

Use the existing [GPU environment](../../docs/nevso/GPU_GUIDE.md) from the checkout
root, then:

```bash
python -m unittest discover -s experiments/nevso_stress -p test_eval.py -v
python experiments/nevso_stress/run_eval.py --engine cuda \
  --output results/nevso-stress-a100
python experiments/nevso_stress/analyze.py results/nevso-stress-a100
```

For Mac Q8 after `./experiments/cpu_gguf/setup.sh --model both --precision q8`:

```bash
experiments/cpu_gguf/.venv/bin/python experiments/nevso_stress/run_eval.py \
  --engine gguf --output results/nevso-stress-q8
experiments/cpu_gguf/.venv/bin/python experiments/nevso_stress/analyze.py \
  results/nevso-stress-q8
```

Use a new output directory, or add `--resume` to continue an interrupted matching
run. `rows.jsonl` and readable `traces.txt` are saved after every trial.
`analyze.py` writes `RESULTS.md` and `analysis.json`, including results by language,
per-order stability, paired differences and a sensitivity view excluding one
contradictory source prompt. Its pre-run source hash is in
[ANALYSIS_FREEZE.json](ANALYSIS_FREEZE.json).

## Validation and interpretation

Six evaluation-contract tests pass locally and on the A100. The separate
[12-trial pilot](evidence/pilot/metadata.json) completed; it uses old greenhouse
and synthetic arithmetic examples and is not part of the new 200 requests.

Full-run workflow completion scores are **automatic proxies**. The missing-argument
category has a separate exhaustive assistant trace review in [REVIEW.md](REVIEW.md);
other categories have only sample review. Correct tool names, correct arguments, controller blocks, final-answer
assertions and strict output formatting must be distinguished. We do not combine
the external call-only score and workflow completion into one headline accuracy.

The run uses the previously pinned public models, with no retraining or
output-driven prompt changes. GPU precision is Nesso3 BF16 + Nev FP32; CPU uses
Q8 GGUF. Report them separately. See the protocol for provenance, constraints
and exact scoring rules.
