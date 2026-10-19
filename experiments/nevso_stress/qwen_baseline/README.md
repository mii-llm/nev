# Qwen3-0.6B comparison

**Completed: all 600 trials in 11 minutes 29 seconds.** Qwen alone was
evaluated on the same 200 requests and three tool-order draws. Read the
**[comparison and trace review](REVIEW.md)**, including the clarification audit.
The separate four-trial pilot completed successfully on the A100.

The [protocol](PROTOCOL.md) pins the model revision, native tool template and
runtime budget. Qwen uses BF16, thinking disabled and greedy generation with the
same 192-token cap and controller as the Nesso3 test. The dataset and original
scores are unchanged. This measures the specified serving setup, not Qwen's
maximum thinking-mode performance.

The runner saves raw completions and readable traces incrementally and produces
`COMPARISON.md` on completion, including Nesso3 alone, both Nev + Nesso3 arms, and
Qwen alone. The completed clarification trace review is reported separately from the raw
proxy scores, using the same principle as the Nesso review. We have not tested Nev + Qwen here.

See [how to read the existing results](../EXPLAINED.md) for the distinction
between tool calls and completed answers.
