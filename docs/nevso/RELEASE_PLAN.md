# Nevso release working record

User direction recorded on **19 October 2026**: prepare the **Nevso** agent,
combining Nev and Nesso3; prioritize the working GPU example and documentation.
RAM optimization is deferred. This document preserves the implementation,
evidence and release decisions for future work. It is a working record for that future release.

## Product and artifact identity

- Working name: **Nevso** — Nev + Nesso3 agent.
- Nev chooses/ranks functions; Nesso3 generates arguments and final prose.
- Generic controller validates calls and dispatches tools. It does not generate
  answer templates or read evaluation answer keys.
- This is a composition of two separate models plus software, not merged weights.
- Nev: `mii-llm/nev`, v3,
  `c5c84121263b423f8846811a24790ab96e66cee3`.
- Nesso3: `mii-llm/nesso3-0.4B-agentic`,
  `56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8`.
- Public model downloads require no login. Preserve upstream attribution and
  notices when preparing the eventual release.

## Evidence to carry into the release

1. [Mac routing comparison](../../experiments/cpu_gguf/ROUTING_COMPARISON.md):
   notes, sensors and music, 24 bilingual requests. Nev-selected exact execution
   22/24 versus 18/24 alone; reviewed task success 20/24 versus 14/24. Warm median
   1.72 s versus 2.57 s. The favorable example is note lookup in both languages.
2. [Mac greenhouse comparison](../../experiments/cpu_gguf/GREENHOUSE_COMPARISON.md):
   new JSON domain, 24 requests. Nev-ranked exact calls 23/24 versus 12/24 alone;
   reviewed factual success 22/24 versus 10/24. Ranked is more accurate here;
   selecting one tool is faster but propagates wrong Nev choices.
3. [GPU guide and evidence](GPU_GUIDE.md): native A100 backend, same frozen
   greenhouse suite and controller. GPU results must remain separate from Q8
   because precision and kernels differ. On the A100, ranked exact calls are
   23/24 versus 13/24 alone; reviewed factual tasks 22/24 versus 12/24. Warm
   medians are 1.44 s versus 1.38 s on a shared GPU. Peak PyTorch allocation is
   2.55 GiB. Native standalone/CLI reruns and the Mac regression were verified.
4. Every published comparison keeps its full raw results, readable traces, model
   revisions, source hashes and the frozen input suite. Review labels are
   assistant-produced, not an independent human audit.

## Implementation to reuse

- `examples/nevso_demo.py`: simple CLI, native CUDA by default; Mac GGUF supported.
- `experiments/cpu_gguf/compare_routing.py`: shared comparison loop; `--suite`
  supplies domain schemas, mock responses and evaluation cases.
- `experiments/abstract_agent/backend.py`: native GPU model adapter.
- `experiments/cpu_gguf/cpu_backend.py`: existing Mac GGUF adapter.
- `experiments/cpu_gguf/abstract_agent/runtime.py`: bounded generic controller.
- `experiments/cpu_gguf/greenhouse_suite.json`: frozen public example data.

The three comparison strategies are `nesso_only`, `nev_ranked`, `nev_selected`.
Domain configuration is external. The best accuracy/latency tradeoff varies by
catalog; do not market one strategy as universally best.

## Requirements before a broader Nevso launch

- Choose the release packaging and destination; no separate Nevso repository or
  Hugging Face checkpoint has been created in this task.
- Keep the quick start, bilingual human-readable examples and failures together.
- Label demonstrations as read-only mock workflows. Real integrations need an
  application-owned executor and authorization boundary.
- Keep correct tool execution separate from final-answer correctness and format
  compliance. Confidence is not a correctness guarantee.
- Test fresh held-out prompts, tool orders and domains before broader claims;
  current examples are reused development evidence.
- Document the known limits: unsupported actions, missing arguments, dependent
  multi-step tasks, boolean policies, high-confidence mistakes and Italian
  confusions. No demonstrated production reliability or autonomous safety claim.
- Preserve the CPU and GPU regression checks. Memory optimization is a separate
  future experiment, not a prerequisite for the example requested here.

## Stronger evaluation started on 19 October 2026

User approved a larger external-plus-authored evaluation. The frozen package is
[experiments/nevso_stress](../../experiments/nevso_stress/README.md): 100 EN/IT
pairs, three strategies, three seeded tool-order draws, 1,800 trials. It keeps
60 BFCL-derived call-only cases separate from 140 authored workflow cases across
five domains. This is an adapted diagnostic evaluation, not an official BFCL
score or a contamination-free benchmark.

The 12-trial pilot and six evaluation-contract checks completed on the A100.
The full run was launched in the existing GPU checkout, with relative output
`results/nevso-stress-a100-20261019`; its PID at launch was `3587245`. Logs are
saved beside the checkout as `nevso-stress-a100-20261019.log`. Results remain
pending as of this entry. Verify metadata status and trial count before reporting
completion. The runner saves every trial and supports matching-source resume.
After completion, use `experiments/nevso_stress/analyze.py` to produce the paired
report, then review traces and preserve evidence before publishing performance
claims. Do not replace earlier greenhouse results with partial stress results.

