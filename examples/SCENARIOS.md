# Bilingual decision scenarios

The original three-department parcel example is a loading smoke test. It does
not establish useful reasoning or reliable confidence. This separate diagnostic
asks four simultaneous decisions on messages with distracting secondary topics:
route, refund eligibility, urgency (three levels), and supervisor escalation.
Each request supplies explicit synthetic shop policies and verified facts.

There are five pairs in each language. Only one verified fact changes within a
pair; customer wording and policy stay fixed:

| Pair | Changed fact | Expected change |
|---|---|---|
| Return window | Delivered 29 vs 31 days ago | Refund approved vs rejected |
| Security override | Unauthorized account activity unconfirmed vs confirmed | Account vs security route; routine vs urgent; no escalation vs escalation |
| Duplicate reimbursement | Duplicate charge not yet refunded vs already refunded | Refund approved vs rejected |
| Delivery deadline | 25 vs 23 hours remaining | Priority vs urgent |
| Repeat contact | 2 vs 3 unsuccessful previous contacts | No escalation vs escalation |

`scenarios.json` contains the full EN/IT requests and explicit answer keys.
`build_scenarios.py` recreates it and cross-checks those keys with executable
rules. The runner passes only each `request` to the model, never the answer key,
case identifier or contrast-pair metadata. Examples were authored for this check;
they are not a representative benchmark and were not used to train these models.
They are conceptually similar to practical tasks in training. Results cannot
establish broad generalization, confidence calibration or production suitability.

## Run on the existing LUMI installation

```sh
cd /scratch/project_465002563/decision-models/kev-nesso2/releases/publication-nev/demo
# Already cached during the release check; safe to repeat if necessary.
bash examples/lumi_nev.sh fetch v2
bash examples/lumi_nev.sh fetch v3
sbatch examples/lumi_scenarios.sbatch
```

The job loads each model once, does a warmup, then tests all 20 requests (80
individual decisions per model). It prints every predicted answer, its assigned
probability, the expected answer, and whether it was correct. It also reports
per-task EN/IT counts and whether decisions respond correctly to the changed
fact on both sides. Scores use the actual native boolean/ordinal decision API.

Read the outputs using the returned job ID:

```sh
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.log
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-scenarios-JOBID.json
```

To run only one variant, add `--variants v3`. For a single editable complex
Italian request containing all four decisions:

```sh
sbatch examples/lumi_nev.sbatch --variant v3 --request examples/request-complex-it.json
```

That uses the ordinary `nev-demo-JOBID.log` filename. Edit the request's customer
message, verified facts, and question policies to explore your own decisions.
A high probability on a wrong decision is retained in the report, not filtered
out. The first-call latency includes warmup; this script is not a latency study.

The completed run is documented in [SCENARIO_RESULTS.md](../SCENARIO_RESULTS.md),
including all failures and the always-no baseline.
