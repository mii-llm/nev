---
language:
- en
- it
license: apache-2.0
base_model: mii-llm/nesso3-0.4B-agentic
pipeline_tag: text-generation
tags:
- gguf
- llama.cpp
- function-calling
- cpu
---
# Nesso3-0.4B-agentic — GGUF

**Nesso3-0.4B-agentic** is a small generative language model with English/Italian text and tool-call generation. This public repository provides **F16 and Q8_0 GGUF** versions of the original [Nesso3 model](https://huggingface.co/mii-llm/nesso3-0.4B-agentic). It can run independently: **Nev is not required**.

## Install and run Nesso3 alone on CPU

The verified path uses the original tokenizer/chat template and a pinned llama.cpp CPU worker. Requires Python 3.12 or 3.13, Git, a C/C++ compiler (Xcode command-line tools on Mac), and network access to Hugging Face and GitHub.

```bash
git clone https://github.com/mii-llm/nev.git
cd nev/experiments/cpu_gguf
./setup.sh --model nesso3 --precision q8
# Public download; no Hugging Face login is required.
.venv/bin/python generate.py --precision q8 --language both
.venv/bin/python test_standalone.py --model nesso3 --precision q8
```

Only Nesso3 artifacts are downloaded and only the Nesso3 model is loaded. The default example supplies bilingual sensor-tool schemas and requests a reading of `S-6K3`. It prints the generated tool-call proposal:

```text
English request: Read temperature sensor S-6K3.
Italian request: Leggi la temperatura del sensore S-6K3.

<tool_call>
{"name": "read_sensor", "arguments": {"sensor_id": "S-6K3"}}
</tool_call>
```

This command **generates text only**. It does not execute a sensor tool or claim to know its reading. Your application must parse and validate proposed calls, execute authorized tools, and return tool results before asking for a grounded answer.

For ordinary generation or custom conversation history:

```bash
.venv/bin/python generate.py --precision q8 --language en \
  --message 'Write a short greeting.'
.venv/bin/python generate.py --precision q8 --language it \
  --message 'Scrivi un breve saluto.'
# messages.json is an array of role/content objects using the native chat format:
.venv/bin/python generate.py --precision q8 --messages messages.json

# Closer numerical fidelity:
./setup.sh --model nesso3 --precision f16
.venv/bin/python generate.py --precision f16 --language both
```

`--output results/my-generation.json` saves a new trace and refuses to overwrite an existing file. The runner uses greedy decoding, the saved chat template, exactly one leading BOS, a 4096-token context and up to 192 generated tokens. Inference is offline after download, on four CPU threads by default, with no Metal/CUDA offload. The Python environment includes reference/conversion dependencies; the GGUF inference path itself uses llama.cpp.

Nesso3 uses the ordinary generative Llama architecture. The tested command above preserves its prompting/tokenization contract; compatibility with every third-party GGUF chat UI has not been tested.

## Conversion results and limitations

On eight short bilingual first-generation probes, GGUF tokenization matched the original HF tokenizer exactly. **F16 matched 8/8 reference token sequences**; **Q8 matched 7/8**. The differing Q8 case and its reference both proposed an invalid extra tool call. This is a small numerical diagnostic, not a broad function-calling success rate.

On the tested M3 Pro, short-probe decoding excluding prompt processing was approximately **89 tokens/s F16** and **129 tokens/s Q8**. These short runs are not throughput guarantees. One F16 file is about **843 MiB**, Q8 about **451 MiB**; memory use includes additional runtime buffers. Phones have not been validated.

The model can choose wrong arguments, add unwanted calls, misstate units or tool facts, and mishandle unsupported actions. Those weaknesses also appear before conversion. Treat generated calls as proposals to validate. Combining it with Nev does not by itself make it a reliable general autonomous agent.

## Files and provenance

- `gguf/nesso3-f16.gguf`, `gguf/nesso3-q8.gguf`: complete generative model.
- `models/nesso3/`: original tokenizer, chat template and configurations.
- `ARTIFACTS.json`: exact inference-file sizes and SHA-256 hashes.
- `PROVENANCE.json`: pinned source and conversion metadata.

Source: `mii-llm/nesso3-0.4B-agentic` at `56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`. Conversion uses unmodified llama.cpp `37d6d653e49aa73c947cc9631a5d499869a21cca`. No retraining during conversion. Apache-2.0; source notices included.

The optional **Nesso3 + Nev CPU agent** is documented in the [GitHub combination guide](https://github.com/mii-llm/nev/tree/main/experiments/cpu_gguf), including runnable bilingual examples, timings, raw traces and known failures. The independent decision model is [mii-llm/nev-gguf](https://huggingface.co/mii-llm/nev-gguf).
