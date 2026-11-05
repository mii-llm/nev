# Q4_0 format follow-up — 5 November 2026

Registered after inspecting quantizer logs and before Q4_0 predictions. The
Q4_K_M quantizer reports 192/290 tensors requiring fallback (many Q5_0) because
of the 960-wide layers, giving 6.39 weight bits on average. Its files are about
341 MiB each. Therefore add Q4_0, whose 32-element blocks fit these dimensions,
quantized directly from the same verified F16 GGUFs with four threads.

Keep the original Q8/Q4_K_M pilot intact. After its four runs, run all 24 routing
cases with Q4_0 selection, then all 24 greenhouse cases with Q4_0 ranking. No
case selection, prompt changes, hybrid models or training. This adds 48 trials,
for 144 total precision trials on the same 48 distinct EN/IT requests. The
Q4_0 runner differs from the original only in admitted precision and the
quantization-record filename. Use the same Q8 baselines, head, tokenizer,
worker settings, memory sampler, metrics and complete trace review.

Q4_0 timing follows the earlier runs rather than being randomized; shared-host
speed results remain illustrative. Compare memory and quality separately. A
4-bit label does not imply a halving of total runtime memory, nor establish a
4 GB device minimum. Record Q4_0 tensor distribution and bits-per-weight from
its quantizer log; metadata and unquantized tensors remain in each GGUF.
