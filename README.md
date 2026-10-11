# Nev — from a language model trained from scratch to bilingual decisions

Nev is the decision-model stage of the **mii-llm Zagreus → Nesso2** lineage: a small language-model foundation trained from scratch, developed into an Italian/English agentic model, and then adapted to make structured decisions over options supplied by an application.

The project follows the whole path from that foundation to two released decision variants. It preserves **50% English / 50% Italian record and loss weight in every decision-training update**, uses the roughly 0.4B-parameter Nesso2 backbone, and builds on Kev's decision-model implementation. The objective is to understand how much useful decision behavior this small bilingual model can learn, how specialization changes its abilities, and where it still fails.

**Weights:** [giux78/nev on Hugging Face](https://huggingface.co/giux78/nev), with separate `v2/` and `v3/` folders. Both the model repository and this GitHub repository are currently private. This README contains the main project narrative, training recipe, results, limitations, and commands; a few detailed records are linked at the end.

| Released variant | Selected checkpoint | Observed strengths | Observed tradeoffs |
|---|---|---|---|
| **V2 Practical** | Original decision checkpoint 74k +256 adaptation updates | Better refund accuracy and Italian urgency than v3 on the reused practical test | Weaker routing |
| **V3 Routing** | Selected v2 +512 focused adaptation updates | Better routing; substantial gains on a new synthetic 16-intent/routing test | Refund and Italian urgency regressions; weak large-option intent classification |

These are measured differences on the described test sets. Both variants remain research models. The harder examples later in this README show that neither reliably follows all supplied policies, even when it assigns a high probability to its answer.

## 1. The complete lineage

```text
Zagreus-0.4B-ita — foundation pretrained from scratch
    │
    ├─ Knowledge continued pretraining
    ├─ Context extension to 32k tokens
    └─ Bilingual agentic supervised fine-tuning
          │
          ▼
Nesso2-0.4B-agentic — the pinned parent of Nev
          │
          ├─ Kev compatibility and decision-head integration
          ├─ Translation, teacher pilots and data review
          └─ Full balanced bilingual decision training: 178,300 updates
                │
                ├─ 142k: original development-selected control
                └─ 74k: starting point for practical adaptations
                      │
                      ├─ Practical v1: exploratory experiment
                      └─ Practical v2: selected at +256 → released v2
                            │
                            └─ Focused v3: selected at +512 → released v3
```

The [pinned Nesso2 model card](https://huggingface.co/mii-llm/nesso2-0.4B-agentic/blob/86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041/README.md) reports the earlier stages: Zagreus was pretrained from scratch on about one trillion tokens, approximately 400B English, 400B Italian and 200B code. Sources included FineWeb, Italian FineWeb-2, Italian FinePDFs and StarCoder Data. That work used Nanotron on 64 A100 GPUs at Seeweb. Knowledge continued pretraining used Italian/English Wikipedia and augmented question-answer data, followed by 32,768-token context adaptation and bilingual agentic SFT with TRL/FSDP.

The foundation uses a Llama-style architecture and Llama-3 tokenizer. **“From scratch” describes the foundation's learned weights.** Nev builds on those weights through Nesso2, with Kev supplying the decision-model framework. Earlier-stage details above come from the parent card; the experiment records in this repository document the subsequent decision-model work on LUMI.

The exact Nesso2 parent is:

```text
mii-llm/nesso2-0.4B-agentic
86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041
```

The distinction between stages matters. The foundation's English/Italian/code pretraining mixture is different from Nev's exact 50/50 English/Italian decision-training balance. Nesso2's advertised 32k context also does not override the smaller input limits enforced by the decision runtime.

## 2. What a decision model does

An application supplies a state, one or more questions, instructions, and the allowed answers. Nev returns a typed decision and a probability distribution over those answers.

| Question type | Meaning | Output |
|---|---|---|
| `choice` | Choose among named runtime options | Selected option ID and its distribution |
| `noul` | Make a boolean decision | `decision`, `p_true`, and false/true probabilities |
| `score` | Choose an ordered level | Selected level, expected level, and level probabilities |

For example, one support request can ask four questions together: which department should handle it, whether the stated refund policy applies, how urgent it is, and whether it should be escalated. The application supplies the policy and option descriptions. The available categories are not restricted to a fixed classification vocabulary learned during training.

The decoder represents the state and question branches. A shared **256-dimensional pointer head** scores the supplied options using representations of the decision position and each option endpoint. A softmax produces the distribution. Decision training updates LoRA adapters and the head; release exports merge the adapters into the decoder.

The ordinary language-generation head is not part of this interface. Nev does not generate a textual explanation or perform a tool action. The application receives the decision and decides what to do with it.

The runtime supports three execution forms:

- **Packed:** state and question branches share a pass with a mask that separates the branches; used in training and practical evaluation.
- **Rows:** each question has a causal row containing its state and branch; used for the external subset evaluations.
- **Cached:** encode the state once and reuse its prefix cache for question branches; used by the native examples.

These paths are intended to compute the same decision function, but arithmetic and precision can change close answers. Benchmark scores below identify the evaluated artifact and execution conditions.

## 3. Making Nesso2 work with Kev

The original feasibility work extended Kev's decoder support to the Llama-style Nesso2 backbone and checked its tokenizer and decision delimiters. It preserved the supported decoder and added bilingual data/training behavior.

Before the full run, checks covered rendering, branch isolation, packed/rows/cached consistency, finite nonzero adapter/head updates, export and reload. A small memorization experiment established that learning occurred. A resume experiment reproduced all **452 trainable tensors exactly**. These checks helped establish implementation correctness; the later held-out evaluations measured how far that learning generalized.

All decision-model training and evaluation described here ran on **LUMI AMD MI250X / ROCm**. The earlier foundation and Nesso2 stages used the separate infrastructure described by the parent card.

## 4. Building and reviewing the bilingual corpus

The full reviewed decision-training corpus contained **713,198 records: 356,599 English and 356,599 Italian**.

| Source family | Decision behavior represented |
|---|---|
| AG News and TREC | Topic and question classification |
| Banking77 | Banking intent classification |
| BoolQ | Boolean question answering |
| MNLI | Natural-language inference |
| SST-5 | Ordered sentiment decisions |
| Generated rules | Executable policy and compositional labels |
| Custom support tickets | Application-style decisions |

About **72% of the corpus was MNLI**. Exact language balance therefore did not imply balanced task exposure. This distinction became important when later practical tasks remained weak despite strong original-domain results.

English/Italian counterparts retained matching answer identities and supervision. Source grouping and split separation preceded translation. Reviews filtered conflicting duplicate labels, malformed translations, and schema/context failures, with paired exclusions so one language did not silently receive different examples.

Italian text was translated using the existing LUMI vLLM setup with **Qwen3.6-35B-A3B**, pinned to `995ad96eacd98c81ed38be0c5b274b04031597b0`, and translation prompt `vllm-quoted-fewshot-v3`. An earlier translation artifact was rejected and retained for diagnosis.

The translator supplied Italian wording. Gold decision labels remained the supervision for the full run. Translation quality was reviewed but is not equivalent to a fully native, independently authored Italian corpus.

### Why the full run used gold labels

A representative pilot used 1,684 bilingual training records and compared gold-only training with teacher distillation. Teacher selection considered Nesso and Qwen alternatives; the selected Nesso teacher supplied soft targets where its interface could admit the question. Banking77 remained gold-only because that interface could not handle all 77 options.

On the full pilot test, with 341 questions per language:

| Pilot student | English | Italian |
|---|---:|---:|
| Gold-only | 38.4% | 36.4% |
| Distilled | 37.0% | 34.6% |

The teacher was much stronger on common eligible questions, but the tested distillation recipe did not transfer that advantage to the student. Paired intervals for the difference included zero. The full decision run therefore used gold labels. This experiment does not settle whether a different teacher, objective, or data mixture would help.

## 5. Full decision training and the first evaluation gap

| Setting | Full-run configuration |
|---|---|
| Initialization | Pinned Nesso2-0.4B-agentic decoder |
| Trainable components | LoRA adapters and shared decision head |
| LoRA | Rank 16, alpha 32, dropout 0.05 |
| Target projections | q/k/v/o and gate/up/down |
| Decision-head dimension | 256 |
| Optimizer and schedule | AdamW, OneCycle |
| Learning rate / weight decay | 5e-5 / 0.01 |
| Microbatch / accumulation | 1 / 8 |
| Language sampling | Four English and four Italian records per full eight-record update |
| Precision | FP32 parameters, BF16 autocast |
| Seed / epochs | 0 / 2 |
| Completed updates | 178,300 |
| Original development selection | Checkpoint 142k |

The language constraint is on **records and loss weight**, not equal token counts. Italian and English versions can tokenize to different lengths.

The original 142k-selected export reached **88.29% English / 86.87% Italian** on its original training-domain test, and **59.30% / 60.70%** on a separate unseen-source panel. These are historical control results on those mixtures, not scores for either released variant.

External MMLU, HellaSwag, ARC, ANLI, CLINC and When2Call subsets showed a much larger gap. This motivated the practical adaptations. Original checkpoint **74k** became their starting point; the original development-selected **142k** was retained as a control. Repeated external inspection influenced the experiment direction, so those external panels are reused diagnostic evidence rather than fresh independent release-selection tests.

## 6. The adaptation experiments

### Practical v1: an improvement that exposed a confidence failure

Starting from 74k, 512 additional updates on 4,096 records improved the synthetic practical final test:

| Model on the v1 practical test | English | Italian |
|---|---:|---:|
| Original 74k | 33.01% | 31.64% |
| After 512 updates | 40.23% | 35.35% |

Development improved more than the final test. Training, development and calibration shared narrow instruction wording, while the final test changed it.

A threshold of 0.7 selected on familiar wording accepted 55.08% of English and 40.63% of Italian final cases, with error rates of **59.57% and 67.31%** among accepted decisions. The confidence policy failed. This led to separating instruction wording as well as fact configurations in the next experiment.

### Practical v2: separate wording, replay, and development selection

V2 restarted from **original 74k**, independently of v1. Its 8,192 training records comprised 4,096 new practical examples and 4,096 original-data replay records, with exact EN/IT balance.

Training, development, temperature fitting, confidence-policy selection, and final testing used disjoint instruction banks and fact configurations. Previous v1 configurations were excluded. The adaptation used a learning rate of 1e-5, accumulation 8, 32 warmup updates, and evaluation every 128 updates. Original-domain retention constraints limited NLL increase to 0.05 and accuracy loss to two percentage points.

Development selected **+256 updates**. The selected adapter scored **43.75% EN / 45.90% IT** on 2,048 final practical requests. Laya scored **43.65% / 39.06%** on those same requests; the English difference was only one correct answer. The actual v2 export was subsequently evaluated independently and scored **44.14% / 45.51%**.

No confidence threshold qualified under the declared policy. V2 is retained for its measured relative strengths, especially refund decisions and Italian urgency compared with v3.

### Focused v3: stronger routing with measurable forgetting

V3 initialized from the selected v2 checkpoint. Its 8,192-record mixture was:

| Component | Records |
|---|---:|
| New routing examples | 1,024 |
| New synthetic 16-intent examples | 1,024 |
| Banking77 replay | 3,072 |
| Other original-data replay | 3,072 |

Each update remained half English and half Italian. Selection applied separate original-domain and practical-v2 development retention checks. The fixed selection was **+512 updates**. Training stopped at +896; later +640, +768 and +896 checkpoints failed retention eligibility.

A new synthetic 16-intent/routing test contained 512 requests per language:

| Artifact on the new synthetic test | English | Italian |
|---|---:|---:|
| V2 adapter | 23.63% | 25.00% |
| V3 adapter | 54.88% | 62.89% |
| **V3 released export** | **54.69%** | **62.50%** |
| Laya | 26.17% | 28.71% |

The v2 export was not measured on this new panel; the v2 row above is explicitly its adapter. This controlled synthetic 16-intent task differs from 151-option CLINC and real customer traffic.

A later regression audit showed that routing gains accompanied refund losses and lower Italian urgency accuracy. Aggregate retention checks had not protected every individual task. That is why both variants are retained. No confidence threshold qualified for v3 either.

## 7. Results for the weights actually released

The following tables evaluate **merged exported weights**, not inferred adapter performance. Both exports store FP32 parameters; these benchmark runs used BF16 autocast. The external subsets used rows/T=1 scoring, while practical evaluation used packed logits.

Every comparison in the first table uses identical examples across v2 and v3. Unsupported requests count as incorrect. N is the number of examples **per language**.

| Task | N/language | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|---:|
| ARC-Challenge | 200 | 31.00% | 29.00% | 30.50% | 31.00% |
| HellaSwag | 200 | 33.00% | 33.00% | 29.50% | 33.00% |
| MMLU | 228 | 31.58% | 32.46% | 32.02% | 32.46% |
| ANLI | 150 | 30.67% | 38.00% | 30.00% | 38.00% |
| CLINC150+OOS | 151 | 4.64% | 6.62% | 5.30% | 12.58% |
| When2Call MCQ | 150 | 48.00% | 40.67% | 46.00% | 38.67% |
| Practical escalation | 256 | 51.95% | 51.56% | 53.52% | 51.17% |
| Practical refund | 256 | 61.33% | 52.73% | 52.73% | 50.39% |
| Practical routing | 256 | 29.69% | 34.77% | 55.08% | 46.88% |
| Practical urgency | 256 | 33.59% | 42.97% | 33.59% | 37.89% |
| **Practical overall** | **1,024** | **44.14%** | **45.51%** | **48.73%** | **46.58%** |

V3 improves practical routing by **25.39 English / 12.11 Italian percentage points** over the v2 export. Refund accuracy falls by **8.59 / 2.34 points**, and Italian urgency falls by **5.08 points**. The higher practical average does not mean all decisions improved.

### Comparing with Laya fairly

The comparison model is `convaiinnovations/laya-multilingual`. Its context/option admission limits exclude some examples that Nev can accept. For the table below, an English/Italian pair is included only when both versions fit every model in the recorded comparison. This produces smaller denominators for the external panels.

| Panel on common bilingual support | N/language | V2 EN / IT | V3 EN / IT | Laya EN / IT |
|---|---:|---:|---:|---:|
| Okapi academic subset | 513 | 31.19% / 31.19% | 30.41% / 32.55% | 30.02% / 27.10% |
| Decision Index subset | 378 | 24.07% / 25.66% | 23.81% / 27.78% | 30.16% / 32.01% |
| Practical v2 | 1,024 | 44.14% / 45.51% | 48.73% / 46.58% | 43.65% / 39.06% |

These are separate panel averages, not one combined benchmark score. The full-panel task table and common-support table have different denominators and should not be compared as if they used identical samples. Laya remains substantially stronger on CLINC, despite Nev's gains on the new synthetic 16-intent task.

The academic tasks use the multilingual evaluation work associated with Okapi in lm-evaluation-harness. The Decision Index work adapts selected tasks; it does not reproduce an official full-suite composite score. Italian evaluation text is synthetic and partly reviewed, including corrections to 27 CLINC labels. CLINC itself was not a training source, although other intent tasks were. Pretraining contamination is unknown.

## 8. Harder examples: what the easy demo concealed

A parcel message routed to “shipping” with a high probability establishes that loading and inference work. To examine more useful behavior, we added **20 authored requests**, ten in each language, each asking four decisions together. Five paired scenarios change exactly one verified fact while keeping the message and policy fixed.

| Scenario pair | Single changed fact | Decision that should change |
|---|---|---|
| Return window | Product delivered 29 vs 31 days ago | Approve vs reject reimbursement |
| Security override | Unauthorized activity unconfirmed vs confirmed | Account vs security routing; urgency and escalation |
| Duplicate payment | Not yet refunded vs already refunded | Approve vs reject reimbursement |
| Delivery deadline | 25 vs 23 hours remaining | Priority vs urgent |
| Repeated contact | Two vs three unsuccessful previous contacts | No escalation vs escalation |

Messages contain distracting secondary requests, resolved complaints, suspicion distinguished from confirmed findings, and angry wording that should not change the policy. Expected answers were fixed before inspecting either model. Only the request enters the model; the answer key and pair metadata do not.

Both models were tested in native cached FP32 inference on the released HF revision:

| Correct answers on this small diagnostic | V2 EN | V2 IT | V3 EN | V3 IT |
|---|---:|---:|---:|---:|
| Routing | 7/10 | 5/10 | 9/10 | 5/10 |
| Refund | 8/10 | 8/10 | 8/10 | 8/10 |
| Urgency | 4/10 | 6/10 | 6/10 | 5/10 |
| Escalation | 8/10 | 8/10 | 8/10 | 8/10 |
| All four decisions correct | 2/10 | 2/10 | 2/10 | 0/10 |
| Changed decision correct on both sides | 0/7 | 1/7 | 1/7 | 0/7 |

**Both models answered false for every refund and escalation question.** The 8/10 counts merely equal the always-no baseline and miss every positive case. Always choosing routine urgency would score 5/10, and always choosing shipping would score 4/10, on this particular fixture.

Concrete v3 failures make the limitation clearer:

- After three unsuccessful English support contacts, the supplied rule requires escalation. V3 declines with probability **0.9885**.
- For a confirmed duplicate English charge that has not been refunded, the policy requires reimbursement. V3 declines with probability **0.8869**.
- For an Italian unopened-product return at 29 days, v3 denies reimbursement and routes to shipping. Changing 29 to 31 days does not repair its interpretation.

These cases expose weaknesses in applying the supplied policies and separating relevant facts from distracting wording. They are small, correlated, authored diagnostics, conceptually related to practical training tasks—not representative accuracy estimates. They were not used to train these released models. If used in future training, they must not continue to be reported as fresh independent tests.

## 9. Calibration, export, and verification

Temperature fitting and confidence-policy selection used distinct splits. The stored temperatures are **0.7320428479728127 for v2** and **0.8122523963562355 for v3**. Neither variant qualified for the declared confidence policy, which targeted at most 10% error with at least 30 accepted examples per language. The runtime still returns a decision. Temperature scaling does not implement abstention or make the probability a correctness guarantee.

FP32 merging and isolated reload were checked independently:

| Check | V2 | V3 |
|---|---|---|
| Maximum merge probability difference | 3.40e-6 across 16 questions | 4.62e-6 across 40 questions |
| FP32 argmax changes in merge check | 0 | 0 |
| Isolated same-dtype reload | Exact | Exact |

Small FP32 merge differences do not imply identical BF16-autocast benchmark answers. V3's merged model changed 12 of 1,024 predictions on the new synthetic test relative to its adapter. The release tables therefore score the actual exports separately.

The packaged runtime preserves 17 frozen source files identified by SHA-256. An isolated installation passed offline inference for both languages and variants. Later, both variants were downloaded from the private HF repository and tested on LUMI again; all four original smoke-example answers and probabilities matched the local-export results exactly.

The immutable model revision is:

```text
giux78/nev@c5c84121263b423f8846811a24790ab96e66cee3
```

HF privacy, remote weight sizes, and LFS SHA-256 were verified after upload. The evaluated core model files were unchanged. Weights are stored on Hugging Face; this repository contains source, recipes, descriptions, result evidence, and provenance.

## 10. Install and load the released model

Use **Python 3.12** and install a PyTorch build appropriate for your hardware first. The verified environment was LUMI ROCm with PyTorch 2.10.0, Transformers 5.17.0, PEFT 0.21.0, Safetensors 0.8.0, Accelerate 1.13.0 and Hugging Face Hub 1.27.0. Other GPU platforms, CPU/mobile deployment and quantization have not been validated by this release.

From a checkout of this repository:

```bash
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime
hf auth login
```

Use an HF account that has access to the private model repository. The requirements record tested primary versions, not a complete transitive or hardware lockfile.

The simplest CLI downloads the pinned artifact and runs the native runtime:

```bash
python examples/hf_decide.py --variant v3 --language both
```

That built-in message is a loading smoke check. For a more demanding four-question Italian request, inspect and edit `examples/request-complex-it.json`, then run:

```bash
python examples/hf_decide.py --variant v3 \
  --request examples/request-complex-it.json
```

The JSON has two top-level fields, `state` and `questions`. It can include multiple `choice`, `noul`, and `score` questions with their own instructions and options. The response contains an `answers` object keyed by the question IDs, together with token usage and execution information.

Equivalent Python loading is:

```python
import json
from pathlib import Path
from huggingface_hub import snapshot_download
from decision_model import DecisionModel

revision = "c5c84121263b423f8846811a24790ab96e66cee3"
variant = "v3"  # or "v2"
folder = Path(snapshot_download(
    "giux78/nev",
    revision=revision,
    allow_patterns=[f"{variant}/**"],
)) / variant

model = DecisionModel.from_pretrained(folder, device="cuda")
request = json.loads(Path("examples/request-complex-it.json").read_text())
result = model.evaluate(**request)
print(json.dumps(result["answers"], ensure_ascii=False, indent=2))
```

PyTorch uses the `cuda` device name for the supported ROCm GPU path too. The native loader reads the artifact's `config.json`, `backbone/`, `tokenizer/`, decision head and calibration. It does not need to fetch the original parent after the standalone artifact has been downloaded.

The runtime enforces artifact-specific admission limits and rejects oversized inputs instead of silently truncating them. A selected option is always a model decision over the options supplied by the application; a high assigned probability is not permission to act without whatever checks the application needs.

### Can Transformers load Nev directly?

Transformers already loads the decoder inside the runtime. The whole released decision model is currently a custom `nn.Module` with `model_type=decision_model` and no `auto_map`. Therefore plain `transformers.AutoModel.from_pretrained("giux78/nev")` is not a supported loading command.

A custom `PreTrainedConfig` / `PreTrainedModel` wrapper and Hub registration could provide that interface without retraining. It would need to preserve the renderer, head, tokenizer, calibration, and equivalent outputs. That wrapper is not implemented in this release. For now, use the HF download plus native loader shown above.

## 11. Run the useful examples on LUMI

A ready copy of the examples and frozen runtime is staged in the existing project installation. After connecting to LUMI:

```bash
cd /scratch/project_465002563/decision-models/kev-nesso2/releases/publication-nev/demo

# Download the pinned private variants into the scratch cache.
bash examples/lumi_nev.sh fetch v2
bash examples/lumi_nev.sh fetch v3

# Compare both models on all 20 harder bilingual requests.
sbatch examples/lumi_scenarios.sbatch
```

The fetch commands use the existing HF login. GPU inference then runs offline in the recorded container. The job loads each model once, warms it up, and prints every prediction, assigned probability, expected answer and success/failure. A full JSON report is saved alongside the log.

Replace `JOBID` with the number returned by `sbatch`:

```bash
squeue -j JOBID
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.log
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.json
```

The completed run reported above is **22720810**, so its results can be inspected immediately:

```bash
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-22720810.log
```

To run only v3, append `--variants v3` to the scenario submission. To edit your own four-question Italian case and inspect one model:

```bash
sbatch examples/lumi_nev.sbatch --variant v3 \
  --request examples/request-complex-it.json
```

That single-request job writes `logs/nev-demo-JOBID.log`. For a quick test of your own text against the simple example's three department options:

```bash
sbatch examples/lumi_nev.sbatch --variant v3 --language it \
  --state "Mi avete addebitato due volte la stessa fattura."
```

These wrappers use the existing LUMI project environment and request one GPU on `dev-g`. When using another checkout on LUMI, submit from its root so `SLURM_SUBMIT_DIR` locates `runtime/` and `examples/`. All download, cache, log and result paths remain under `/scratch/project_465002563/`.

First-call time includes initialization and warmup. The difference between a slow first example and a faster later example is not a controlled latency benchmark.

## 12. Rebuilding the decision training

The practical synthetic generators run with the Python standard library:

```bash
python tools/generate_synthetic.py --variant v2 --out data-v2-synthetic
python tools/generate_synthetic.py --variant v3 --out data-v3-synthetic
```

Use new output directories. The generators reproduced all eight recorded held-out split hashes: development, temperature fitting, confidence-policy selection and test for each variant. Pair validation checks one English and one Italian record with matching supervision.

Generated training files contain the new synthetic data only. Reconstructing the actual 8,192-record adaptation mixtures also requires the recorded original-data replay; the commands above do not recreate or redistribute the third-party base corpus.

The complete decision-stage recipe is:

1. Prepare source datasets at their recorded revisions, deduplicate, and enforce grouped split separation before translating.
2. Create and review Italian counterparts with the pinned translation setup, preserve gold labels, and apply paired exclusions.
3. Train the reviewed 713,198-record corpus using the full-run settings above. Preserve intermediate checkpoints, especially 74k and the independently selected 142k control.
4. Build v2 with disjoint practical instruction/fact splits and replay. Initialize from 74k, apply its development retention checks, and retain the full candidate-selection history. The observed selection was +256.
5. Build v3's routing/16-intent mixture plus Banking77 and broad replay. Initialize from selected v2, apply both development checks, and preserve rejected checkpoints in the history. The observed selection was +512.
6. Fit temperature and confidence policy on distinct splits; record that no threshold qualified. Export merged FP32 weights, verify merge and isolated reload, and evaluate the actual export independently.

Training for exactly the selected number of updates without reproducing selection is not the same experiment. Source manifests, recipes, retained controls and rejected candidates are part of the record.

The operational recipe files are `recipes/base-recipe.json`, `recipes/nesso2-practical-v2.json` and `recipes/nesso2-focused-v3.json`. The data revisions and review exclusions are in `recipes/data-manifest.json`; split hashes are in `recipes/synthetic-split-hashes.json`. Frozen implementations live in `recipe-source/`, and historical LUMI launchers in `experiments/lumi/`.

**A portable end-to-end rebuild from an empty machine is still unfinished.** Operational training wrappers expect the existing LUMI base-run tree and metadata. The repository provides the recorded recipes, implementations and verified inference artifacts; it does not claim that the complete foundation pretraining or decision-training pipeline has been independently rebuilt elsewhere.

## 13. What this work establishes, and what comes next

The project demonstrates a complete path from a foundation pretrained from scratch through bilingual agentic post-training to a functioning typed decision model. Within the decision stage, it documents learning, specialization, forgetting, export behavior, and substantial remaining weaknesses in policy-sensitive decisions.

The strongest observed development was v3's routing and synthetic 16-intent improvement. The central limitation is that success on a familiar task mixture and high softmax confidence do not establish reliable decisions under changed wording or interacting policies. The later contrast examples make that limitation visible without hiding it behind a favorable aggregate score.

The next experiments should use broader instruction wording and task balance, explicit positive/negative contrast pairs, and **task-level** development retention checks. Any examples used to improve the model must be separated from new independent tests. A Transformers loading wrapper would improve usability, but would not by itself fix the observed decision errors. These are directions for future work, not completed improvements.

The scope remains a small bilingual research model. External subsets have been reused; Italian text is partly synthetic; pretraining exposure is unknown; no confidence threshold qualified; and neither real-traffic reliability nor CPU/mobile, quantized or cross-platform performance is established here.

## 14. A few deeper records

The main reading path ends here. For auditing or rebuilding specific details:

- [Chronological experiment log](docs/nesso2/EXPERIMENT_LOG.md): launches, controls, failed attempts, checkpoint selection, release work and later diagnostics.
- [Machine-readable export comparison](export-comparison.json): exact task denominators, common-support comparisons and source provenance.
- [Evidence directory](docs/nesso2/evidence): detailed training, regression, export, publication and harder-scenario reports. Historical focused documents remain available as supporting records.

Kev attribution, Nesso2 provenance and upstream notices are retained in [NOTICE](NOTICE). Software and declared parent-model licensing are Apache-2.0; see [LICENSE](LICENSE). Source datasets retain their own terms. Original third-party training and benchmark texts and model weight binaries are not checked into this code repository.
