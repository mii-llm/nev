# Build recipe and provenance

## Regenerate the authored synthetic splits

These portable commands use only Python's standard library, without a GPU,
model download or connection to LUMI:

```sh
python tools/generate_synthetic.py --variant v2 --out data-v2-synthetic
python tools/generate_synthetic.py --variant v3 --out data-v3-synthetic
```

Both commands were run successfully during preparation. All eight generated
held-out split files (dev, calibration-fit, calibration-policy and test for each
variant) exactly match the original experiment SHA-256 hashes. Pair validation
enforces one English and one Italian record with matching supervision per pair.
The generated training files contain only new synthetic examples: add the
recorded original-data replay and development guards before training. This
command does not reconstruct or redistribute the original third-party corpus.

## Full training lineage

Parent: `mii-llm/nesso2-0.4B-agentic`, revision
`86d4bb76c0dd32b6f2e759734d6a0cb0eab9b041`.

1. Prepare the source datasets at their recorded revisions; deduplicate and
   enforce grouped split separation before translation. Preserve gold labels.
2. Translate Italian using the recorded Qwen3.6-35B-A3B revision
   `995ad96eacd98c81ed38be0c5b274b04031597b0` and prompt
   `vllm-quoted-fewshot-v3`. Apply recorded schema, context and translation review
   exclusions to both members of each language pair.
3. Train on the reviewed 713,198-record corpus with LoRA r=16, alpha=32,
   dropout=.05 on q/k/v/o and gate/up/down projections, plus a 256-dimensional
   decision head. Use LR 5e-5, AdamW/OneCycle, accumulation 8, two epochs and
   seed 0. Parameters are FP32; training uses BF16 autocast. Each update has
   exactly four English and four Italian records. Save intermediate checkpoints.
4. Preserve original 74k for both released variants. The original run selected
   142k by its own development criterion; it is a separate historical control.
5. For v2, use `recipes/nesso2-practical-v2.json`: build the disjoint practical
   instruction/fact splits, mix original training replay, initialize from 74k,
   and select by eligible development macro NLL. The actual selection is +256.
6. For v3, use `recipes/nesso2-focused-v3.json`: initialize from selected v2,
   mix focused routing/16-intent data and Banking77/general replay, and enforce
   both recorded development guards. The actual selection is +512, with later
   snapshots rejected. Do not train 512 updates and call it a faithful reproduction
   of the selection procedure; preserve the full eligible-candidate history.
7. Fit temperature and confidence policy on their distinct splits. Record that
   no threshold qualified for either candidate. Export FP32 merged weights,
   prove merge and isolated offline reload, and evaluate the actual export.

The packaged inference runtime is extracted byte-for-byte from the frozen
regression evidence, rather than inferred from the working repository's Git HEAD.
`runtime/SOURCE_MANIFEST.json` identifies those bytes. `environment.json` records
the measured LUMI runtime. The Python dependencies alone do not reproduce the
AMD container, kernels or floating-point behavior.

The archived reference implementation is in `recipe-source/`, including data
generators, translation and selection code, and its per-file provenance manifest.
`recipes/data-manifest.json` records source revisions, splits, translation hashes
and review filters; `recipes/base-recipe.json` preserves the base settings.
`${PROJECT_ROOT}` in JSON is a placeholder requiring explicit substitution.

The public command-line training wrapper and portable data-reconstruction entry
point are still being prepared. Current operational wrappers expect a LUMI
base-run tree and previous experiment metadata. This release includes the recorded
recipe and frozen inference runtime; a one-command rebuild from an empty machine
has not been verified. The internal build record retains the historical launchers,
base recipe, source/data hashes, resume proof and translation provenance.
