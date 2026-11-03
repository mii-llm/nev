# Nevso CPU on Linux — 3 November 2026

The [quick start](QUICKSTART.md) was exercised in a new isolated Python
environment on a **Seeweb Ubuntu 22.04.4 x86_64 host**, using an Intel Xeon
(Icelake), Python 3.12, Q8 models and **four CPU threads**. The host has an NVIDIA
GPU, but the GGUF worker was built with CUDA/Metal disabled and **PyTorch was
not installed** in this environment. Existing model-serving environments were
left unchanged. This is a shared virtual host, not an isolated latency test.

Python 3.12 and the C++ compiler were already installed. The quick start's apt
prerequisite command targets Ubuntu 24.04; it was not executed on this 22.04
host. On older distributions, provide a supported Python separately.

## Installation and smoke check

The public Q8 artifacts were downloaded without login and verified against
their pinned SHA-256 hashes. llama.cpp was built from revision
`37d6d653e49aa73c947cc9631a5d499869a21cca`.

```bash
./experiments/cpu_gguf/setup.sh \
  --python python3.12 --gguf-only --model both --precision q8
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/test_smoke.py \
  --precision q8 --output results/smoke.json
```

**Passed:** both English and Italian requested sensor `S-6K3`, Nev chose
`read_sensor`, the controller executed the expected call, and Nesso3 answered
**18.2°C**. The standalone Italian refund-routing check also passed. This is a
selected installation check, not evidence of general refund-policy reasoning.

The first inference attempt exposed a missing `Jinja2` dependency in the new
inference-only list. It was added explicitly, setup was rerun successfully, and
the smoke check and comparisons below then completed. The original failed log
is retained on the test host; no prompts or model weights were changed to pass.

## Two launch examples, all three approaches

Both use the existing greenhouse suite and unchanged controller. Each request
was run once per approach. Final answers were read alongside the calls; these
six trials are not a new independent benchmark or the full 24-request suite.

| Request | Nesso3 alone | Nev ranks + Nesso3 | Nev selects + Nesso3 |
| --- | --- | --- | --- |
| IT: soil pH in bed B-73 | Wrong moisture tool; reports pH **38** | Correct pH tool and answer **6.4** | Correct pH tool and answer **6.4** |
| EN: water remaining in tank W-26 | Wrong tool; reports “not found” | Correct tank tool and answer **81%** | Correct tank tool and answer **81%** |

Measured warm request times, excluding loading/warmup:

| Request | Nesso3 alone | Nev ranks + Nesso3 | Nev selects + Nesso3 |
| --- | ---: | ---: | ---: |
| Italian pH | 8.16 s | 11.42 s | 5.50 s |
| English tank level | 6.38 s | 9.35 s | 4.62 s |

These are individual observations, not medians over repeated measurements or
a stable speed ranking. Do not transfer Mac timings to this Linux host. Selection
exposes one schema; ranking retains all tools. Both models remain resident in
every approach. All tools are deterministic read-only mocks.

## Saved evidence

- [Environment, package versions, model pins and source hashes](evidence/linux-cpu-20261103/environment.json).
- [Bilingual smoke result and traces](evidence/linux-cpu-20261103/smoke.json).
- Italian pH: [JSON](evidence/linux-cpu-20261103/ph-it.json), [readable trace](evidence/linux-cpu-20261103/ph-it.txt).
- English tank: [JSON](evidence/linux-cpu-20261103/tank-en.json), [readable trace](evidence/linux-cpu-20261103/tank-en.txt).

Validated here: Linux x86_64 CPU installation, public downloads, offline model
inference and these documented examples. The historical Mac and Linux/CUDA
evaluations remain separate. Linux ARM, Windows and phone deployment have not
been tested in this validation.
