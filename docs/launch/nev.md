# Meet Nev: 438 million parameters, bilingual decisions, your own hardware

**Route requests. Select tools. Run locally, in English and Italian.**

Today we’re introducing **Nev**, mii-llm’s first English–Italian decision-model family. Nev turns a request into a structured choice: a support queue, a function to call, a news category or a banking intent.

You supply the state and the available options. Nev scores those options and returns a typed decision with probabilities, without generating a conversational response. With **438 million parameters**, public weights and a tested Mac CPU path, it gives developers a small, inspectable component to put inside their applications.

The release includes **Nev v2 Practical** and **Nev v3 Routing**, the code, the training recipe and the experiment history. The models and runtime are released under Apache-2.0. Inference works offline after setup.

## Routing gains you can reproduce

**Specializing a small model can make a substantial difference.** On our bilingual practical routing test, v3 improved accuracy by **25.4 percentage points in English** and **12.1 points in Italian** over v2.

| Routing accuracy, 256 examples per language | Nev v2 | Nev v3 |
| --- | ---: | ---: |
| English | 29.69% | **55.08%** |
| Italian | 34.77% | **46.88%** |

These are the same 256 examples per language, evaluated on merged exports with BF16 autocast. They demonstrate a gain on this controlled routing workload, rather than a production accuracy estimate.

**V3 Routing** adds focused routing and intent training and powers our launch reference examples and CPU GGUF release. **V2 Practical** stays available for broader decisions: it is stronger on compact API-Bank and the MASSIVE intent samples later in this post. Developers can compare both variants on their own requests. The release uses these established exports; newer workflow-training experiments remain research artifacts.

## A better tool workflow with Nev and Nesso3

Nev can also improve the work of a generative model. In our notes, sensors and music demonstration, **Nev chooses one function from a 12-tool catalog; Nesso3 generates its arguments and answers from the result**.

On an Apple M3 Pro with four CPU threads and Q8 models, across **24 authored requests, 12 English and 12 Italian**:

| Measured workflow | Nesso3 with all tools | Nev selects + Nesso3 |
| --- | ---: | ---: |
| Exact executed calls | 18/24 | **22/24** |
| Reviewed task success | 14/24 | **20/24** |
| Warm median full request | 2.57 s | **1.72 s** |

That is **25 percentage points more reviewed task success** and approximately **33% lower median latency** in this demonstration, including Nev’s own work. Selecting the schema also reduced Nesso3’s average prompt from 1,546 to 316 tokens per request.

