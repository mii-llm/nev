# Qwen3-0.6B comparison

**Full run started on 19 October 2026; results pending.** Qwen alone is being
evaluated on the same 200 requests and three tool-order draws: 600 trials.
The separate four-trial pilot completed successfully on the A100.

The [protocol](PROTOCOL.md) pins the model revision, native tool template and
runtime budget. Qwen uses BF16, thinking disabled and greedy generation with the
same 192-token cap and controller as the Nesso3 test. The dataset and original
scores are unchanged. This measures the specified serving setup, not Qwen's
maximum thinking-mode performance.

The runner saves raw completions and readable traces incrementally and produces
`COMPARISON.md` on completion, including Nesso3 alone, both Nev + Nesso3 arms, and
Qwen alone. Clarification proxies need the same trace review before comparison
with the separately reviewed Nesso scores. We have not tested Nev + Qwen here.

See [how to read the existing results](../EXPLAINED.md) for the distinction
between tool calls and completed answers.
