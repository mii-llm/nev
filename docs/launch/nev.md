# Meet Nev: small model, fast decisions, two languages

**A ~0.4B decision backbone. A ~451 MiB Q8 file. English and Italian at the core.**

Today we’re introducing **Nev**, mii-llm’s first bilingual decision-model family, built on a foundation pretrained from scratch. Nev turns a request into a structured choice: the right support queue, a function to call, a news category, or a banking intent.

You provide the options. Nev scores them and returns a typed decision with probabilities. That makes it a compact component for applications where the next step is a choice: route this message, select this function, classify this event.

Nev is available with public weights, an Apache-2.0 release, a Python runtime, and a tested Mac CPU path. It works offline after the initial downloads.

## Small enough to run locally. Quick enough to put in the request path.

Nev’s Q8 backbone is approximately **451 MiB on disk**. Its native GPU runtime recorded a **77.2 ms warm median** for a single decision on a shared NVIDIA A100, with a **98.5 ms p95** in that run.

Those timings cover 20 sequential, batch-one requests in FP32, including validation, tokenization and GPU synchronization. They exclude model loading, downloads and HTTP transport. The Q8 size and FP32 GPU timing describe different deployment configurations.

For local inference, we tested Nev on an **Apple M3 Pro using four CPU threads, with GPU acceleration disabled**. The supplied adapter combines the GGUF backbone with Nev’s original decision head and tokenizer. This is the path for developers exploring edge inference on local computers; the recorded hardware is a Mac, rather than a phone or microcontroller.

The appeal is practical: keep the model near the application and return a structured decision without generating a conversational response. The 451 MiB figure is the backbone file size; the head, tokenizer and runtime require additional disk space and memory.

## English and Italian are part of the training design

Every decision-training update balances **50% English and 50% Italian**. Both languages are part of the same release and the same developer workflow.

Here are selected passing examples from our published reference gallery:

| Task | English request | Italian request | Nev’s choice |
| --- | --- | --- | --- |
| Support routing | My monthly subscription was charged twice on the same day. | Il mio abbonamento mensile è stato addebitato due volte nello stesso giorno. | `billing` |
| Function selection | I need a copy of the invoice for order ORD-2048 to attach to my expense report. Please retrieve the document. | Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota spese. Recuperate il documento, per favore. | `get_invoice` |
| Banking intent | The ATM debited my account, but the machine did not dispense any cash. | Il bancomat ha addebitato il mio conto, ma non ha erogato contanti. | `cash_withdrawal` |

The support and banking messages are shortened here for readability; the complete inputs and candidate labels are in the repository. These are curated examples, rather than an accuracy estimate. In function selection, Nev chooses the function; your application or a generative partner supplies its arguments.

## A release focused on routing

Nev comes in two variants, **v2 Practical** and **v3 Routing**. V3 is the starting point for the routing examples in this launch.

On our bilingual practical routing panel, the released v3 export improved over the released v2 export:

| Routing accuracy | V2 | V3 |
| --- | ---: | ---: |
| English, 256 examples | 29.69% | **55.08%** |
| Italian, 256 examples | 34.77% | **46.88%** |

On a separate synthetic routing and 16-intent panel, v3 reached **54.69% English and 62.50% Italian**, with 512 examples per language. These are controlled development results using the merged exports with BF16-autocast evaluation; they demonstrate the routing focus of this release, rather than production accuracy across arbitrary tasks. The [research guide](https://github.com/mii-llm/nev/blob/main/docs/RESEARCH.md) includes the complete evaluations and methodology.

## A foundation built from scratch

Nev’s lineage starts with the Zagreus foundation, pretrained from scratch on [Seeweb](https://seeweb.it/) infrastructure. It continues through the bilingual Nesso2 agentic model into specialized decision training using the Kev framework.

“From scratch” describes the foundation’s learned weights. The project builds on a Llama-style architecture, an existing tokenizer and open-source software. We publish the recipe and experiment history alongside the model so developers can inspect how that foundation became a decision system.

## Try Nev on your Mac

With Python 3.12–3.13, Git and the Xcode command-line tools installed:

```bash
git clone https://github.com/mii-llm/nev.git
cd nev

# Create the CPU environment and download Nev's Q8 artifacts.
./experiments/cpu_gguf/setup.sh --model nev --precision q8

# Select a function from an Italian request.
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/decide.py \
  --precision q8 --request examples/request-function-it.json

# Run the English counterpart.
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/decide.py \
  --precision q8 --request examples/request-function-en.json
```

These commands use the supplied decision adapter; a generic chat loader alone does not reproduce Nev’s decision head. The native Python/GPU setup is documented in the repository.

**Start with a decision your application already needs to make. Supply the choices, run both languages, and measure the result on your own requests.**

[Get Nev and the code](https://github.com/mii-llm/nev) · [Native weights](https://huggingface.co/mii-llm/nev) · [CPU GGUF release](https://huggingface.co/mii-llm/nev-gguf)
