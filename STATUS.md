# Research release status

Targets: private Hugging Face `giux78/nev` (v2/ and v3/) and the existing private GitHub repository `mii-llm/nev`.

Both fixed candidates have standalone FP32 exports, merge/reload checks, bilingual evaluation and successful offline inference from an isolated installation of the packaged runtime. The exact evaluated weights are retained. English/Italian training weight is 50/50.

The portable synthetic generator reproduces all eight held-out split hashes. The full base-data rebuild and a portable end-to-end training launcher still require work; historical implementations and dependency assumptions are included. Original testing was on LUMI ROCm. A fresh isolated CUDA environment on an A100 subsequently passed 160 matching FP32 decisions and brief shared-GPU latency checks; the full benchmark suite was not rerun there. No confidence threshold qualified for either variant.

Detailed adapter and export results are kept separate. The original preparation status and failed packaging smoke test remain documented in docs/nesso2/EXPERIMENT_LOG.md. Raw third-party datasets and model binaries are not checked into GitHub; archive inventories and result/provenance JSON are included.

Bilingual A100 reference examples now retain all 32 authored candidates, their v2/v3 outputs and 16 explicitly curated successful requests. Function-name selection is demonstrated with application-supplied arguments and dry-run calls; no argument extraction or tool execution is claimed.

A bounded Nesso2-v2 + Nev agent prototype and both 80-request protocol comparisons are retained. Compact tool schemas with Nev ordering gave a small mechanical-check gain (27/80 vs 23/80); hard top2 fell to 17/80. No reliable agent-level improvement or production readiness is established.

Nesso3 is now the selectable default hybrid generator, pinned at 56f42f1. Eight
simple EN/IT requests were tested in baseline and Nev-ranked modes on the A100:
both passed the same 4/8 strict checks. Four successful curated examples and
all 16 readable/raw traces are retained under docs/nesso3. No broad model gain
or Nev-ranking benefit is claimed from this demonstration set.

A 24-request (12 EN/12 IT), 72-run Nesso3 policy comparison found correct Nev
top1 and Nesso3 first calls on every scoped request. A short prompt was mixed.
An opt-in single_read controller validates/deduplicates calls and formats tool
facts without a second generation: 16/16 reviewed complete fresh answers vs
11/16 baseline, 10/16 prompt. This is application completion, not perfect raw
generation (strict: 12/16 vs 9/16 and 9/16). Its scope must be established by the
application; no general out-of-scope detector was built. All results and audit
are in docs/nesso3; original default and evidence retained.

An opt-in `workflow` entry point now adds a bounded bilingual grammar and
preflights one-to-four explicitly referenced reads before sequential execution.
All 24 single-read regression outputs matched; 8 new single reads and 12 new
multi-step requests completed. All 16 unsupported/out-of-scope cases executed
nothing. 96 total records and audit retained under docs/nesso3. Application code
plans and formats answers; unrestricted phrasing, conditionals and result-driven
arguments remain unsupported. No general planning or model-accuracy claim.

On 2026-10-14, Nesso3 + Nev v3 also ran on an Apple M3 Pro using a custom
CPU-only llama.cpp bridge, F16/Q8 GGUF backbones and Nev's original FP32 head.
F16 retained 24/24 tested Nev decisions; Q8 retained 23/24. On 12 authored
bilingual requests, every backend had 9/10 correct supported plans but only
7/10 reviewed grounded answers and 0/2 correct unsupported-action refusals.
Q8's warm full-request median was 1.89 seconds, versus 4.24 seconds F16 and
3.39 seconds original FP32 CPU. These are small diagnostic measurements,
not broad accuracy or mobile validation. The build recipe, bilingual examples,
raw traces, numerical checks and executable smoke tests are in
`experiments/cpu_gguf/`. The generic agent's known weaknesses remain visible.

CPU weights are distributed independently in private `giux78/nev-gguf` and
`giux78/nesso3-0.4B-agentic-gguf`. Each has standalone instructions; GitHub
documents how to combine the models. The split uses the identical tested
GGUF files, original model revisions and numerical calibration.
