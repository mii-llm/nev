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
