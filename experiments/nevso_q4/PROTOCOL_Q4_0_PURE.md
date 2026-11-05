# Pure Q4_0 follow-up — 5 November 2026

The default Q4_0 conversion still upgrades the tied token embedding matrix to
Q6_K, which falls back to Q8_0 for its 960 columns. The log shows one fallback,
293.75 MiB tensor bytes and 5.63 average bits/weight. Register this follow-up
before pure-Q4 predictions to answer the user's four-bit weight question.

Use the same F16 GGUFs with `llama-quantize --pure SOURCE DEST Q4_0 4`.
Pure mode bypasses automatic higher-precision tensor choices; retain FP32 norms
and Nev's external FP32 head. Quantizer logs must confirm the resulting type
mix and fallbacks. Scale overhead means even pure Q4_0 exceeds exactly four
storage bits per parameter.

After default-Q4_0 finishes, evaluate all 48 unchanged requests with the same
preselected strategies and runner, using another separately named precision.
This brings the experiment to 192 precision trials on 48 unique requests.
The admission/manifest filename is the only runner change. No prompt edits,
training, sampling changes, case selection or hybrid pair. Keep every prior
result. This follow-up follows inspection of earlier format logs and some
prior predictions; it is not a fresh independent benchmark. Timings are serial
shared-host observations; no device-size guarantee is implied.
