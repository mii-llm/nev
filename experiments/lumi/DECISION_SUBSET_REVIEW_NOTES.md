# Italian semantic review in progress

The Italian evaluation is **not yet approved**. Translation repair job 22573534 reduced
the automatic failures from 143 to 12. Four were reviewed and corrected in the
cache (three added question marks; one wind-speed range formatting change).
The other failures exposed an overly broad placeholder policy for prose.

`prepare_decision_subset.py` now protects technical literals in prose, not common
schema words such as `to`, `class`, `regular`, `time` or `date`. The complete JSON
tool calls and schema keys/enum values remain unchanged. The English sample is
unchanged. New active translation input: 3,979 unique strings; 1,710 need a new
translation under the revised masking. Jobs: **22575243** translation and
**22575244** dependent CPU audit. At the latest check, translation was pending.

## Required follow-up before scoring

1. Check the two jobs and any remaining automatic flags. Do not approve the
   panel merely because the automatic checks pass.
2. Normalize remaining quoted translation output. Inspection found outer quoted
   strings with literal newlines, which strict `json.loads` rejects. Consider
   `json.loads(text, strict=False)` only for JSON string decoding, retaining raw
   output and original prompt identity, with regression coverage. Some model
   responses also contain literal escaped quotes; inspect the decoded result.
   Do not globally replace arbitrary backslashes or quote characters.
3. Apply and document task-specific CLINC label corrections. The complete shared
   151-label vocabulary was read without gold labels. Definite errors include:
   - `account blocked`: remove the English-to-Italian arrow commentary; use
     `account bloccato`.
   - `carry on`: `bagaglio a mano`, not `prosegui`.
   - `change language`: `cambia lingua`, not unchanged English.
   - `food last`: `durata di conservazione degli alimenti`, not `cibo ultimo`.
   - `order checks`: `ordinare assegni`, not `verifiche degli ordini`.
   - `directions`: `indicazioni stradali`, rather than generic `istruzioni`.
   - `gas` / `gas type`: `carburante` / `tipo di carburante`.
   - `next holiday`: `prossimo giorno festivo`, not `prossime vacanze`.
   - `replacement card duration`: `tempo di attesa per la carta sostitutiva`,
     not the validity duration of the replacement card.
   - `routing`: banking routing number, not generic network routing.
   - `text`: sending a text message, not the noun `testo`.
   - `time`: current time (`ora`), not generic `tempo`.
   - `sync device`: `sincronizzare dispositivo`, not a synchronization device.
   - `bill due`: bill due date, not merely a bill to pay.
   - `how busy`: establishment crowding, not how occupied a person is.
   - Expand PTO appropriately as paid leave; retain the acronym for clarity.
   - Polish `oil change how`, `oil change when`, `todo list`, `apr`, `mpg`
     and `rollover 401k` using their original task meanings.
   Confirm ambiguous domain meanings against the source's training examples if
   needed. Prefer task-specific overrides so a label fix does not alter an
   unrelated short tool description that shares the same English string.
4. Ten deterministic ANLI review cases were read (the same SHA256-ordered sample
   that finalization writes). Most preserve the inference relation, but correct
   `royalty` to `famiglie reali` in
   `ANLI:test_r2:1e1dcd73-82a9-4e3e-b87e-7d885d1f33cd`. For
   `ANLI:test_r3:24fd1b4b-3819-4eab-83ea-0f69ce15c9fd`, the English hypothesis
   `All lettuce is not red.` is scope-ambiguous; Italian `Non tutta la lattuga è
   rossa` selects one reading. Preserve/document the source ambiguity or exclude
   the whole pair under an explicit translation-quality exclusion, not using its
   gold answer. Also check tense in the helicopter example
   `ANLI:test_r3:60b70232-6c44-45ea-9227-2aace7f068f5` (`is responding`).
5. Review the ten CLINC full request pairs and ten When2Call pairs, including
   translations of shared descriptions and prose answer options. Gold must not
   be passed to a translator or inference engine.
6. If data or scripts change, preserve the old version and manifest, update
   hashes explicitly, rerun the CPU capacity/pairing audit, and then write a
   truthful `quality-review.json` tied to the final panel hashes. Record the
   review as machine-assisted and partial, not native-speaker certification.
7. Only then launch the prepared selection evaluation for 74k, 142k, parent and
   Laya. Keep confirmation unused until a checkpoint choice is frozen.

All remote artifacts remain under
`/scratch/project_465002563/decision-models/kev-nesso2/runs/bilingual-all-v1/decision-index-bilingual-v1`.
English scoring has now been submitted independently in the sibling directory
`decision-index-english-selection-v1`: preparation 22577094, followed by 74000
(22577095), 142000 (22577096), parent (22577097) and Laya (22577098). It uses only
the unchanged 451 English selection cases, with native schema/token capacity,
checkpoint and runtime integrity checks. The English report lists only English
metrics; it does not report absent Italian scores as zero. Confirmation remains
unused. All five jobs were pending at the last check.

Translation job 22575243 completed its 1,710 requests, then stopped on two numeric
format flags: the movie-title Roman numeral `II` became `2`, and the source date
`2023 .10.01` lost its space. Audit 22575244 was cancelled. These two repairs and
the semantic review above remain required for Italian.

Domain meanings were checked against the pinned CLINC training examples, not
evaluation gold: `gas` refers to fuel-tank level; `how_busy` includes queue/wait
time; `text` means sending an SMS; `routing` is the bank routing number;
`carry_on` is airline hand luggage. The source training data itself contains at
least one apparent label anomaly (`tell me about today weather` labelled
`replacement_card_duration`); preserve original evaluation labels and disclose
that source labels are not guaranteed flawless.

The original completed Okapi results remain valid and untouched.

## Latest status: Italian selection released as a provisional diagnostic

The user explicitly accepts a few imperfect translations and does not want
them to block the evaluation. This supersedes the exhaustive-review prerequisite
above for this diagnostic. Both remaining numeric-format flags belong only to
confirmation cases; neither affects the 451 selection cases. Confirmation stays
unused. Applied 27 task-specific CLINC shared-label corrections, preserving gold
labels and JSON tool calls. Review remains partial and machine-assisted, with
residual semantic limitations disclosed in the frozen review artifact.

Italian artifacts are in the sibling `decision-index-italian-selection-v1`.
CPU preparation 22578695 COMPLETED successfully (exit 0, 1m11s). Italian GPU
jobs: 74000 = 22578696, 142000 = 22578697, parent = 22578698, Laya = 22578699.
All four were PENDING for Priority at the latest scheduler check, as were the
four English GPU jobs. English preparation 22577094 previously completed.
No new evaluation scores are confirmed yet. English jobs retain their frozen
source; the new Italian preparation source is isolated in the Italian run.
