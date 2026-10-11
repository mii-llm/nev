# Loading the released decision artifacts

Use Python 3.12 and the accompanying frozen runtime. Install a PyTorch build for
your hardware separately; the recorded environment was LUMI ROCm, not a portable
CUDA requirements lock. From this package:

```sh
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime
python examples/decide.py --model /path/to/downloaded/model --language it
```

The requirements record primary tested library versions; they are not a complete
transitive lockfile. Install the hardware-specific PyTorch build first.

The model directory must contain `config.json`, `backbone/`, `tokenizer/`,
`decision_head.safetensors`, `calibration.json` and conversion metadata. Model
weights are in the private Hugging Face repository `giux78/nev`, under `v2/` and
`v3/`; they are not included in this GitHub source package. The same API works for both variants. It supports `choice`, `noul`
(boolean) and `score` (ordinal) questions. Read the artifact's admission limits;
excessively long inputs fail rather than being silently truncated.

This native API example uses the cached serving form in FP32 by default. Published
external subset tables used rows/T=1 under BF16 autocast; practical tables used
packed logits under BF16 autocast. Different arithmetic and execution forms can
change close decisions. Do not interpret the example as a throughput benchmark
or assume its prediction exactly matches every measured configuration.

The stored temperature rescales probabilities; it does not enforce abstention.
Neither candidate has a validated confidence threshold from these experiments.
`top_probability` is not a guarantee that the selected decision is correct.

## Download one variant

Authenticate with a Hugging Face account that has access to `giux78/nev`, then:

```python
from pathlib import Path
from huggingface_hub import snapshot_download

variant = "v3"  # or "v2"
folder = Path(snapshot_download("giux78/nev", allow_patterns=[f"{variant}/**"])) / variant
print(folder)
```

Pass that folder to `examples/decide.py --model`. For a fixed experiment, set
`revision` to the recorded Hugging Face commit instead of following `main`.