The requests each need one supported operation with the required arguments present. Both models stayed resident; the controller and read-only mock tools were identical across arms. Task success comes from assistant trace review, not an independent audit. This supports a concrete design for local applications: let Nev choose, then let the generative model perform the focused task. The [runnable comparison](https://github.com/mii-llm/nev/blob/main/experiments/cpu_gguf/ROUTING_COMPARISON.md) preserves every request and trace. It is one building block of **Nevso**, our Nev–Nesso3 agent preview.

## Two languages by design

Every decision-training update balances **50% English and 50% Italian**. Both languages share the same model and developer interface.

That balance is a training commitment, not a promise of equal accuracy. On the paired MASSIVE sample reported below, Nev v2 scored 58% in English and 42% in Italian. The 50 source IDs are matched across languages, with native utterances and a shared English intent catalog. Italian capability is part of the release, and improving its consistency remains a clear research direction.

**Support routing, function selection, news topics and banking intents:** our published reference gallery contains eight selected English–Italian pairs that both released variants answered correctly in both languages. Here are four examples:

| Task | English request | Italian request | Nev’s choice |
| --- | --- | --- | --- |
| Support routing | My monthly subscription was charged twice on the same day. | Il mio abbonamento mensile è stato addebitato due volte nello stesso giorno. | `billing` |
| Function selection | I need a copy of the invoice for order ORD-2048 to attach to my expense report. Please retrieve the document. | Mi serve una copia della fattura dell’ordine ORD-2048 da allegare alla nota spese. Recuperate il documento, per favore. | `get_invoice` |
| News-topic classification | The retailer reported higher quarterly revenue but lower profit margins. | La catena di negozi ha registrato ricavi trimestrali più alti ma margini di profitto inferiori. | `business` |
| Banking intent | The ATM debited my account, but the machine did not dispense any cash. | Il bancomat ha addebitato il mio conto, ma non ha erogato contanti. | `cash_withdrawal` |

These are selected passing examples, not an accuracy estimate. Support, news and banking messages are shortened here; the repository preserves complete requests and candidate labels. Nev selects the function. Your application or a generative partner such as Nesso3 supplies its arguments; the application validates and executes the call.

## A small model with its own foundation

Nev’s story starts with **Zagreus**, our foundation pretrained from scratch on [Seeweb](https://seeweb.it/) infrastructure. That foundation became the bilingual Nesso2 agentic model, then the starting point for Nev’s specialized decision training.

[Jared Palmer’s Kev](https://github.com/jaredpalmer/kev) provided the inspiration and the open-source decision-model framework we built on. Its central idea is useful: when an application already knows the possible answers, a model can score those answers directly. We adapted that approach to our own small foundation and an English–Italian training recipe.

“From scratch” refers to the foundation’s learned weights. The project also builds on a Llama-style architecture, an existing tokenizer and open-source software. Both the lineage and the contributions we build on are documented in the repository.

## How close can a smaller model get?

We compared the released Nev variants with **Kev 0.8B** on the same saved benchmark inputs. The completed evaluation ran all three models afresh: **2,641 benchmark requests**, covering 15 English tasks, two API-Bank formats, device control and paired English–Italian intents, plus a separate bilingual workflow panel.

The loaded models contain **438.3 million parameters for Nev** and **752.9 million for Kev**. Nev uses approximately **42% fewer parameters**. That is a parameter comparison, not a measured RAM or speed advantage.

Here is a cross-section of the completed results. All values in this table are accuracy:

| Task | Cases | Kev 0.8B | Nev v2 | Nev v3 |
| --- | ---: | ---: | ---: | ---: |
| WinoGrande, English | 100 | 46% | 54% | **57%** |
| HellaSwag, English | 100 | 34% | 32% | **35%** |
| CLadder, English | 100 | 42% | 47% | **49%** |
| BANKING77, English | 100 | **76%** | 59% | 61% |
| ARC-Easy, English | 100 | **86%** | 55% | 57% |
| API-Bank, compact tool descriptions | 508 | **48.2%** | 41.5% | 39.0% |
| MASSIVE intents, English | 50 | **64%** | 58% | 50% |
| MASSIVE intents, Italian | 50 | **62%** | 42% | 38% |

Nev is competitive on selected tasks at a smaller size; Kev leads on several others. A one-case difference on HellaSwag is not evidence of a stable advantage. Input format matters too: with API-Bank’s original full schemas, Kev scored **43.7%**, Nev v2 **16.7%** and Nev v3 **6.1%**. The compact result describes a particular input format, not general function-calling reliability.

These are small, previously inspected diagnostic samples, not an official leaderboard or newly held-out test. All models used native FP32 inference, their supported runtimes, matched 8k state/row admission and no truncation. Every main model supported all 3,921 requests, including the separate workflow panel. API-Bank measures the next tool name, not argument generation or successful execution. The [complete comparison](https://github.com/mii-llm/nev/blob/main/experiments/kev_comparison/evidence/results/README.md) includes every task, native metrics and the experimental workflow candidate, which is separate from this release.

For us, the reason to release Nev is concrete: a small decision model built from our own foundation, useful behaviors developers can reproduce, and enough evidence to decide where it fits.

## A practical route to local inference

Nev v3’s **Q8 backbone occupies approximately 451 MiB on disk**. We tested the supplied GGUF adapter on an **Apple M3 Pro, using four CPU threads with GPU acceleration disabled**. The adapter also loads Nev’s original decision head and tokenizer; the backbone file size is not the full package size or RAM requirement. This establishes a Mac CPU path for local and edge experimentation. Phone deployment has not been tested.

On a shared NVIDIA A100, the native FP32 runtime recorded a **77.2 ms warm median** and **98.5 ms p95** for a single decision. This was a 20-request, sequential, batch-one measurement including validation, tokenization and synchronization, excluding model loading, downloads and HTTP transport. It is separate from the CPU Q8 configuration and the Kev accuracy comparison.

## Try Nev on your Mac

With Python 3.12–3.13, Git and the Xcode command-line tools installed:

```bash
git clone https://github.com/mii-llm/nev.git
cd nev

# Create the CPU environment and download Nev v3's Q8 artifacts.
./experiments/cpu_gguf/setup.sh --model nev --precision q8

# Select a function from an Italian request.
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/decide.py \
  --precision q8 --request examples/request-function-it.json

# Run the English counterpart.
experiments/cpu_gguf/.venv/bin/python experiments/cpu_gguf/decide.py \
  --precision q8 --request examples/request-function-en.json
```

These commands use the supplied decision adapter. The repository also includes native Python/GPU inference and examples combining Nev with Nesso3 in the Nevso agent workflow.

**Start with the choices your application already makes. Run Nev locally, test both languages, and choose the variant that works for your data.**

[Code, recipe and examples](https://github.com/mii-llm/nev) · [Native weights](https://huggingface.co/mii-llm/nev) · [CPU GGUF release](https://huggingface.co/mii-llm/nev-gguf)
