# Meet Nevso: two small models, one local tool workflow

**Nev chooses. Nesso3 calls and answers. Your application controls execution.**

Today we’re introducing the **Nevso developer preview**: a runnable agent workflow combining **Nev** and **Nesso3-0.4B-agentic**. Each has a roughly 0.4B backbone. Together, their Q8 backbone files occupy approximately **902 MiB**, and the workflow already runs on a Mac CPU in English and Italian.

Nevso brings a focused division of work to local AI. Nev helps select the right function. Nesso3 generates its arguments and turns the returned data into an answer. A controller validates the call and dispatches it to the supplied executor.

The preview combines two existing public models and open-source code. You can run it today from the Nev repository, without a separate Nevso checkpoint or hosted inference service.

## A smaller prompt can produce a better result

In our notes, sensors and music demonstration, Nesso3 receives a catalog of 12 tools. Adding Nev lets us choose one relevant schema before asking Nesso3 to generate the call.

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

The Mac implementation uses four CPU threads with GPU acceleration disabled. Inference works offline after setup. The pair of Q8 backbone files, **totaling approximately 902 MiB**, represents disk storage, not a total RAM requirement: a separate CPU diagnostic sampled approximately **2.9 GiB of summed process RSS** for the combined runtime. That sampling can count shared pages more than once and is not a physical-footprint measurement. Phone deployment has not been tested.

The examples use read-only mock tools, so every call and returned value is reproducible. The controller checks schemas and argument provenance; it does not generate the final prose. For a real integration, the application supplies its tool executor and permissions.

The 24-request demonstrations are authored development examples, with factual success assessed by assistant trace review. Requiring the requested date formatting reduces greenhouse combined success to **19/24** on both backends. Their results support focused tool workflows; the full reports retain every trial and describe the wider evaluation scope.

## Run the bilingual preview

On a Mac with Python 3.12–3.13, Git and Xcode command-line tools:

```bash
git clone https://github.com/mii-llm/nev.git
cd nev
./experiments/cpu_gguf/setup.sh --model both --precision q8

RUN="results/nevso-launch-$(date +%Y%m%d-%H%M%S)"

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

Each output compares Nesso3 alone, Nev-ranked tools and Nev-selected tools. You can read the request, calls, mock observations and final answer. Omit `--case` to run all 24 greenhouse requests. NVIDIA users can follow the [GPU guide](https://github.com/mii-llm/nev/blob/main/docs/nevso/GPU_GUIDE.md).

**Download two small models. Run the comparison locally. Bring your own tool catalog.**

[Code and examples](https://github.com/mii-llm/nev) · [Nev GGUF](https://huggingface.co/mii-llm/nev-gguf) · [Nesso3 GGUF](https://huggingface.co/mii-llm/nesso3-0.4B-agentic-gguf) · [Full CPU comparison](https://github.com/mii-llm/nev/blob/main/experiments/cpu_gguf/ROUTING_COMPARISON.md)
