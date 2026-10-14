---
language:
- en
- it
license: apache-2.0
base_model:
- giux78/nesso3-0.4B-agentic
- giux78/nev
tags:
- gguf
- llama.cpp
- function-calling
- decision-model
- cpu
---
# Nesso3 + Nev v3: CPU GGUF experiment

Private release of the **F16 and Q8_0 GGUFs** tested on an Apple M3 Pro (18 GiB RAM), four CPU threads, with Metal and CUDA disabled. Nesso3 generates tool calls and answers; Nev ranks the supplied next-step options. English and Italian examples use deterministic read-only mock tools.

## Install and use

The complete CPU bridge, pinned build recipe, runnable examples and test evidence are in [mii-llm/nev](https://github.com/mii-llm/nev/tree/main/experiments/cpu_gguf). Both repositories currently require authorized access.

```bash
git clone git@github.com:mii-llm/nev.git
cd nev/experiments/cpu_gguf
# Requires Python 3.12 or 3.13 and a C/C++ compiler (Xcode command-line tools on Mac).
./setup.sh --precision q8
# setup prompts for an HF login only if no saved login exists.
./run.sh --precision q8 --language both
.venv/bin/python decide.py --precision q8
.venv/bin/python test_smoke.py --precision q8 --output results/my-smoke.json
```

Use `./setup.sh --precision f16` and `./run.sh --language both` for the closer-to-reference F16 variant. Setup downloads the selected two GGUFs, original Nev FP32 head, tokenizers and configuration. Inference runs offline. The full dependency lock also includes PyTorch for optional conversion/reference checks; the GGUF inference path uses llama.cpp and NumPy.

**Nev is not a standalone chat GGUF.** Its files contain the decoder backbone only. The supplied adapter extracts final hidden states at the option/decision positions and applies `models/nev/v3/decision_head.safetensors` with the original renderer and calibration. Loading Nev's GGUF alone in a generic chat application does not reproduce Nev decisions. Nesso3 is the ordinary generative Llama model.

## Bilingual example

The following F16 smoke example passed in both languages; it was selected after the full comparison. Tools are mocks, not connected devices.

| Language | Request | Nev choice | Nesso3 tool call | Tool output | Final answer |
| --- | --- | --- | --- | --- | --- |
| English | Read temperature sensor S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `{"temperature":18.2,"unit":"C"}` | The temperature is 18.2°C. |
| Italian | Leggi la temperatura del sensore S-6K3. | `read_sensor` | `read_sensor(sensor_id="S-6K3")` | `{"temperature":18.2,"unit":"C"}` | La temperatura è 18.2°C. |

A working English two-step example:

```bash
./run.sh --precision q8 --language en \
  --message 'Find the temperature sensor in Studio, then read its temperature.'
```

The model searches for the sensor, receives ID `S-4J9`, then reads that returned ID and answers **21.5°C**. The corresponding Italian dependent case fails in the diagnostic set.

## Measured results and limitations

Measured on 2026-10-14, with resident warmed models, four threads, shared desktop activity; model loading excluded. Twelve fixed requests: six EN/six IT, ten supported and two unsupported actions. Small diagnostic sample, not a general agent benchmark.

| Backend | Median EN request | Median IT request | Combined median |
| --- | ---: | ---: | ---: |
| Original FP32 PyTorch CPU | 3.02 s | 3.58 s | 3.39 s |
| F16 GGUF + FP32 head | 3.73 s | 4.61 s | 4.24 s |
| Q8_0 GGUF + FP32 head | 1.84 s | 2.26 s | 1.89 s |

- **Nev F16: 24/24 decisions preserved** versus FP32 on 20 requests; maximum probability difference 0.00541.
- **Nev Q8: 23/24 decisions preserved**; maximum probability difference 0.06086. Quantized probabilities have not been recalibrated.
- Nesso3 F16 matched all eight first-generation reference token sequences; Q8 matched seven. Tokenization matched for both.
- Each backend executed the expected plan on 9/10 supported requests, but manual answer review gave **7/10 fully grounded answers**. An Italian conversion used the wrong unit, and an Italian media answer confused artist and title.
- Neither unsupported request received a clear correct refusal (**0/2** for each backend). This prototype is not a reliable general-purpose autonomous agent.
- F16 is the default for closer numerical fidelity, not bit-identical FP32 inference. Q8 offers smaller files and faster measured execution with a changed Nev decision in this sample.
- The two F16 files total about 1685 MiB; the two Q8 files about 902 MiB. These are file sizes, not RAM requirements. Sampled summed process RSS was about 2.9 GiB for GGUF and may double-count mapped/shared pages. Mobile deployment has not been tested.

The CPU bridge was rebuilt in the publication checkout, and the F16 and Q8 bilingual smoke tests passed using the existing Python environment. A fresh OS/environment installation was not tested.

All numerical evidence, human-readable traces, failure examples, verification scripts and reproduction commands are included in the GitHub CPU guide. The accuracy corrections distinguish exact tool execution and simple answer-anchor matching from semantic correctness.

## Artifacts and provenance

| Path | Purpose |
| --- | --- |
| `gguf/nesso3-f16.gguf`, `gguf/nesso3-q8.gguf` | Generative Nesso3 backbone |
| `gguf/nev-v3-f16.gguf`, `gguf/nev-v3-q8.gguf` | Nev v3 decision backbone |
| `models/nesso3/` | Original tokenizer, chat template and configuration |
| `models/nev/v3/` | Original FP32 decision head, tokenizer and decision configuration |
| `ARTIFACTS.json` | SHA-256 hashes and exact sizes of all inference artifacts |
| `PROVENANCE.json` | Original local measurement provenance; its source hashes describe the measured experiment, not subsequent publication edits |

Source models (pinned; no retraining during conversion):

- Nesso3: `giux78/nesso3-0.4B-agentic` at `56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`.
- Nev v3: `giux78/nev` at `c5c84121263b423f8846811a24790ab96e66cee3`, folder `v3/`.
- Controller and original runtime: `mii-llm/nev` at `28fda72603c8c7fe6729f3db2f856f8991fba38f`.
- Unmodified llama.cpp at `37d6d653e49aa73c947cc9631a5d499869a21cca`, external custom CPU bridge; 4096-token context, FP32 KV cache, no GPU offload.

Apache-2.0, consistent with both source model cards. Preserve source attribution when redistributing. Repository visibility is private.
