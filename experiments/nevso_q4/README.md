# Nevso 4-bit CPU experiment

**Completed:** pure Q4_0 reduced the two GGUF files to 485 MiB, but correct
calls fell from 44/48 to 30/48 and peak process-tree PSS rose from 2.58 to
2.62 GiB. Keep Q8 as the default. See the [full report](REPORT.md), including
the mixed-precision alternatives, English/Italian results and all traces.

This experiment compares the released Q8_0 pair with Q4_K_M, default Q4_0 and pure Q4_0, starting
from the pinned public F16 GGUFs. It keeps Nev's decision head in FP32 and uses
the existing CPU worker, tokenizer, prompts and controller. The public release
files and default API precision are unchanged.

Q4_K_M is mixed precision. In this model's 960-wide layers, the pinned quantizer
reports **192/290 tensors requiring fallback**, producing about **6.39 bits per
weight**, so it is not a close-to-four-bit result for this architecture. Default Q4_0 still keeps the large tied token embedding at Q8, giving 5.63
bits per weight. A separately registered `--pure` Q4_0 run disables those
automatic upgrades to test four-bit matrices (plus block-scale overhead).

The [original protocol](PROTOCOL.md), [Q4_0 follow-up](PROTOCOL_Q4_0.md) and
[pure Q4_0 follow-up](PROTOCOL_Q4_0_PURE.md)
specify the scope: 48 distinct requests (24 EN + 24 IT), two catalogs and fixed
strategies. Each precision runs all requests, for 192 trials in total. These
are reused authored examples, not a new holdout. Both backbones use the same
precision; this does not isolate the effect on Nev from the effect on Nesso3.

## Reproduce on a prepared Linux CPU host

Use the [CPU setup](../../docs/nevso/QUICKSTART.md) first. The experiment needs
additional disk space for the F16 source pair and quantized variants. From the
repository root, choose a new directory:

```bash
EXPERIMENT="$PWD/results/nevso-q4-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EXPERIMENT"
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/download_gguf.py \
  --model both --precision f16 --destination "$EXPERIMENT/artifacts"

# Quantize Q4_K_M; run fresh Q8 and Q4_K_M comparisons, in sequence.
sh experiments/nevso_q4/run_linux.sh "$PWD" "$EXPERIMENT"

# Quantize Q4_0; run the separately specified follow-up.
sh experiments/nevso_q4/run_q4_0_linux.sh "$PWD" "$EXPERIMENT"

# Also quantize the token embeddings at Q4_0, without automatic upgrades.
sh experiments/nevso_q4/run_q4_0_pure_linux.sh "$PWD" "$EXPERIMENT"

python3 experiments/nevso_q4/analyze.py "$EXPERIMENT/results"
cat "$EXPERIMENT/results/RESULTS.md"
```

The runners use Linux process-tree RSS/PSS/USS sampling, so this memory protocol
is Linux-specific. They do not use the host GPU. Each configuration runs in its
own process with four CPU threads and both models resident. Each output keeps
all calls, observations and final answers. Failed calls and incorrect final
prose remain in the reports.

`RESULTS.md` contains automatic call and answer-anchor counts. `REVIEW_INPUT.md`
groups every answer for manual inspection; the anchor metric is not factual
accuracy. Memory figures distinguish RSS, proportional sharing (PSS), and unique
pages (USS); none includes the OS or proves a minimum device RAM capacity.
Timings are illustrative shared-host measurements, not repeated controlled
speed benchmarks. Quantization manifests and SHA-256 freeze files record the
source and generated artifacts. No importance matrix or calibration data is used.
