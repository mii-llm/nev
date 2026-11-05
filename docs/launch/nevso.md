# We’re launching Nevso: a decision model + SLM agent for small devices

**Nev chooses. Nesso3 calls and answers. Your application controls execution.**

Today we’re launching the **Nevso developer preview**, an agent that pairs **Nev, a decision model**, with **Nesso3-0.4B-agentic, a small language model (SLM)**. Our aim is to make useful English and Italian tool workflows practical on devices with limited compute, with inference running locally.

The two models have distinct jobs. **Nev selects or ranks the available functions. Nesso3 generates the call and answers from the returned data.** A controller validates the call and dispatches it to your application’s executor. You supply the tools; the same workflow can serve different domains.

Each model has a roughly **0.4B backbone**. Their combined Q8 backbone files occupy approximately **902 MiB on disk**. We have tested CPU inference on **Linux and macOS**, and a native **Linux/NVIDIA GPU** path is also available. The results below describe these tested systems and provide a starting point for deployment on smaller devices.

The preview brings together public weights, open-source code and a Python API for registering your own functions. You can run it today from the Nev repository. After setup, inference works offline.

## Run it on Linux or macOS

Use Python 3.12–3.13, Git and a C/C++ compiler. On Ubuntu 24.04, install
`git build-essential python3.12 python3.12-venv`; on macOS, install Python and
Xcode command-line tools. The [quick start](https://github.com/mii-llm/nev/blob/main/docs/nevso/QUICKSTART.md)
includes exact prerequisites, an installation check and the full comparison:

```bash
git clone https://github.com/mii-llm/nev.git
cd nev
./experiments/cpu_gguf/setup.sh --python python3.12 --gguf-only --model both --precision q8

RUN="results/nevso-launch-$(date +%Y%m%d-%H%M%S)"

# Verify bilingual CPU inference before the comparison.
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/test_smoke.py \
  --precision q8 --output "$RUN-smoke.json"

# Italian: retrieve soil pH.
experiments/cpu_gguf/.venv/bin/python examples/nevso_demo.py \
  --engine gguf --precision q8 --case read_soil_ph-it \
  --output "$RUN-it.json"
cat "$RUN-it.txt"

# English: retrieve the water-tank level.
experiments/cpu_gguf/.venv/bin/python examples/nevso_demo.py \
  --engine gguf --precision q8 --case read_water_tank_level-en \
  --output "$RUN-en.json"
cat "$RUN-en.txt"
```

Each output compares Nesso3 alone, Nev-ranked tools and Nev-selected tools. You can read the request, calls, mock observations and final answer. Omit `--case` to run all 24 greenhouse requests. Supply `--suite /path/to/your-suite.json` to change the catalog and fixtures without rewriting the controller. NVIDIA users can follow the [Linux GPU guide](https://github.com/mii-llm/nev/blob/main/docs/nevso/GPU_GUIDE.md).

The CPU setup uses published GGUF files and skips training dependencies. No account, GPU or hosted inference service is needed for these examples. The performance numbers below belong to the named test hosts, not every Linux machine or Mac.

For your own application, the [Python API](https://github.com/mii-llm/nev/blob/main/docs/nevso/PYTHON_API.md)
accepts tool descriptions, JSON schemas and Python handlers. Create an `Agent`,
call `agent.run(request, language="it")`, and inspect the answer and tool trace.
The [runnable API example](https://github.com/mii-llm/nev/blob/main/examples/nevso_api.py)
shows this with three local functions in English and Italian.

## Why combine a decision model with an SLM?

Choosing a tool and generating its arguments are different tasks. Nevso gives each model a focused role: the decision model helps determine which function to use, then the SLM works with that choice.

In our notes, sensors and music demonstration, Nesso3 starts with a catalog of 12 tools. Adding Nev lets us select one relevant schema before asking Nesso3 to generate the call. A smaller prompt can mean less work and a better result, as this comparison illustrates.

Across **24 authored requests—12 English and 12 Italian—on an Apple M3 Pro**, the selected-tool workflow improved both quality and latency:

| Mac CPU, Q8, four threads | Nesso3 with all tools | Nev selects + Nesso3 |
| --- | ---: | ---: |
| Exact executed tool calls | 18/24 | **22/24** |
| Reviewed task success | 14/24 | **20/24** |
| Warm median full request | 2.57 s | **1.72 s** |
| Average Nesso3 prompt tokens per request | 1,546 | **316** |

That is approximately **33% lower median latency** and a **25 percentage-point increase in reviewed task success** in this demonstration. Timings include Nev’s work, generation and controller overhead, and exclude model loading. Both models remained resident in all comparison arms.

Here is one recorded example:

> **User:** Find the identifier of the note titled Aurora.
>
> **Nesso3 alone:** chooses a music lookup, receives “not found,” and incorrectly says the note cannot be found.
>
> **Nevso:** Nev selects `find_note`. Nesso3 generates `find_note(query="Aurora")`. The mock tool returns `N-7Q2`. Nesso3 answers: “The identifier of the note titled Aurora is N-7Q2.”

The Italian request—**“Trova l’identificativo della nota intitolata Aurora”**—also succeeds with the combined workflow.

## A new tool catalog, the same controller

We then supplied a greenhouse catalog through JSON: 12 functions for measurements, crop information and schedules. The models were not retrained, and the controller stayed the same.

For this catalog, **ranking all available tools with Nev** produced the strongest results. Nesso3 still sees every tool, with Nev determining their order.

| Greenhouse demonstration: 24 bilingual requests | Nesso3 alone | Nev ranks + Nesso3 |
| --- | ---: | ---: |
| Mac CPU Q8: exact calls | 12/24 | **23/24** |
| Mac CPU Q8: reviewed factual task success | 10/24 | **22/24** |
| A100 GPU: exact calls | 13/24 | **23/24** |
| A100 GPU: reviewed factual task success | 12/24 | **22/24** |

The combined exact-call score was **12/12 English and 11/12 Italian** on both backends. CPU and GPU were separate runs: the Mac used Q8; the shared A100 used Nesso3 BF16 and Nev FP32.

We also reproduced the two examples below on a **Linux x86_64 CPU** in a fresh
GGUF-only environment: both Nev-ranked and Nev-selected workflows returned the
correct values, while Nesso3 alone chose the wrong tools. The
[Linux validation record](https://github.com/mii-llm/nev/blob/main/docs/nevso/LINUX_VALIDATION.md)
includes the bilingual smoke test, all six comparison traces and host details.
This checks installation and example reproducibility, not the full benchmark.

Two selected GPU examples show what changes:

| Request | Nesso3 alone | Nev ranks + Nesso3 |
| --- | --- | --- |
| “Leggi il pH del terreno nell’aiuola B-73.” | Retrieves soil moisture and reports **38%**. | Retrieves soil pH and answers **6.4**. |
| “What percentage of water remains in tank W-26?” | Chooses the wrong tool and reports no level found. | Retrieves the tank reading and answers **81%**. |

The lesson for deployment is to test the strategy against your catalog. Selecting one tool reduced work in the first demonstration. Ranking preserved flexibility and delivered higher accuracy in the greenhouse demonstration; its CPU median was **4.16 seconds**, versus **2.92 seconds** for Nesso3 alone. The shared-GPU ranked workflow recorded a **1.44-second** median, versus **1.38 seconds** alone. These are separate measurements, not a universal speedup claim.

## More evidence for the routing benefit

A subsequent test covered confusing tool choices across five authored domains and three starting tool orders. Nev-selected + Nesso3 improved correct executed calls from **28.3% to 93.3% in English** and from **38.3% to 71.7% in Italian**.

Each language had 20 distinct requests repeated under three tool orders. These percentages measure tool names and arguments, not final-answer accuracy, and apply to that category. The [complete stress-test record](https://github.com/mii-llm/nev/blob/main/experiments/nevso_stress/README.md) covers the broader workflow evaluation.

## Local inference you can inspect

The GGUF CPU implementation uses llama.cpp with GPU acceleration disabled; the recorded Mac tests used four CPU threads. Linux CPU validation is recorded separately in the [installation guide](https://github.com/mii-llm/nev/blob/main/docs/nevso/QUICKSTART.md). Inference works offline after setup. The pair of Q8 backbone files, **totaling approximately 902 MiB**, represents disk storage, not a total RAM requirement: a separate CPU diagnostic sampled approximately **2.9 GiB of summed process RSS** for the combined runtime. That sampling can count shared pages more than once and is not a physical-footprint measurement. Phone deployment has not been tested.

The examples use read-only mock tools, so every call and returned value is reproducible. The controller checks schemas and argument provenance; it does not generate the final prose. For a real integration, the application supplies its tool executor and permissions.

The 24-request demonstrations are authored development examples, with factual success assessed by assistant trace review. Requiring the requested date formatting reduces greenhouse combined success to **19/24** on both backends. Their results support focused tool workflows; the full reports retain every trial and describe the wider evaluation scope.

**Build a local agent from two small models. Connect your tools. Inspect the trace.**

[Code and examples](https://github.com/mii-llm/nev) · [Nev GGUF](https://huggingface.co/mii-llm/nev-gguf) · [Nesso3 GGUF](https://huggingface.co/mii-llm/nesso3-0.4B-agentic-gguf) · [Full CPU comparison](https://github.com/mii-llm/nev/blob/main/experiments/cpu_gguf/ROUTING_COMPARISON.md)
