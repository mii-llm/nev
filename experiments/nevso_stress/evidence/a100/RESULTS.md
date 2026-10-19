# Nevso bilingual stress test — automatic results

Run status: **complete**. Recorded **1800/1800 trials**.

Engine: `cuda`; precision: `nesso3_bf16_nev_fp32`.

**These are automatic scores.** BFCL-derived rows measure schema-valid reference calls; workflow scores are completion proxies, not reviewed factual accuracy. Date-format rows use the strict proxy. Three tool orders repeat each request; trial counts are not independent sample sizes.

| Category | Language | Requests | Nesso3 alone | Nev-ranked | Nev-selected |
| --- | --- | ---: | ---: | ---: | ---: |
| confusable | EN | 20 | 7/60 (11.7%) | 28/60 (46.7%) | 41/60 (68.3%) |
| confusable | IT | 20 | 15/60 (25.0%) | 26/60 (43.3%) | 29/60 (48.3%) |
| date_format | EN | 5 | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) |
| date_format | IT | 5 | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) |
| dependent | EN | 10 | 1/30 (3.3%) | 1/30 (3.3%) | 0/30 (0.0%) |
| dependent | IT | 10 | 0/30 (0.0%) | 0/30 (0.0%) | 0/30 (0.0%) |
| direct | EN | 5 | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) |
| direct | IT | 5 | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) |
| external_single | EN | 30 | 19/90 (21.1%) | 15/90 (16.7%) | 16/90 (17.8%) |
| external_single | IT | 30 | 21/90 (23.3%) | 13/90 (14.4%) | 18/90 (20.0%) |
| missing | EN | 15 | 2/45 (4.4%) | 0/45 (0.0%) | 32/45 (71.1%) |
| missing | IT | 15 | 8/45 (17.8%) | 5/45 (11.1%) | 28/45 (62.2%) |
| tool_error | EN | 5 | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) |
| tool_error | IT | 5 | 0/15 (0.0%) | 1/15 (6.7%) | 0/15 (0.0%) |
| unsupported | EN | 10 | 12/30 (40.0%) | 12/30 (40.0%) | 18/30 (60.0%) |
| unsupported | IT | 10 | 3/30 (10.0%) | 4/30 (13.3%) | 21/30 (70.0%) |

## Paired differences versus Nesso3 alone

Percentage-point differences pool EN/IT and cluster resampling by bilingual pair, retaining all tool orders together. Intervals are descriptive and conditional on this selected sample.

| Category | Strategy | Difference | 95% cluster bootstrap interval | Pairs |
| --- | --- | ---: | --- | ---: |
| confusable | nev_ranked | +26.7 pp | [+11.7, +43.3] pp | 20 |
| confusable | nev_selected | +40.0 pp | [+24.2, +56.7] pp | 20 |
| date_format | nev_ranked | +0.0 pp | [+0.0, +0.0] pp | 5 |
| date_format | nev_selected | +0.0 pp | [+0.0, +0.0] pp | 5 |
| dependent | nev_ranked | +0.0 pp | [-5.0, +5.0] pp | 10 |
| dependent | nev_selected | -1.7 pp | [-5.0, +0.0] pp | 10 |
| direct | nev_ranked | +0.0 pp | [+0.0, +0.0] pp | 5 |
| direct | nev_selected | +0.0 pp | [+0.0, +0.0] pp | 5 |
| external_single | nev_ranked | -6.7 pp | [-15.0, +0.6] pp | 30 |
| external_single | nev_selected | -3.3 pp | [-15.6, +7.8] pp | 30 |
| missing | nev_ranked | -5.6 pp | [-11.1, +0.0] pp | 15 |
| missing | nev_selected | +55.6 pp | [+40.0, +71.1] pp | 15 |
| tool_error | nev_ranked | +3.3 pp | [+0.0, +10.0] pp | 5 |
| tool_error | nev_selected | +0.0 pp | [+0.0, +0.0] pp | 5 |
| unsupported | nev_ranked | +1.7 pp | [+0.0, +5.0] pp | 10 |
| unsupported | nev_selected | +40.0 pp | [+18.3, +61.7] pp | 10 |

## Interpretation boundaries

- The selected arm keeps only its initial tool; dependent cases measure that restriction. Ranking is also performed once, not after every observation.
- BFCL-derived API descriptions stay English in both languages. Italian requests are assistant translations. The 30-pair subset is filtered, and training overlap is unknown.
- Workflow checks use lexical assertions. Correct assertions can coexist with invented statements; valid paraphrases can fail. These scores must not be called hallucination-free or independently reviewed task success.
- No live service runs. Error cases are permanent missing-record responses, and clarification cases stop at the first request for information.
- See analysis.json for tool-order stability, rejected-call counts, median latency, and the sensitivity analysis excluding the contradictory BFCL date prompt.
- Shared A100 timings exclude model loading and cannot be presented as Mac Q8 timings.

The frozen protocol and complete raw/readable traces accompany this report.
