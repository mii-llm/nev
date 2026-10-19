# Qwen3-0.6B baseline on the frozen Nevso test

User requested a small-model comparison to help interpret the BFCL and workflow
results. This run evaluates **Qwen/Qwen3-0.6B alone**, without Nev, on exactly the
same 200 requests (100 EN, 100 IT) and three starting tool-order draws: **600
trials**. No dataset, fixture, original controller or scoring files are changed.

Model revision: `c1899de289a04d12100db370d81485cdf75e47ca`.

## Serving and fairness

- BF16 CUDA on the same shared A100, with a 4 GiB process allocation cap.
- Native Qwen chat template with `tools=...` and `enable_thinking=False`. The
  controller's original tool JSON envelope is unpacked into that interface;
  valid historical calls become native `tool_calls`. Invalid/mixed model outputs
  are not repaired. Tool-response contents and user requests are unchanged.
- Greedy generation, maximum 192 new tokens per turn, original four-turn/eight-
  execution limits and strict parsing/validation. This matches the Nesso run's
  runtime budget. It is not a claim about Qwen's maximum capability: the official
  card recommends sampling for non-thinking use, and thinking requires a separate
  budget and evaluation. No output-driven prompt/sampling search is performed.
- Qwen sees all candidate tools. It is compared primarily to Nesso3 alone;
  the Nev-ranked/selected Nesso3 columns provide context. Selected Nesso3 has a
  smaller tool catalog, so these are different system configurations.
- Only Qwen is loaded in this baseline. The earlier run kept Nev and Nesso3
  resident. Shared-GPU timings cannot establish a controlled speed ranking.

The native-template smoke test and four adapter tests precede the four-trial
pilot. The pilot reuses the separate old greenhouse/arithmetic examples, not
any of the 200 stress requests. Hashes pin the adapter, runner, report and the
previous Nesso rows before Qwen stress outputs are inspected. Model outputs,
token counts and prompt hashes are retained for every generation.

## Interpretation

Use the existing call scores and output checks, broken down by language and
category. Do not combine BFCL call-only performance and workflow completion into
one accuracy number. The clarification proxy is known to be too generous; keep
it for reproducibility and review Qwen clarifications separately before comparing
them to the reviewed Nesso labels. Final-answer anchors elsewhere also remain
proxies. Exact-date compliance and semantic date correctness are different.

The BFCL subset is adapted, limited and potentially present indirectly in
training. This is not an official BFCL score. Comparing two models does not
isolate parameter count from training, tokenizer or architecture differences.

## Run

Use the existing GPU environment and download the pinned public model once:

```bash
python - <<'PYTHON'
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-0.6B',
    revision='c1899de289a04d12100db370d81485cdf75e47ca',
    allow_patterns=['*.json', '*.safetensors', '*.jinja', '*.txt', '*.model'],
    token=False)
PYTHON
python -m unittest discover -s experiments/nevso_stress/qwen_baseline -p test_adapter.py -v
python experiments/nevso_stress/qwen_baseline/run.py \
  --suite experiments/nevso_stress/pilot.json --orders 0 \
  --output results/qwen3-stress-pilot
python experiments/nevso_stress/qwen_baseline/run.py \
  --output results/qwen3-stress
```

Use a fresh output directory or `--resume` for an interrupted matching run. The
runner checks the original freeze and its own source freeze. `--baseline` can
point to another copy of the exact original Nesso `rows.jsonl`; its SHA-256 must
match. Results save incrementally; the completed run writes `COMPARISON.md` and
`comparison.json` alongside raw rows, readable traces and metadata.

Source: [official Qwen3-0.6B card](https://huggingface.co/Qwen/Qwen3-0.6B).
