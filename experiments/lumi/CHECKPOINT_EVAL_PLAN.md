# Full-data learning checks

This plan uses development data only. The final test panels remain reserved for
the selected model after training. The live trainer and its resume identity stay
unchanged; additional diagnostics run on a separate GPU and a copied checkpoint.

## Automatic checks already running

- Recovery snapshot every 500 updates, about 17 minutes at the measured rate.
- Fixed 1,082-record development evaluation every 2,000 updates (about 69 minutes)
  and at epoch boundaries. Tracks source/language macro record NLL, micro question
  accuracy, and all 18 source/language NLL cells. Saves each improving model.
- Finite loss and gradient checks on every optimizer update.

## Larger development evaluation

`checkpoint_eval.sbatch` copies one atomic `latest.pt` snapshot and compares it
against the exact step-zero model on a fixed development sample of up to 256
parallel pairs per source (4,154 records). It reports EN/IT accuracy separately,
per-source accuracy and NLL, macro record NLL, and per-question predictions.
This panel overlaps the smaller selection panel; it is not an independent test.
The first such evaluation is submitted now. Future larger runs are proposed at
the review points below; the trainer's normal 2,000-update checks are automatic.

## Decision points

| Point | Update | Decision |
|---|---:|---|
| Early trend | 4,000 and 10,000 | Compare consecutive validations; do not infer a trend from isolated eight-record batches. |
| End of warm-up | approximately 17,830–18,000 | Require sustained macro NLL improvement over step zero and inspect both languages and each source. If still flat, diagnose LR, label alignment and delimiter representations before committing the remaining budget. |
| Half of epoch one | approximately 44,575 | Check whether improvements extend beyond AG News and the dominant MNLI source; assess EN/IT divergence. |
| Epoch one end | 89,150 | Compare with earlier checkpoints; if validation deteriorates despite lower training loss, investigate overfitting before continuing unchanged. |
| Epoch two end | 178,300 | Calibrate and evaluate the selected checkpoint on the reserved final panels. |

Do not automatically stop or change learning rate on a single noisy validation.
Three successive increases in macro dev NLL, any sustained language-specific
regression, or no improvement by the end of warm-up require investigation. These
are review criteria, not new automatic early-stopping rules in the live trainer.

## October 1 measurement

At 13:45 UTC: update 3,550/178,300, about 2% complete. Median training time is
2.016 seconds/update; the first periodic dev evaluation adds about 103 seconds.
Extrapolating both gives approximately 100.4 hours of training remaining, excluding
future queue waits and final calibration/export/evaluation. A practical range is
100–105 compute hours remaining. This is a throughput estimate, not a guaranteed
completion date. Warm-up ends roughly eight hours after this measurement.

Logged batch-loss samples (one eight-record update every 50 steps) have means
1.1512 for the first 20 samples and 1.1525 for the latest 20. These are sampled
batch losses, not full-window or full-corpus averages, and show no clear decrease.
Dev macro NLL is 1.48393 at step zero and 1.48413 at step 2,000; micro accuracy
rose from 35.15% to 38.24%. AG News improved, while BoolQ NLL worsened. The evidence
is mixed, and the selected checkpoint at that measurement is still step zero.
