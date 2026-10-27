# Kev 0.8B versus released Nev and the workflow candidate

Registered before benchmark predictions, 26 October 2026. No training.

Main models: `jaredpalmer/kev-0.8b` at resolved Hub commit
`bf75a6a8848ea6960ff2ed108d9ed44c2941174f`, Nev v2 and v3 at
`c5c84121263b423f8846811a24790ab96e66cee3`. Kev official runtime commit
`2074cc44256200bb37540103fa4572901faa10f3`; base Qwen3.5-0.8B-Base
`dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`. The model card gives an earlier
release revision; this run pins the current linked repository and hashes its
actual checkpoint files. Never substitute a model-card score for this run.

Use the entire saved GLiClass-comparison suite: 2,641 requests / 4,055 fields:
15 English tasks × 100, 508 API-Bank requests in each of two formats, 25 Home
Appliance cases, and 50 paired English/Italian MASSIVE intents. Preserve every
option, instruction, ID, order and expected label. API formats remain separate.
Add the 1,280 previously used new-domain workflow decisions (640 per language).
These are previously inspected diagnostics, not fresh holdouts or a full official
Decision Index submission. Italian is outside Kev's declared English scope.

Main models each score all 3,921 requests. The earlier gold-only Nev workflow
checkpoint (`gliclass-distillation-20261024/arms/gold/checkpoint-2000.pt`)
scores the 1,280 workflow decisions only. It is experimental and failed retention
checks; not a released model or proposed replacement. The failed retention
candidate is excluded prospectively. No best-checkpoint selection on these tests.

All use native renderers and FP32 weights/computation without autocast or TF32.
Kev uses its official LocalPredictor and shipped temperature; Nev uses frozen
DecisionModel cached inference and shipped temperature. Temperatures do not
change choice argmax; do not rank calibration across different calibration data.
Kev uses its supported Torch 2.8 environment; Nev retains its supported Torch
2.10 environment. Record package/kernel environments. Matched admission of
8,192 tokens for the state and each complete question row; no truncation. This
is a comparison setting, not Kev's maximum supported context or a Nev default
change. Tokenizers differ, so report full support and complete common case groups.
Both processes use a 32 GiB allocator cap on the shared A100. Report OOM and
admission failures, never count them as correct or silently drop them.

Native Decision Index metrics separately by task, with per-field accuracy and
coverage in JSON. Sarcasm uses positive-class F1, SATA/Home Appliance whole-case
accuracy, classification macro-F1 plus accuracy. Do not average unrelated metrics.
Workflow results measure single actions; do not call them end-to-end success.
MASSIVE remains paired and English/Italian separated. No timing ranking: different
native architectures/runtimes on a shared GPU, reference evaluation paths.

Synthetic smoke tests check probability keys, finite normalized distributions,
question isolation, experimental checkpoint loading and label-invariant inference
before evaluation. Hash inputs, source, model files and environment before reads.
Outputs are append-only and resumable; report all successful/unsupported rows.
Public model artifacts and existing environments are not modified.
