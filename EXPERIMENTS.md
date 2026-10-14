# What we learned building Nesso2 Decision

The objective was to adapt a small independently pretrained English/Italian
backbone to Kev's typed decisions, keeping half of every training update in each
language. A state and explicit criteria replace open-ended generation: one
shared head selects among runtime options. The experiment explored whether a
small model could learn useful bilingual operational decisions, and where
adaptation improves one capability at the expense of another.

## 1. Establishing compatibility

We extended the Kev decoder path for the Llama-style Nesso2 backbone, validated
rendering and balanced sampling, and checked that the adapter and head receive
finite nonzero updates. A small memorization experiment verified learning; a
resume experiment reproduced all 452 trainable tensors exactly. These checks
supported the training implementation, but did not establish generalization.
The first tiny teacher experiment was an integration test, not evidence of a
competitive model.

## 2. Translation and the small teacher comparison

An early bilingual translation artifact was rejected and retained for diagnosis.
The corrected representative pilot contained 1,684 training records. A Nesso
teacher supplied soft targets for a controlled gold-only versus distilled
comparison; Banking77 was gold-only because the alternative teacher interface
could not admit all 77 options.

On the full 341-question/language pilot test, gold-only scored 38.4% EN / 36.4%
IT, versus 37.0% / 34.6% for distillation. On common eligible questions, the
teacher itself was much stronger, but its advantage did not transfer to the
student. Paired intervals included zero for the distilled-minus-gold difference.
We therefore used gold labels for the full run. This does not establish that
other teachers or distillation recipes would fail.

## 3. Moving to the full corpus

The reviewed corpus contained 713,198 training records, 356,599 per language.
It combined AG News, TREC, Banking77, BoolQ, MNLI, SST-5, generated rules and
support tickets. Around 72% was MNLI: language balance did not mean task balance.
Italian text was translated with the pinned Qwen3.6-35B-A3B vLLM setup; the
translator did not replace gold labels or distill the full decision model.
Conflicting duplicate labels, malformed translations and schema/context problems
were audited and filtered with paired exclusions.

The full run completed two epochs, 178,300 updates. Original development NLL
selected checkpoint 142k. Its export scored 88.29% EN / 86.87% IT on the original
training-domain test and 59.30% / 60.70% on a separate unseen-source panel. Those
numbers belong to that original model and those task mixtures, not either of the
two release candidates.

## 4. External tasks exposed a gap

Small paired MMLU/HellaSwag/ARC, ANLI, CLINC and When2Call panels showed much lower
accuracy than the training-domain tests. Original 74k was a useful starting point
for later adaptations; repeated external evaluation influenced that choice, so
these panels are diagnostic development evidence. CLINC was not in training,
although Banking77 and support-ticket intent classification were.

The Decision Index setup was a subset adapter, not the official composite score.
Italian text was synthetic and partially reviewed, including 27 corrected CLINC
labels. Context/option limits rejected more Laya examples on some tasks. Later
comparisons therefore report both full panels (unsupported is wrong) and
identical bilingual common support. A model comparison is meaningful only when
its task, denominator, scoring method and supported examples are explicit.

## 5. Practical v1: gains with a confidence failure

Starting from 74k, 512 extra updates on 4,096 records improved the synthetic
practical final test from 33.01% / 31.64% to 40.23% / 35.35% EN/IT. Development
accuracy rose sharply, but training, development and calibration shared a narrow
instruction template, while final test changed the wording.

A 0.7 threshold chosen on familiar wording accepted 55.08% of English and 40.63%
of Italian final cases, with error rates of 59.57% and 67.31%. This was a failed
confidence policy. The lesson was to separate wording as well as facts, not to
interpret a high softmax probability as correctness.

## 6. Practical v2: independent wording and a fixed selection

V2 restarted from original 74k, not from adapted v1. Its 8,192 training records
were half new practical examples and half original-data replay, with equal
English/Italian weight. Training, development, temperature fitting, policy
selection and final test used disjoint instruction banks and fact configurations;
previous v1 configurations were excluded.

Development selected +256 updates. On 2,048 final requests the adapter scored
43.75% EN / 45.90% IT. Laya scored 43.65% / 39.06% on those same examples; the
English difference was one answer. No confidence threshold qualified on the
predeclared policy. V2 is retained because some capabilities survive better than
in the more specialized v3 model, not because the policy is solved.

