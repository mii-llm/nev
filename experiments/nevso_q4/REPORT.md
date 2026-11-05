# Nevso Q4 CPU results

5 November 2026. **Four-bit conversion works, but Q8 remains the recommended
precision for this workflow.** Pure Q4_0 nearly halves the GGUF storage while
losing substantial call and answer accuracy. It does not reduce measured
runtime memory in this configuration.

We evaluated Nev v3 + Nesso3 on **48 distinct reused requests: 24 English and
24 Italian**, at four precisions (192 trials). These are authored development
examples, not a new benchmark holdout. The two catalogs cover notes, sensors,
music and greenhouse tools. Results describe this small diagnostic sample.

## Storage, memory and quality

| Both backbones | Combined GGUF files | Peak process-tree PSS | Correct calls | Reviewed factual completion |
| --- | ---: | ---: | ---: | ---: |
| Released Q8_0 | ~902 MiB | 2.58 GiB | **44/48** | **40/48** |
| Q4_K_M with fallback | 682 MiB | **2.39 GiB** | 43/48 | 38/48 |
| Default Q4_0 | 602 MiB | 2.60 GiB | 33/48 | 22/48 |
| Pure Q4_0 | **485 MiB** | 2.62 GiB | 30/48 | 20/48 |

File sizes cover the two GGUFs; the unchanged external decision head and
tokenizer/runtime files are additional. PSS is the larger sampled peak across
the two catalogs, including loading, warmup and inference. It covers Python
and its worker processes, apportions shared pages, and excludes the operating
system. These figures establish neither a device RAM minimum nor a hard cap.
In particular, this experiment does **not** validate a 4 GB device claim.

Correct calls require the complete expected executed function/argument sequence.
Factual completion additionally requires a complete, factually correct final
answer. All 192 outputs were reviewed by the assistant against the traces;
this is not an independent human audit. Requiring the requested ISO date
format as well gives 37/48, 35/48, 21/48 and 16/48 respectively.

## English and Italian

Each language contains 24 requests across both catalogs.

| Precision | EN correct calls | IT correct calls | EN factual completion | IT factual completion |
| --- | ---: | ---: | ---: | ---: |
| Q8_0 | 24/24 | 20/24 | 22/24 | 18/24 |
| Q4_K_M | 24/24 | 19/24 | 22/24 | 16/24 |
| Default Q4_0 | 18/24 | 15/24 | 13/24 | 9/24 |
| Pure Q4_0 | 15/24 | 15/24 | 9/24 | 11/24 |

The aggregate hides catalog differences. Q4_K_M executes all 24 greenhouse
requests correctly, versus 23/24 for Q8, but drops from 21/24 to 19/24 in
notes/sensors/music. A correct execution also does not ensure correct prose:
its Italian fertilizer answer labels the returned time as irrigation.

Pure Q4_0 introduces more severe errors. For the English conversion of 20 °C
to Fahrenheit it executes no tool and answers `20 F = 20 * 2 = 40.0`.
For an Italian soil-pH request it returns the moisture value, 38, instead of
the pH, 6.4. Other cases execute the right call but return an incomplete answer
or hit the turn limit. The [paired traces](evidence/results/REVIEW_INPUT.md)
show every configuration, including successes.

Nev's initial top-choice counts remain relatively close: 41/48 for Q8,
42/48 for Q4_K_M, and 40/48 for either Q4_0 variant. That makes a future
**Nev Q4 + Nesso3 Q8** experiment worth considering. It has **not** been tested
here: both backbones changed together, so this study cannot isolate which
model caused each regression.

## Why three different Q4 variants?

All conversions start directly from the pinned public F16 GGUFs, without
requantizing Q8. The quantizer is llama.cpp revision
`37d6d653e49aa73c947cc9631a5d499869a21cca`; no importance matrix or calibration
data was used.

- **Q4_K_M:** the 960-wide layers trigger fallback for 192/290 tensors.
  The quantizer reports 6.39 bits per weight. Its approximately 7% PSS saving
  is real in this run, but describing this result as uniformly four-bit would
  be misleading.
- **Default Q4_0:** the large tied token embedding is automatically upgraded
  and falls back to Q8_0; the model averages 5.63 bits per weight.
- **Pure Q4_0:** `llama-quantize --pure` disables automatic upgrades. The
  reported average is 4.50 bits per weight, including scale overhead. The two
  files total exactly 508,584,256 bytes (485.02 MiB).

Normalization tensors and Nev's external decision head retain their existing
precision. The worker retains FP32 KV caches and a 4,096-token context. A
smaller weight file does not imply an equally smaller resident process: KV
caches, compute buffers, runtime allocations and memory mapping also matter.
We did not profile their individual contributions, so we do not attribute the
higher Q4_0 PSS to a specific cause.

## Test conditions and timing

Tests ran on the Seeweb Linux x86_64 host, with four CPU threads and GPU use
disabled. Each configuration used a fresh process with both models resident.
The tokenizer, prompts, generation settings, controller and mock tools stayed
unchanged. Nev selection was fixed for notes/sensors/music; Nev ranking was
fixed for greenhouse before evaluation.

Q8 and Q4_K_M warm medians were respectively 4.63/4.68 seconds for routing and
10.92/10.92 seconds for greenhouse. Pure Q4_0 medians were 3.27 and 7.85 seconds,
but its failed or shortened responses mean these are **not evidence of a
quality-preserving speedup**. This was one pass on a shared CPU host, not a
controlled latency benchmark.

Memory was sampled every 50 ms using Linux process-tree RSS/PSS/USS; all samples
succeeded. Full per-catalog memory figures, automatic answer-anchor proxies
and paired changes are in [automatic results](evidence/results/RESULTS.md).
Answer anchors can accept incorrect labels or reject correct dates written in
words; reviewed factual completion is deliberately separate.

## Reproduction and evidence

Use the [reproduction commands](README.md). The initial
[Q4_K_M protocol](PROTOCOL.md), [default Q4_0 follow-up](PROTOCOL_Q4_0.md) and
[pure Q4_0 follow-up](PROTOCOL_Q4_0_PURE.md) record the sequence. Follow-ups
were specified before their own predictions, after inspecting preceding
quantizer logs/results; they are not independent preregistered replications.
No prompts or cases were tuned between precisions.

- [All automatic metrics and source-linked runs](evidence/results/summary.json)
- [All outputs, calls and observations side by side](evidence/results/REVIEW_INPUT.md)
- [Per-case factual review, reasons and source hashes](evidence/answer_review.json)
- [Q4_K_M conversion](evidence/artifacts/quantization.json),
  [default Q4_0 conversion](evidence/artifacts/quantization-q4_0.json),
  [pure Q4_0 conversion](evidence/artifacts/quantization-q4_0_pure.json)
- [Environment](evidence/environment.txt) and [host](evidence/host.txt)

Raw JSON and readable traces for all eight runs are retained in
`evidence/results/`, with frozen source/artifact hashes in `evidence/FREEZE*.sha256`.
The generated weights remain in the Seeweb experiment directory
`/home/ecuser/nev-a100/nevso-q4-20261105/artifacts/gguf/`.
Published Hugging Face weights, download pins and the default Q8 API are unchanged.
