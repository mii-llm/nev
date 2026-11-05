# Nevso Q4 versus Q8 — automatic results

48 reused authored requests, 24 EN + 24 IT, each at Q8, Q4_K_M, Q4_0 and pure Q4_0; 192 trials.

Selection for routing; ranking for greenhouse, fixed before evaluation. CPU only, four threads.
Answer-anchor checks are automatic proxies; review final answers separately. Shared-host timings are illustrative.

| Suite | Precision | Language | Correct calls | Answer proxy | Nev top choice |
| --- | --- | --- | ---: | ---: | ---: |
| routing | q8 | en | 12/12 | 10/12 | 12/12 |
| routing | q8 | it | 9/12 | 8/12 | 10/12 |
| routing | q4_k_m | en | 12/12 | 10/12 | 12/12 |
| routing | q4_k_m | it | 7/12 | 6/12 | 11/12 |
| routing | q4_0 | en | 7/12 | 5/12 | 10/12 |
| routing | q4_0 | it | 8/12 | 4/12 | 9/12 |
| routing | q4_0_pure | en | 7/12 | 3/12 | 10/12 |
| routing | q4_0_pure | it | 8/12 | 5/12 | 9/12 |
| greenhouse | q8 | en | 12/12 | 11/12 | 9/12 |
| greenhouse | q8 | it | 11/12 | 9/12 | 10/12 |
| greenhouse | q4_k_m | en | 12/12 | 11/12 | 10/12 |
| greenhouse | q4_k_m | it | 12/12 | 10/12 | 9/12 |
| greenhouse | q4_0 | en | 11/12 | 9/12 | 11/12 |
| greenhouse | q4_0 | it | 7/12 | 4/12 | 10/12 |
| greenhouse | q4_0_pure | en | 8/12 | 4/12 | 11/12 |
| greenhouse | q4_0_pure | it | 7/12 | 5/12 | 10/12 |

| Suite | Precision | Warm median | Peak summed RSS | Peak PSS | Peak USS |
| --- | --- | ---: | ---: | ---: | ---: |
| routing | q8 | 4.63 s | 2590 MiB | 2576 MiB | 2569 MiB |
| routing | q4_k_m | 4.68 s | 2416 MiB | 2401 MiB | 2393 MiB |
| routing | q4_0 | 5.02 s | 2625 MiB | 2610 MiB | 2603 MiB |
| routing | q4_0_pure | 3.27 s | 2645 MiB | 2631 MiB | 2624 MiB |
| greenhouse | q8 | 10.92 s | 2653 MiB | 2638 MiB | 2631 MiB |
| greenhouse | q4_k_m | 10.92 s | 2466 MiB | 2451 MiB | 2444 MiB |
| greenhouse | q4_0 | 9.23 s | 2679 MiB | 2664 MiB | 2657 MiB |
| greenhouse | q4_0_pure | 7.85 s | 2697 MiB | 2682 MiB | 2675 MiB |

Memory peaks include loading/warmup and the Python/worker process tree, not the OS. PSS apportions shared pages; USS excludes them; RSS can double count. These are sampled observations, not device RAM minima or hard caps.

## Paired changes

- routing / q4_k_m: Nev top-choice agreement 23/24; 4 cases change at least one automatic metric.
- routing / q4_0: Nev top-choice agreement 21/24; 11 cases change at least one automatic metric.
- routing / q4_0_pure: Nev top-choice agreement 21/24; 11 cases change at least one automatic metric.
- greenhouse / q4_k_m: Nev top-choice agreement 22/24; 3 cases change at least one automatic metric.
- greenhouse / q4_0: Nev top-choice agreement 20/24; 12 cases change at least one automatic metric.
- greenhouse / q4_0_pure: Nev top-choice agreement 20/24; 12 cases change at least one automatic metric.
