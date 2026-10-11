"""Compare actual ROCm training with/without process restart before full launch."""
import json
import sys
from pathlib import Path
import torch

root = Path(sys.argv[1])
a = torch.load(root / "split/latest.pt", map_location="cpu", weights_only=True)
b = torch.load(root / "continuous/latest.pt", map_location="cpu", weights_only=True)
assert a["identity"] == b["identity"]
for key in ("step", "records_seen", "forward_tokens", "selected_step", "best_nll"):
    assert a["progress"][key] == b["progress"][key], key
assert a["progress"]["step"] == 32
delta = max((a["parameters"][k]-v).abs().max().item() for k, v in b["parameters"].items())
assert delta <= 1e-6, delta
assert a["scheduler"] == b["scheduler"]
assert torch.equal(a["torch_rng"], b["torch_rng"])
assert all(torch.equal(x, y) for x, y in zip(a["cuda_rng"], b["cuda_rng"]))
report = {"status": "passed", "step": 32, "max_parameter_delta": delta,
          "records_seen": a["progress"]["records_seen"], "trainable_tensors": len(a["parameters"]),
          "identity": a["identity"], "comparison": "16 updates + process restart + 16 updates versus 32 uninterrupted updates"}
(root / "proof.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k != "identity"}, indent=2))
