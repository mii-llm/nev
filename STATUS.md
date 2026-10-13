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