## 7. Focused v3: routing and intent, with two retention guards

V3 started from selected v2. The 8,192-record mixture added routing and synthetic
16-intent examples, Banking77 replay and broad original-data replay. Every
update remained half English and half Italian. Selection checked the original
development guard and the v2 practical development guard separately.

The fixed selection was +512 updates; training stopped at +896. Later +640,
+768 and +896 checkpoints failed retention eligibility. On a new 1,024-request
synthetic intent/routing test, v2 scored 23.63% / 25.00%, v3 adapter 54.88% /
62.89%, and Laya 26.17% / 28.71%. The merged v3 export scored 54.69% / 62.50%.
This is a controlled 16-intent synthetic result, not a claim about CLINC or real
customer traffic. No confidence threshold qualified.

## 8. The regression audit explains why we retain two models

The fixed v3 adapter and export were rerun on 4,206 frozen requests each, half
English and half Italian. Relative to v2, adapter routing improved by 24.22/13.28
points on the older practical test, but refunds fell 9.38/3.91 points and Italian
urgency fell 5.47 points. The practical average still increased to 47.75/46.88%.
The export showed the same tradeoff. Aggregate development guards had not
protected each individual practical task.

External changes were mixed: English HellaSwag fell 3 points, while Italian
CLINC rose 5.30 points. Laya remained substantially stronger on CLINC. These
small reused panels do not establish statistical or population-level superiority.
Both variants therefore remain useful research artifacts with different measured
strengths; v3 is not presented as a universal replacement for v2.

## 9. Export arithmetic is part of the result

FP32 merge and isolated offline reload are checked separately from BF16-autocast
benchmark inference. V3's merge check had maximum probability difference 4.62e-6
on 40 questions and no changed argmax; the same-dtype reload was exact. Yet BF16
autocast changed 12/1,024 answers on the new synthetic test after merging.
Adapter scores must therefore never be silently assigned to released weights.
The v2 export was evaluated independently on all 4,206 original regression requests. Its practical accuracy is 44.14% EN / 45.51% IT; merge/reload passed, with no FP32 argmax changes. Detailed actual-export comparisons are in EXPORT_COMPARISON.md.

## Interpretation and reproducibility

This study shows learning, specialization and measurable forgetting in a small
bilingual decision model. It does not prove the optimal recipe for this size,
independent gains on every domain, or readiness for unattended decisions.
Pretraining contamination and broader real-traffic generalization are unknown.
Future work can use task-level development guards, broader wording and balanced
replay; none of those future experiments are claimed as completed here.

The accompanying recipes, frozen inference source, model identities, environment
versions and result tables identify the two candidates. Original experiment
archives preserve failed runs and selection history. Site-specific job logs and
raw third-party dataset texts are kept separate from the public-facing draft.

## 10. CPU conversion: fidelity, latency and retained failures

The 14 October 2026 Mac experiment converted the pinned Nesso3 generator and
Nev v3 decoder to F16 and Q8_0 GGUF. A separate llama.cpp bridge exposes Nev's
final hidden states to its unchanged FP32 pointer head and calibration; each
question uses an isolated causal row. Metal and CUDA were disabled. No training
or quantization recalibration was performed.

Twenty Nev verification requests contained 24 questions: F16 kept all decisions,
Q8 changed one (maximum probability deltas 0.00541 and 0.06086). Eight Nesso
first-generation probes matched the reference 8/8 in F16 and 7/8 in Q8, with
identical tokenization. This establishes limited conversion fidelity, not global
equivalence.

The 12-request agent comparison used the original abstract controller and
read-only mock fixtures. All three backends executed 9/10 supported plans, but
full-answer inspection reduced success to 7/10 because matching an answer anchor
did not catch a wrong unit or confusing artist and title. Unsupported-action
refusals were 0/2. The same semantic weaknesses exist in the FP32 reference.
Warm medians were 3.39 seconds FP32, 4.24 seconds F16 and 1.89 seconds Q8 on an
M3 Pro with four CPU threads. Raw results and the corrected review are retained
in `experiments/cpu_gguf/results/`; original measurement provenance and published
source hashes are kept distinct. The CPU bridge was rebuilt and selected
bilingual smoke examples rerun from the publication checkout.
