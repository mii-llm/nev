# Kev 0.8B versus Nev: saved benchmark comparison

All main models rerun using FP32 native inference; official runtimes require different Torch versions. Same saved inputs, 8k admission, no truncation. These are diagnostic samples, not an official leaderboard. Italian is outside Kev’s declared language scope. Experimental Nev is not a released replacement. No calibration or speed ranking is claimed.

| Task / condition | Language | Common requests | Metric | Kev 0.8B | Nev v2 | Nev v3 | Workflow candidate |
|---|---|---:|---|---:|---:|---:|---:|
| BANKING77 / original | en | 100 | macro-F1 | 71.2% | 54.0% | 53.9% | — |
| CLINC150+OOS / original | en | 100 | macro-F1 | 9.2% | 8.0% | 7.2% | — |
| ANLI / original | en | 100 | macro-F1 | 36.1% | 35.0% | 32.7% | — |
| ARC-Easy / original | en | 100 | accuracy | 86.0% | 55.0% | 57.0% | — |
| ARC-Challenge / original | en | 100 | accuracy | 51.0% | 35.0% | 33.0% | — |
| WinoGrande / original | en | 100 | accuracy | 46.0% | 54.0% | 57.0% | — |
| HellaSwag / original | en | 100 | accuracy | 34.0% | 32.0% | 35.0% | — |
| SATA-Bench / original | en | 100 | case exact accuracy | 8.0% | 2.0% | 0.0% | — |
| FinEntity / original | en | 100 | macro-F1 | 70.7% | 51.6% | 47.1% | — |
| iSarcasmEval / original | en | 100 | sarcastic-class F1 | 38.1% | 16.0% | 10.0% | — |
| VAST / original | en | 100 | macro-F1 | 46.8% | 23.1% | 20.2% | — |
| CLadder / original | en | 100 | accuracy | 42.0% | 47.0% | 49.0% | — |
| MMLU-Pro / original | en | 100 | accuracy | 23.0% | 15.0% | 13.0% | — |
| BBH fixed-option tasks / original | en | 100 | accuracy | 48.0% | 41.0% | 41.0% | — |
| New Yorker caption matching / original | en | 100 | accuracy | 31.0% | 30.0% | 34.0% | — |
| MASSIVE / original | en | 50 | accuracy | 64.0% | 58.0% | 50.0% | — |
| MASSIVE / original | it | 50 | accuracy | 62.0% | 42.0% | 38.0% | — |
| Home appliance simulator / original | en | 25 | case exact accuracy | 0.0% | 0.0% | 0.0% | — |
| API-Bank / described_choices | en | 508 | accuracy | 48.2% | 41.5% | 39.0% | — |
| API-Bank / original | en | 508 | accuracy | 43.7% | 16.7% | 6.1% | — |
| Synthetic next action / unseen_domains | en | 640 | accuracy | 30.3% | 7.5% | 18.9% | 65.2% |
| Synthetic next action / unseen_domains | it | 640 | accuracy | 10.0% | 10.0% | 20.5% | 54.2% |

Full support, per-field accuracy and native metrics are retained in report.json. Workflow rows measure single next actions, not full agent completion. Banking77 is a known training domain; prior benchmark exposure has not been comprehensively audited. No new training or selection was performed.
