# Building Nevso: a decision model + small language model for local AI agents

**Nev chooses. Nesso3 calls and answers. Your application controls execution.**

We built **Nevso** by combining **Nev, a decision model**, with **Nesso3-0.4B-agentic, a small language model (SLM)**. The workflow separates tool selection from call generation, with English and Italian inference running locally.

Nev comes from our own language-model family: **Zagreus, pretrained from scratch → Nesso2 → Nev**. We adapted Nesso2’s learned backbone for structured decisions using the Kev framework. Nesso3 is the generative partner in Nevso; it is not the parent checkpoint used to train Nev. “From scratch” refers to the foundation’s learned weights, with the architecture, tokenizer and software built on existing open-source work. The [training lineage](https://github.com/mii-llm/nev/blob/main/docs/RESEARCH.md#the-complete-lineage) documents those stages.

In a demonstration with **24 authored bilingual requests on an Apple M3 Pro CPU**, adding Nev to select a tool improved correct executed calls from **18/24 to 22/24** and reduced warm median request latency from **2.57 to 1.72 seconds**, approximately **33%**. Those results describe this specific demonstration; the examples and measurements below show where the approach helps and where its tradeoffs remain.

The two models have distinct jobs. **Nev selects or ranks the available functions. Nesso3 generates the call and answers from the returned data.** A controller validates the call and dispatches it to your application’s executor. You supply the tools; the same workflow can serve different domains.

Each model has a roughly **0.4B backbone**. Their combined Q8 backbone files occupy approximately **902 MiB on disk**. We have tested CPU inference on **Linux and macOS**, and a native **Linux/NVIDIA GPU** path is also available. The results below describe these tested systems and provide a starting point for deployment on smaller devices.

For these small, sequential Q8 workflows, **8 GB of total device RAM is a reasonable planning target**, allowing room for the operating system and application. Our recorded CPU diagnostic sampled a peak of approximately **2.9 GiB of summed process RSS** for the combined runtime. The 8 GB recommendation is an estimate based on that measurement, not a tested device requirement or a hard memory ceiling; a 4 GB device has not been validated. The memory measurement and its limits are explained below.

Beyond the small demonstrations, we completed a broader evaluation of **200 requests: 100 English and 100 Italian**, producing **1,800 trials** across three strategies and three starting tool orders. It tests both the routing benefit and the limits of the complete workflow.

The following sections cover installation, comparisons with Nesso3 alone, and the design choices behind the workflow. After setup, inference works offline.

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

## Separating tool selection from generation

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

## Beyond the demos: 200 requests, 1,800 trials

We tested the same model pair on **200 requests**, evenly split between English and Italian. Each request ran with Nesso3 alone, Nev ranking all tools, and Nev selecting one tool, under three seeded starting tool orders: **200 × 3 × 3 = 1,800 completed trials**. The orders repeat the same requests; they do not create 1,800 independent examples.

The test ran on an A100 with Nesso3 BF16 and Nev FP32. These results are separate from the Mac Q8 measurements. Model revisions, prompts, controller and scoring were frozen before the run, with no retraining or prompt changes during evaluation.

| Test area | Distinct requests, EN + IT | What it checks |
| --- | ---: | --- |
| BFCL-derived external API calls | 60 | Function names and arguments on adapted public API cases |
| Confusable functions | 40 | Nearby operations and negation across five authored domains |
| Missing arguments | 30 | Asking for the information needed to make a call |
| Unsupported actions and direct answers | 30 | Avoiding inappropriate or unnecessary tool use |
| Dependent calls | 20 | Using an identifier returned by an earlier tool |
| Missing records and date formatting | 20 | Handling tool errors and following output requirements |

The authored domains cover libraries, parcels, museums, bicycles and laboratory records. Their tools are local simulations. The BFCL-derived cases check call generation only; no external API is executed.

### Tool selection and final answers

For the confusable-function panel, there are **20 distinct requests per language**, each repeated under three orders: 60 trials per strategy and language.

| Metric | Language | Nesso3 alone | Nev ranks + Nesso3 | Nev selects + Nesso3 |
| --- | --- | ---: | ---: | ---: |
| Correct executed calls | EN | 17/60 (28.3%) | 40/60 (66.7%) | **56/60 (93.3%)** |
| Correct executed calls | IT | 23/60 (38.3%) | **44/60 (73.3%)** | 43/60 (71.7%) |
| Calls + answer checks, automatic proxy | EN | 7/60 (11.7%) | 28/60 (46.7%) | **41/60 (68.3%)** |
| Calls + answer checks, automatic proxy | IT | 15/60 (25.0%) | 26/60 (43.3%) | **29/60 (48.3%)** |

The executed-call metric requires the correct function **and arguments**. The answer checks additionally test expected content and completion; they are automatic proxies, not independently reviewed factual accuracy. The gap between the two metrics matters: selecting the right tool does not guarantee that Nesso3 correctly explains its result. Selection gives the strongest English call score here; ranking has the highest Italian call score.

### Transfer to external API catalogs

The adapted BFCL subset contains **30 requests per language**, repeated three times. Its metric checks schema-valid reference calls, without scoring final answers.

| Language | Nesso3 alone | Nev ranks + Nesso3 | Nev selects + Nesso3 |
| --- | ---: | ---: | ---: |
| English | **19/90 (21.1%)** | 15/90 (16.7%) | 16/90 (17.8%) |
| Italian | **21/90 (23.3%)** | 13/90 (14.4%) | 18/90 (20.0%) |

The routing gains on authored catalogs did not transfer to better scores on this external subset. The paired uncertainty intervals include zero, so this small sample also does not establish a general regression. This is a filtered, adapted BFCL subset, not an official BFCL score. Italian requests are translated while API descriptions remain English, and possible training overlap has not been resolved.

### Clarification and workflow limits

A review of all **270 missing-information trials** found that single-tool selection improved clean clarification from **0/45 to 16/45 in English** and **7/45 to 20/45 in Italian**. These are assistant-reviewed labels, not an independent human audit; the original automatic scorer overcounted successful clarification. The test stops at the clarification request and does not measure completion after a user replies.

Dependent workflows remain weak: Nesso3 alone and Nev ranking each passed **1/60** completion checks across both languages; initial single-tool selection passed **0/60** and cannot expose a different second function. All strategies also failed the strict date-format checks, even though some responses contained the correct date in words.

This larger evaluation supports Nevso as a tool-selection workflow for suitable catalogs. Argument generation, final answers and multi-step completion need their own checks. The [complete evaluation and trace review](https://github.com/mii-llm/nev/blob/main/experiments/nevso_stress/REVIEW.md) preserves every category, the scoring corrections and all 1,800 trials; the [plain-language results guide](https://github.com/mii-llm/nev/blob/main/experiments/nevso_stress/EXPLAINED.md) walks through successful and failed behavior.

## Local inference you can inspect

The GGUF CPU implementation uses llama.cpp with GPU acceleration disabled; the recorded Mac tests used four CPU threads. Linux CPU validation is recorded separately in the [installation guide](https://github.com/mii-llm/nev/blob/main/docs/nevso/QUICKSTART.md). Inference works offline after setup. The pair of Q8 backbone files, **totaling approximately 902 MiB**, represents disk storage, not a total RAM requirement: a separate CPU diagnostic sampled approximately **2.9 GiB of summed process RSS** for the combined runtime. That sampling can count shared pages more than once and is not a physical-footprint measurement. Phone deployment has not been tested.

The examples use read-only mock tools, so every call and returned value is reproducible. The controller checks schemas and argument provenance; it does not generate the final prose. For a real integration, the application supplies its tool executor and permissions.

The 24-request demonstrations are authored development examples, with factual success assessed by assistant trace review. Requiring the requested date formatting reduces greenhouse combined success to **19/24** on both backends. Their results support focused tool workflows; the full reports retain every trial and describe the wider evaluation scope.

Nevso is available as a **developer preview** in the Nev repository, with public model weights, open-source code, recorded evaluations and a Python API for registering your own functions. The examples provide a starting point for testing this approach with your own tool catalog.

[Code and examples](https://github.com/mii-llm/nev) · [Nev GGUF](https://huggingface.co/mii-llm/nev-gguf) · [Nesso3 GGUF](https://huggingface.co/mii-llm/nesso3-0.4B-agentic-gguf) · [Full CPU comparison](https://github.com/mii-llm/nev/blob/main/experiments/cpu_gguf/ROUTING_COMPARISON.md)
