# Nev — small models, bilingual decisions

**mii-llm’s first English–Italian decision-model family, built on a foundation pretrained from scratch.**

Turn language into structured choices with a ~0.4B backbone: route a support request, select a function, classify a topic, or recognize a banking intent. Supply your own options; Nev returns a typed decision and its probabilities. Every decision-training update balances **50% English and 50% Italian**.

**Public weights · Apache-2.0 · GPU and tested Mac CPU inference · Offline after download**

[Models on Hugging Face](https://huggingface.co/mii-llm/nev) · [Nev GGUF](https://huggingface.co/mii-llm/nev-gguf) · [Research guide](docs/RESEARCH.md)

## Get started

Use Python 3.12 and install the PyTorch build appropriate for your hardware.

```bash
git clone https://github.com/mii-llm/nev.git
cd nev
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime

# Try English and Italian decisions; public downloads need no HF login.
python examples/hf_decide.py --variant v3 --language both

# A four-question request with custom instructions and options.
python examples/hf_decide.py --variant v3 --request examples/request-complex-it.json
```

Use **v3** to explore routing and intent specialization; compare **v2** when refund rules or Italian urgency matter. A request contains `state` and `questions`. The native runtime supports categorical choices (`choice`), booleans (`noul`) and ordered levels (`score`).

### Run Nev on a Mac CPU

With Python 3.12–3.13 and Xcode command-line tools installed:

```bash
cd experiments/cpu_gguf
./setup.sh --model nev --precision q8
.venv/bin/python decide.py --precision q8
.venv/bin/python test_standalone.py --model nev --precision q8
```

Setup downloads Nev’s GGUF, tokenizer and original decision head. **Q8** is the smaller option; **F16** more closely matched the original decisions in our checks. Nev uses the supplied decision adapter; its GGUF alone is not a chat model.

## Results at a glance

Both released variants were evaluated on the same bilingual practical test. These scores are for the **merged exports** with BF16-autocast evaluation, not adapter-only results.

| Task | Examples per language | V2 English | V2 Italian | V3 English | V3 Italian |
| --- | ---: | ---: | ---: | ---: | ---: |
| Routing | 256 | 29.69% | 34.77% | **55.08%** | **46.88%** |
| Refund | 256 | **61.33%** | **52.73%** | 52.73% | 50.39% |
| Practical overall | 1,024 | 44.14% | 45.51% | **48.73%** | **46.58%** |

On a separate **synthetic 16-intent/routing panel**, the v3 export reached **54.69% English / 62.50% Italian** across 512 examples per language. V3’s routing gains come with tradeoffs in refund accuracy and Italian urgency. These limited, partly synthetic panels are not estimates of production accuracy; the research guide includes all tasks, comparisons and failures.

| Measured workload | Hardware | Warm median |
| --- | --- | ---: |
| Nev v3, one decision, FP32 | Shared NVIDIA A100 | **77.2 ms** |
| Nesso3 + Nev, complete Q8 agent request | Apple M3 Pro, four CPU threads | **1.89 s** |

These are different workloads from small diagnostic runs, excluding model loading. F16 preserved **24/24** tested Nev decisions versus FP32; Q8 preserved **23/24**. The Q8 Nev backbone is approximately **451 MiB**; both Q8 models together are approximately **902 MiB**. File size is not total memory use.

## Use Nev with Nesso3: a bilingual agent

Use **Nev to rank the available functions** and **Nesso3 to generate the call and answer**. This is the working preview of **Nevso**, our planned agent combining the two models. The greenhouse example supplies 12 tools through JSON; the same controller can use another tool catalog.

```text
Request → Nev ranks tools → Nesso3 generates the function and arguments
        → controller validates and runs a mock tool → Nesso3 answers
```

### Run it on an NVIDIA GPU

Complete **Get started** above, then run these commands from the **GitHub checkout directory `nev/`**, using a CUDA-enabled PyTorch 2.10 environment with at least **4 GiB free GPU memory**. The code comes from GitHub; the two public model downloads come from Hugging Face, with no login required.

```bash
python -m pip install -r experiments/abstract_agent/requirements.txt
python examples/hf_decide.py --variant v3 --download-only
python - <<'PYTHON'
from huggingface_hub import snapshot_download
snapshot_download(
    'mii-llm/nesso3-0.4B-agentic',
    revision='56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8',
    allow_patterns=['*.json', '*.safetensors', '*.jinja', 'tokenizer.model'],
    token=False,
)
PYTHON

# Italian: compare Nesso3 alone, Nev-ranked tools, and Nev-selected tools.
RUN="results/nevso-$(date +%Y%m%d-%H%M%S)"
python examples/nevso_demo.py --case read_soil_ph-it --output "$RUN-it.json"
cat "$RUN-it.txt"

# English: retrieve a water-tank reading.
python examples/nevso_demo.py --case read_water_tank_level-en --output "$RUN-en.json"
cat "$RUN-en.txt"
```

The runner creates the results directory. Each `.txt` file shows the request, Nev's selection, Nesso3's calls, mock observations and final answer; `.json` stores the full results. Omit `--case` to run all 24 English/Italian requests. Use a new output filename for each run.

### What the combination improves

These selected examples come from the recorded A100 run:

| Language | Request | Nesso3 alone | Nev-ranked + Nesso3 |
| --- | --- | --- | --- |
| IT | Leggi il pH del terreno nell’aiuola B-73. | Calls the moisture tool and answers **38%**, the wrong measurement. | Calls `read_soil_ph(bed_id="B-73")` and answers **6.4**. |
| EN | What percentage of water remains in tank W-26? | Chooses the wrong tool and reports the level was not found. | Calls `read_water_tank_level(tank_id="W-26")` and answers **81%**. |

Across the full **24-request demonstration** on a shared A100, using Nesso3 BF16 + Nev v3 FP32:

| Result | Nesso3 alone | Nev-ranked + Nesso3 |
| --- | ---: | ---: |
| Exact tool calls, English | 7/12 | **12/12** |
| Exact tool calls, Italian | 6/12 | **11/12** |
| Reviewed factual task success | 12/24 | **22/24** |
| Warm median request | 1.38 s | **1.44 s** |

These are authored examples with read-only mock tools. The factual scores come from assistant trace review; requiring the requested date format reduces combined task success to **19/24**. Wrong calls and incorrect final answers remain in the full results. Shared-GPU timings exclude loading and are illustrative.

The **[GPU guide](docs/nevso/GPU_GUIDE.md)** includes fresh-environment installation, all traces and failures. For the Mac Q8 version, use the **[CPU guide](experiments/cpu_gguf/README.md)**; after its setup, the same example accepts `--engine gguf --precision q8`.

## English and Italian in action

These selected examples passed on both variants; outputs shown are from v3. The application supplies the candidate labels.

| Use case | Language | Request | Nev decision |
| --- | --- | --- | --- |
| Support routing | EN | My monthly subscription was charged twice on the same day. I can see both completed payments on my statement and need this checked. | `billing` |
| Support routing | IT | Il mio abbonamento mensile è stato addebitato due volte nello stesso giorno. Vedo entrambi i pagamenti completati sull’estratto conto e vorrei una verifica. | `billing` |
| Function selection | EN | I need a copy of the invoice for order ORD-2048 to attach to my expense report. Please retrieve the document. | `get_invoice` |
| Function selection | IT | Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota spese. Recuperate il documento, per favore. | `get_invoice` |
| News classification | EN | Researchers demonstrated a new optical chip that processes signals using light. The laboratory prototype could reduce the energy required by future computers. | `science_technology` |
| News classification | IT | I ricercatori hanno presentato un nuovo chip ottico che elabora segnali usando la luce. Il prototipo di laboratorio potrebbe ridurre l’energia necessaria ai computer del futuro. | `science_technology` |
| Banking intent | EN | The ATM debited my account, but the machine did not dispense any cash. How do I report the failed withdrawal? | `cash_withdrawal` |
| Banking intent | IT | Il bancomat ha addebitato il mio conto, ma non ha erogato contanti. Come posso segnalare il prelievo non riuscito? | `cash_withdrawal` |

Nev selects the function; the application supplies arguments and controls execution. Full inputs and candidate labels are in `examples/reference_examples.json`. These are curated successes, not a representative accuracy sample.

## From foundation to decision model

```text
Zagreus foundation, pretrained from scratch
  → Nesso2 bilingual agentic model
  → Nev bilingual decision training
  → v2 Practical / v3 Routing
```

The foundation was pretrained on [Seeweb](https://seeweb.it/) infrastructure using 64 A100 GPUs, as documented in the pinned parent model card. Nev carries those learned weights through Nesso2 into a decision model built with Kev’s framework. The research guide documents the full lineage, training recipe and selection history.

“From scratch” describes the foundation’s learned weights. The project uses a Llama-style architecture and tokenizer, and builds on open-source training and decision-model software. Nesso3 is the optional generative partner; **Nesso2 remains Nev’s trained parent**.

## Go deeper

- **[Research and evaluation](docs/RESEARCH.md):** complete benchmarks, Laya comparisons, data, training, calibration, failure analysis and reproducibility.
- **[CPU guide](experiments/cpu_gguf/README.md):** standalone models, the combined agent, GGUF conversion, timings and executable tests.
- **[Inference guide](INFERENCE.md):** Python loading, request structure and runtime details.

Nev is a small research model with useful bilingual routing and classification behavior. Policy-sensitive decisions, large intent sets and unsupported actions remain challenging; probabilities are not correctness guarantees. Code and model releases use Apache-2.0; upstream notices are retained in `NOTICE`.
