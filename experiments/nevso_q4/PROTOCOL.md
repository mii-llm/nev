# Nevso Q4_K_M pilot — 5 November 2026

Registered before predictions. Compare the existing Q8_0 backbones with new
Q4_K_M backbones quantized directly from the pinned public F16 GGUFs. No
requantization of Q8, importance-matrix tuning, prompt edits or training.
Q4_K_M is mixed quantization, not every tensor stored at exactly four bits.
Nev's FP32 head, tokenizers, temperatures and model revisions remain unchanged.
Published Q8 files are preserved. New files stay in an experiment directory.

CPU: existing Seeweb Linux x86_64 host, four threads, pinned llama.cpp revision
37d6d653e49aa73c947cc9631a5d499869a21cca. No GPU use. Preserve the worker's
4096-token context, FP32 KV caches, generation limit and controller. Download
F16 sources with the existing hash-verifying downloader. Record source and
output hashes, quantizer identity, environment and source-code hashes.

Use all 24 bilingual notes/sensors/music requests and all 24 bilingual
greenhouse requests. These are reused authored development examples, not an
independent holdout. **48 distinct requests, 24 EN + 24 IT; 96 precision trials.**
Choose the previously documented strategy for each catalog before this run:
selection for notes/sensors/music and ranking for greenhouse. Do not select a
new strategy after looking at Q4 outputs. Preserve seeded tool order and case
order from compare_routing.py. Expected calls and answer anchors are scored
after generation and never fed to the models.

Run sequentially in fresh processes, both backbones at the same precision:
notes Q8, notes Q4, greenhouse Q4, greenhouse Q8. This reverses precision order
between catalogs; it is not a repeated controlled speed benchmark. Run the same
warmup for both configurations. Capture all failures and complete traces.

Report separately per catalog and language: correct executed function +
arguments, Nev top-choice correctness/agreement, automatic answer-anchor proxy,
and reviewed factual completion. Review every final answer with tool outputs;
label this assistant review, not independent human evaluation. Preserve date
formatting separately. A successful call is not a verified final answer.

Memory: sample the Python process and its worker children every 50 ms, starting
before model loading. On Linux capture summed RSS, proportional set size (PSS),
and unique set size (USS), including both a full-run and inference-phase peak.
Record sampling failures. PSS allocates shared pages proportionally and is more
useful than summing RSS alone; neither measure includes the OS or establishes
a minimum device size or hard memory maximum. Timings include ranking,
generation and validation but exclude load and warmup. Keep memory sampling
identical across precisions and record that the CPU host is shared.

Do not update release downloads or advertise 4 GB device support from this
pilot. If Q4 loses accuracy, report the losses; hybrid precisions or another
quantization would require a separately labelled follow-up.
