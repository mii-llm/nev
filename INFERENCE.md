# Loading the released decision artifacts

Nev's **weights** are hosted on [Hugging Face](https://huggingface.co/mii-llm/nev),
under `v2/` and `v3/`. Its **Python runtime and examples** are in the
[GitHub code repository](https://github.com/mii-llm/nev).
Clone the GitHub repository and run the following with Python 3.12:

```sh
git clone https://github.com/mii-llm/nev.git
cd nev
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "torch>=2.10,<2.11"
python -m pip install -r runtime/requirements-inference.txt
python -m pip install --no-deps ./runtime
python examples/hf_decide.py --variant v3 --language both --device cuda
```

These commands target an NVIDIA GPU; install the appropriate PyTorch build for
other hardware. For Mac CPU inference, use the [GGUF guide](experiments/cpu_gguf/README.md).
The final command downloads the public pinned Hugging Face weights automatically,
then prints English and Italian decisions. No Hugging Face login is needed.
The `decision_model` module is installed from `./runtime` above. Keep the virtual
environment activated and run `examples/` commands from this GitHub checkout.

The requirements record primary tested library versions; they are not a complete
transitive lockfile. Install the hardware-specific PyTorch build first.

The model directory must contain `config.json`, `backbone/`, `tokenizer/`,
`decision_head.safetensors`, `calibration.json` and conversion metadata. Model
weights are in the public Hugging Face repository `mii-llm/nev`, under `v2/` and
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

Download the public model without an HF account:

```python
from pathlib import Path
from huggingface_hub import snapshot_download

variant = "v3"  # or "v2"
folder = Path(snapshot_download("mii-llm/nev", revision="c5c84121263b423f8846811a24790ab96e66cee3", allow_patterns=[f"{variant}/**"])) / variant
print(folder)
```

Pass that folder to `examples/decide.py --model`. For a fixed experiment, set
`revision` to the recorded Hugging Face commit instead of following `main`.

## Quick test on the existing LUMI setup

A ready copy is staged under `/scratch/project_465002563/decision-models/kev-nesso2/releases/publication-nev/demo`.
From a LUMI login shell:

```sh
cd /scratch/project_465002563/decision-models/kev-nesso2/releases/publication-nev/demo
bash examples/lumi_nev.sh fetch v3
sbatch examples/lumi_nev.sbatch --variant v3 --language both
```

The first command downloads the pinned public HF variant into the scratch cache
without an HF login. The job runs
inference offline on one AMD GPU with the frozen runtime. The log path is:

```sh
cat /scratch/project_465002563/decision-models/kev-nesso2/logs/nev-demo-JOBID.log
```

Replace `JOBID` with the number printed by `sbatch`. Check queue status with
`squeue -j JOBID`. The JSON contains the selected `choice` and all option
`probabilities`, separately for English and Italian. This is an inference demo,
not a benchmark score. ROCm uses PyTorch's `cuda` device name on AMD too.

Try your own text against the example's three departments:

```sh
sbatch examples/lumi_nev.sbatch --variant v3 --language it --state "Mi avete addebitato due volte la stessa fattura."
```

To change the decision task and options, edit `examples/request-it.json` (which
contains `state` and `questions`), then pass
`--request /scratch/project_465002563/path/to/request.json` instead of `--state`.
For v2, first run `bash examples/lumi_nev.sh fetch v2`, then use `--variant v2`.
The launcher is specific to this existing LUMI installation. In a different
checkout on LUMI, run `sbatch` from the checkout root so `SLURM_SUBMIT_DIR`
identifies its `runtime/` and `examples/` directories.

## Loading through Transformers

The published release is not registered with Transformers' `AutoModel`. It is
an `nn.Module` with a custom pointer head, typed input renderer and calibration,
and its `from_pretrained` method currently accepts local artifact directories.
Loading only `backbone/` with Transformers omits the trained decision interface.

Direct `AutoModel.from_pretrained` loading is feasible without retraining, by
adding a custom `PreTrainedConfig` / `PreTrainedModel` implementation and Hub
`auto_map` metadata, while preserving the renderer, tokenizer, head and
calibration. That wrapper still needs to be implemented and verified against the
released probabilities. The upstream mechanism is documented in
[Transformers custom models](https://huggingface.co/docs/transformers/en/custom_models).

Today, use `snapshot_download` plus `DecisionModel.from_pretrained`, or the
`examples/hf_decide.py` command, after installing the packaged runtime:

```sh
python examples/hf_decide.py --variant v3 --language both
```

This helper is pinned to the verified model revision and supports `--state`,
`--request`, `--offline` and `--device`. No HF login is required for downloads.

Verified on LUMI: jobs 22720431 (v2) and 22720432 (v3). All four EN/IT
example answers and probabilities exactly match the previous local-export
smoke check. See `docs/nesso2/evidence/hf-demo-results.json`.

## More demanding examples

For multi-question requests, policy boundaries and bilingual one-fact contrast
pairs, use [the scenario runner](examples/SCENARIOS.md). It compares both models
and reports incorrect answers as well as successful ones.
