# Qwen3-0.6B comparison on the frozen Nevso stress test

Qwen status: **complete**, 600/600 trials. Non-thinking, native tools template, greedy BF16, 192-token output cap.

These are runtime-budget-matched results, not an official BFCL score or a maximum-capability Qwen evaluation. No reasoning tokens or model-specific sampling search were used. Qwen documentation recommends sampling; this run uses greedy decoding to match the existing baseline.

**Do not interpret the raw clarification proxy as successful clarification:** it is known to accept wrong questions and refusals. Nesso3 has separate reviewed labels; Qwen needs the same review before that category is compared substantively.

| Metric | Language | Nesso3 | Nev-ranked + Nesso3 | Nev-selected + Nesso3 | Qwen3-0.6B alone |
| --- | --- | ---: | ---: | ---: | ---: |
| Confusable: correct calls | EN | 17/60 (28.3%) | 40/60 (66.7%) | 56/60 (93.3%) | 44/60 (73.3%) |
| Confusable: correct calls | IT | 23/60 (38.3%) | 44/60 (73.3%) | 43/60 (71.7%) | 45/60 (75.0%) |
| Confusable: answer proxy | EN | 7/60 (11.7%) | 28/60 (46.7%) | 41/60 (68.3%) | 44/60 (73.3%) |
| Confusable: answer proxy | IT | 15/60 (25.0%) | 26/60 (43.3%) | 29/60 (48.3%) | 43/60 (71.7%) |
| BFCL-derived: correct calls | EN | 19/90 (21.1%) | 15/90 (16.7%) | 16/90 (17.8%) | 45/90 (50.0%) |
| BFCL-derived: correct calls | IT | 21/90 (23.3%) | 13/90 (14.4%) | 18/90 (20.0%) | 43/90 (47.8%) |
| Missing input: RAW clarification proxy | EN | 2/45 (4.4%) | 0/45 (0.0%) | 32/45 (71.1%) | 20/45 (44.4%) |
| Missing input: RAW clarification proxy | IT | 8/45 (17.8%) | 5/45 (11.1%) | 28/45 (62.2%) | 1/45 (2.2%) |
| Dependent: completion proxy | EN | 1/30 (3.3%) | 1/30 (3.3%) | 0/30 (0.0%) | 0/30 (0.0%) |
| Dependent: completion proxy | IT | 0/30 (0.0%) | 0/30 (0.0%) | 0/30 (0.0%) | 0/30 (0.0%) |
| Unsupported: behavior proxy | EN | 12/30 (40.0%) | 12/30 (40.0%) | 18/30 (60.0%) | 18/30 (60.0%) |
| Unsupported: behavior proxy | IT | 3/30 (10.0%) | 4/30 (13.3%) | 21/30 (70.0%) | 3/30 (10.0%) |
| Direct: exact answer, no calls | EN | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) | 4/15 (26.7%) |
| Direct: exact answer, no calls | IT | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) | 4/15 (26.7%) |
| Tool error: completion proxy | EN | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) | 10/15 (66.7%) |
| Tool error: completion proxy | IT | 0/15 (0.0%) | 1/15 (6.7%) | 0/15 (0.0%) | 3/15 (20.0%) |
| Date: exact requested format | EN | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) | 1/15 (6.7%) |
| Date: exact requested format | IT | 0/15 (0.0%) | 0/15 (0.0%) | 0/15 (0.0%) | 7/15 (46.7%) |

Each language has 100 requests, each repeated with three seeded tool-order draws. Trial counts are correlated. Both runs use the same controller, fixtures, scoring and output cap, but each generator uses its native chat/tool template. The selected Nesso3 arm has one tool; standalone Qwen sees the full catalog.

Correct calls and complete answers are different metrics. Answer assertions are proxies, not a factual audit. The initial single-tool strategy cannot perform a second distinct tool call. BFCL training overlap is unknown. No blanket model ranking or causal size claim follows from these small panels.
