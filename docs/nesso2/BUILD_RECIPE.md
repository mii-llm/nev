# Building and auditing the Nesso2 decision experiment

This is the working build record for a future release, not a claim that the
experimental checkpoint is ready for deployment. Read [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)
for the complete result history and limitations. No upload step is included.

## Base conversion

The model uses the Kev Llama-compatible runtime and the pinned Nesso2 parent
revision in `recipes/nesso2-practical-v2.json`. The base is a gold-supervised
LoRA r=16, alpha=32, dropout=.05 plus a 256-dimensional pointer head. Target
modules: q/k/v/o projections and gate/up/down projections. The language-model
backbone is frozen during adapter training. The decision head chooses among
provided options; this is not an ordinary text-generation checkpoint.

The base recipe and complete dataset revisions/filters are archived as
`base-recipe.json` and `data-reviewed/manifest.json` in the evidence archive.
The full run uses LR 5e-5, AdamW, OneCycle, accumulation 8, 2 epochs, seed 0,
FP32 weights/BF16 autocast, and paired EN/IT updates. Review and resumed-training
proofs precede launch. Relevant commands and steps are in
`experiments/lumi/README.md`, `prepare_full.py`, `vllm_translate.py`,
`review_full.py`, `launch_full.py`, `train_full.py` and `finish_full.py`.
Retain the original 74k and 142k adapter/head checkpoints and their hashes.

The frozen Python source in the evidence archive is necessary because the
working checkout contains later changes. Git HEAD alone does not identify the
code used by the completed run. Package and hardware metadata from completed
evaluations are also archived; v2 writes an explicit `results/environment.json`.

## Practical v2 adaptation

Input recipe: `recipes/nesso2-practical-v2.json`. Four operational rule families
have bilingual, independently split instruction banks. Exact fact configurations
from v1 are excluded, including its inspected final test. Synthetic templates
and executable labels can be regenerated without calling an external teacher.
Original-data replay comes only from the reviewed base training split.

The current wrappers expect an existing base-run directory containing:

- `training-source/`: the frozen Kev runtime and training helpers;
- `data-reviewed/`: the reviewed base corpus and manifest;
- `decision-index-english-selection-v1/manifest.json` and `checkpoints/`: the
  verified 74k/142k reference hashes and checkpoint copies;
- `practical-pilot-v1/manifest.json`: the historical experiment identity.

These prerequisites describe this actual run. Before public release, package
reference-checkpoint metadata independently of benchmark-output directories so
users need not reproduce every exploratory evaluation to build the model.

On LUMI, stage the following into a new experiment directory's `source/`:

```text
practical_data.py
practical_data_v2.py
prepare_practical_v2.py
run_practical_v2.py
prepare_practical_v2.sbatch
practical_pilot_v2.sbatch
launch_practical_v2.py
nesso2-practical-v2.json
test_practical_v2.py
```

Then run the journaled launcher, with an absolute path under project scratch:

```sh
python3 source/launch_practical_v2.py --out "$EXPERIMENT_DIR"
```

`EXPERIMENT_DIR` is a user-provided experiment path. Set it explicitly before
running the command; this snippet assumes the current directory is that path.
The site wrappers still need the user's LUMI account, container/cache setup and
base-run path. They have been kept separate from the pure-Python generator and
recipe. No broader hardware portability claim has been verified yet.

CPU preparation verifies checkpoints, frozen code, pairing, split separation,
exact overlap, schema/context admission, recipe identity and counts, then writes
hash manifests. GPU execution starts only after successful preparation, verifies
those hashes, checks the trainable loader against inference, and checks actual
adapter/head weight changes. Optimizer/scheduler/RNG snapshots support restart.

## Reading outputs

- `jobs.json`: preparation and GPU IDs, avoiding ordinary duplicate submission.
- `manifest.json`, `data/manifest.json`: all identities and split checksums.
- `training/loss-history.jsonl`: 32-update mean losses and elapsed session time.
- `training/progress.json`: dev/guard history and stopping reason.
- `training/adapted-N/`: adapter/head snapshots, preserved separately from base.
- `results/selection.json`: choice frozen before calibration/final test.
- `results/calibration.json`: separate fitting and threshold-selection results.
- `results/*-test-logits.json`: per-case predictions for reproducible aggregation.
- `results/report.json`: written only when the full evaluation completes.

Compare exact case sets and metric denominators. Unsupported cases, selection
panels, final tests and source-domain tests must not be silently mixed. A better
aggregate score alone does not qualify a confidence policy. The candidate still
needs stable performance across languages/wording and verified export equivalence
before a release artifact and final model card are selected.

## Focused v3 follow-up

The predeclared follow-up is [FOCUSED_V3.md](FOCUSED_V3.md). It requires the completed
v2 run and its selected `training/adapted-256` checkpoint. Stage the v3 generator,
preparer, runner, finisher, launcher, two batch scripts, recipe and tests in a new
`source/` directory, together with their imported v1/v2 generator and Laya/comparison
helpers. `launch_focused_v3.py --out "$EXPERIMENT_DIR"` submits CPU preparation and
one dependent GPU pipeline. The launcher journals IDs; do not duplicate a running
job when checking status. The frozen source manifest identifies the actual scripts.

Completion requires `results/completion.json` and Slurm exit 0. The pipeline writes
a private FP32 export, final-test export comparison, Laya comparison and checkpoint
selection provenance. These artifacts inform release review; creation of an export
alone does not mean release approval or good confidence calibration. V3 evaluation
and the [broader regression audit](V3_REGRESSION.md) are complete. Preparation now
targets [two research variants](../../README.md), preserving
v2's stronger refund/Italian urgency results and v3's stronger routing results.
