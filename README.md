# Nev — bilingual Nesso2 decision models

Two small English/Italian research variants built with Kev on `mii-llm/nesso2-0.4B-agentic`. Both return typed categorical, boolean and ordinal decisions over supplied criteria. They use the same frozen runtime and exactly 50% English / 50% Italian training weight.

**Model repository:** [giux78/nev](https://huggingface.co/giux78/nev) (private; account access required). **Code:** [mii-llm/nev](https://github.com/mii-llm/nev).

| Variant | Hugging Face folder | Measured relative strength | Tradeoff |
|---|---|---|---|
| [V2 Practical](models/v2/README.md) | `v2/` | Refund decisions and Italian urgency | Weaker routing than v3 |
| [V3 Routing](models/v3/README.md) | `v3/` | Routing, plus the new synthetic 16-intent experiment | Refund and Italian urgency regressions; weak 151-option intent classification |

These labels describe observed differences on research subsets, not guarantees for real traffic. The conversion keeps the parent backbone size and does not provide ordinary text generation.

## Start here

- [Install and run](INFERENCE.md), including the bilingual example.
- [Actual exported-model comparison](EXPORT_COMPARISON.md), with English/Italian and Laya comparisons.
- [Adapter comparison](COMPARISON.md), kept separate from export measurements.
- [Experiment narrative](EXPERIMENTS.md), including unsuccessful distillation, translation corrections, confidence failure and task regressions.
- [Detailed experiment log](docs/nesso2/EXPERIMENT_LOG.md) and [historical LUMI implementation record](experiments/lumi/README.md).
- [Build recipe](BUILD.md), [source/data recipes](recipes), and [frozen reference implementations](recipe-source).
- [Release limitations and remaining portability work](STATUS.md).

## Reproduce the authored datasets

```sh
python tools/generate_synthetic.py --variant v2 --out data-v2-synthetic
python tools/generate_synthetic.py --variant v3 --out data-v3-synthetic
```

These require only the standard library and verify the original held-out hashes. The generated training files exclude original-data replay; read BUILD.md before training.

## Attribution

Kev implementation and Nesso2 parent attribution are retained in [NOTICE](NOTICE) and [LICENSE](LICENSE). The exact parent revision declares Apache-2.0. Source datasets retain their own terms. Model weights live on Hugging Face; this repository carries source, recipes, result tables and provenance.
