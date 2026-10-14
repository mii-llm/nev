---
language:
- en
- it
license: apache-2.0
base_model: giux78/nev
tags:
- gguf
- decision-model
- cpu
- llama.cpp
---
# Nev GGUF — standalone bilingual decisions

**Nev v3** is a small English/Italian decision model. Given state, instructions and candidate options, it returns categorical, boolean or ordinal decisions with probabilities. It does not generate conversational text. This private repository contains its decoder in **F16 and Q8_0**, plus the original FP32 pointer head, tokenizer and calibration configuration. **Nesso3 is not required.**

## Install and use Nev alone on CPU

The tested runtime is an Apple M3 Pro with four CPU threads, Metal/CUDA disabled. Requires Python 3.12 or 3.13, Git, a C/C++ compiler (Xcode command-line tools on Mac), and access to this repository and the private GitHub source.

```bash
git clone git@github.com:mii-llm/nev.git
cd nev/experiments/cpu_gguf
./setup.sh --model nev --precision f16
# Uses your saved HF login, or prompts for one.
.venv/bin/python decide.py
.venv/bin/python test_standalone.py --model nev --precision f16
```

The selected download contains only Nev artifacts. The shared Python environment includes conversion/reference dependencies, but inference uses a CPU llama.cpp worker and NumPy. No Nesso3 weights are downloaded or loaded.

The default example routes an Italian damaged-parcel/refund request to `refund`. To provide your own request, save this as `request.json`:

```json
{
  "state": "Il pacco è arrivato rotto e voglio un rimborso.",
  "questions": {
    "route": {
      "type": "choice",
      "instructions": "Seleziona il tipo di richiesta.",
      "criteria": {
        "refund": "Rimborso o merce danneggiata",
        "account": "Accesso all'account",
        "info": "Informazioni sui prodotti"
      }
    }
  }
}
```

```bash
.venv/bin/python decide.py --request request.json
# Smaller/faster alternative:
./setup.sh --model nev --precision q8
.venv/bin/python decide.py --precision q8 --request request.json
```

The output contains `answers.route.choice`, `probabilities`, token usage and latency. You can supply English state/instructions/criteria in the same format. A high probability is a score over the supplied alternatives, not a calibrated guarantee of correctness.

Python, from the same experiment folder:

```python
import os
os.environ["USE_TORCH"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
from cpu_backend import NevGGUF

model = NevGGUF(precision="f16", threads=4)
try:
    result = model.evaluate(
        state="My parcel arrived broken. I want a refund.",
        questions={"route": {
            "type": "choice",
            "instructions": "Select the appropriate department.",
            "criteria": {"refund": "Damaged goods and refunds",
                         "account": "Account access",
                         "info": "Product information"}
        }},
    )
    print(result["answers"])
finally:
    model.close()
```

## Why Nev needs an adapter

**This is a decision backbone GGUF, not a standalone chat model.** A generic chat application loading the GGUF alone will not reproduce Nev decisions. The supplied adapter reads final-normalized hidden states at option/readout positions, applies the original FP32 pointer head and calibration temperature, and renders each question as an isolated causal row. Keep `models/nev/v3/config.json`, `decision_head.safetensors` and `tokenizer/` together. No labels are generated as text.

## Conversion results

On 20 diagnostic requests containing 24 questions, **F16 preserved 24/24 decisions** relative to original FP32 CPU inference; maximum probability difference was **0.00541**. **Q8 preserved 23/24**, with maximum difference **0.06086**. The changed case was an Italian dependent notes request. Q8 probabilities have not been recalibrated. F16 is the default for closer fidelity, not bit-identical FP32 arithmetic. This small panel does not measure broad task accuracy; the original Nev release documents wider evaluations and limitations.

One F16 file is approximately **843 MiB**; Q8 approximately **451 MiB**. These are file sizes, not RAM requirements. CPU Mac inference is tested; mobile deployment is not validated.

## Files and provenance

- `gguf/nev-v3-f16.gguf`, `gguf/nev-v3-q8.gguf`: decision decoder only.
- `models/nev/v3/`: original head, decision configuration and tokenizer.
- `ARTIFACTS.json`: exact inference-file sizes and SHA-256 hashes.
- `PROVENANCE.json`: source model and conversion revisions.

Source: `giux78/nev`, folder `v3/`, revision `c5c84121263b423f8846811a24790ab96e66cee3`. Conversion uses unmodified llama.cpp `37d6d653e49aa73c947cc9631a5d499869a21cca`, with a separate CPU bridge. No retraining or recalibration occurred during conversion. Apache-2.0; source notices included.

For the optional **Nesso3 + Nev agent on CPU**, see the [GitHub combination guide](https://github.com/mii-llm/nev/tree/main/experiments/cpu_gguf). Nesso3's independent generative GGUF release is [giux78/nesso3-0.4B-agentic-gguf](https://huggingface.co/giux78/nesso3-0.4B-agentic-gguf).