Nesso3's training card discloses When2Call, whose source fields refer to BFCL.
Actual overlap with the selected BFCL IDs is unknown. Disclose this possible
indirect exposure. The 70 freshly authored pairs are separate; they still do not
constitute an independent audit. The full test preserves the one-shot selection
strategy, whose multi-step restriction is reported separately.


### Completed stress test and scoring audit

The full run completed all 1,800 trials on 19 October, 15:32:13–16:19:33 UTC
(47m20s), without infrastructure failures. Evidence is now in
[the stress-test review](../../experiments/nevso_stress/REVIEW.md).
Authored confusable exact calls improved from 17/60 EN and 23/60 IT standalone to
56/60 EN and 43/60 IT with selection; ranking achieved 40/60 EN and 44/60 IT.
External BFCL point estimates did not improve: 19/90 EN and 21/90 IT standalone,
15/90 and 13/90 ranking, 16/90 and 18/90 selection. Preserve this counterevidence.

The clarification proxy falsely accepted refusals, wrong fields and fabricated
`additionalProperties` arguments. Exhaustive assistant review of the 270
clarification trials gives clean clarification 0/45 EN and 7/45 IT standalone,
0/45 and 5/45 ranking, 16/45 and 20/45 selection. Keep original proxy scores and
new review labels separate; never market the raw 71.1%/62.2% proxy as reliable
clarification. Other completion proxies remain provisional. Multi-step, no-tool,
error stopping and exact formatting remain weak. Some date-format failures
contained factually correct dates written in words. No fixes or retraining have
been applied as part of this evaluation.


### Qwen3-0.6B baseline requested

The user requested Qwen3-0.6B on the same dataset and a clearer explanation.
[EXPLAINED.md](../../experiments/nevso_stress/EXPLAINED.md) distinguishes call
selection, arguments, final answers and workflow completion using real traces.
The Qwen-only runner is in
[qwen_baseline](../../experiments/nevso_stress/qwen_baseline/README.md).

Pinned Qwen revision: `c1899de289a04d12100db370d81485cdf75e47ca`.
Native Qwen tools template, thinking disabled, greedy BF16, 192 new tokens per
turn, unchanged controller/fixtures/data/scoring. This is the same runtime
budget, not Qwen's maximum thinking-mode capability or recommended sampling.
Only Qwen is loaded; shared-GPU timings remain illustrative. Nev + Qwen is not
part of this run.

Four adapter tests and the separate four-trial pilot passed. A cache-only
preflight failure occurred before model loading and was repaired by matching
the download file patterns; no test prompts or scoring were tuned. The full
600-trial run launched on the existing A100 checkout with PID `941970`, relative
output `results/qwen3-stress-a100-20261019`, and sibling log
`qwen3-stress-a100-20261019.log`. Its runner writes COMPARISON.md on completion.
Results are pending at this entry. Check status/count before claiming completion,
preserve all evidence, and review Qwen clarification outputs using the same
review criteria before comparing them with reviewed Nesso clarification scores.


### Qwen comparison completed

All 600 Qwen trials completed on 19 October, 16:41:00–16:52:29 UTC (11m29s),
without infrastructure errors. Evidence and the reviewed interpretation are in
[qwen_baseline/REVIEW.md](../../experiments/nevso_stress/qwen_baseline/REVIEW.md).
Qwen BFCL calls: 45/90 EN, 43/90 IT. Authored confusable correct calls: 44/60 EN,
45/60 IT; answer proxy: 44/60 EN, 43/60 IT. Nev-selected + Nesso3 remains stronger
on authored English executed calls (56/60), but not its answer proxy (41/60).
Qwen dependent completion was 0/60 in the unchanged controller; sampled outputs
attempted the dependent call with placeholders in the same batch as the lookup.

All 90 Qwen clarification trials were assistant-reviewed: clean clarification
20/45 EN, 0/45 IT; two additional Italian responses were borderline conditional
offers about ticket type (2/45 if accepted). Preserve labels and the explicit
rubric, not just raw proxy counts. No blanket model superiority claim. Nev +
Qwen remains an untested possible follow-up, not a completed experiment.

### Launch articles prepared — 21 October 2026

Prepared two standalone drafts in [docs/launch](../launch/EVIDENCE.md):
[Nev](../launch/nev.md) and [Nevso](../launch/nevso.md). User direction is to
highlight compact size, local/edge inference, fast decisions and favorable
measured use cases. Nevso is positioned as a runnable developer preview of the
existing two-model workflow, with no new checkpoint implied.

The evidence index maps each launch claim to the saved reports. The articles
keep backbone file size separate from runtime RAM, standalone GPU decision
latency separate from full CPU workflow latency, and tool calls separate from
final-answer success. Earlier experiments and raw results remain unchanged.
The articles are local drafts; no external blog publication has taken place.
