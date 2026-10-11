"""Cache pinned published Kev adapters and their exact base revisions on LUMI."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from huggingface_hub import snapshot_download

MODELS = {
    "kev08b": ("jaredpalmer/kev-0.8b", "9a45d25eb2ab761841196625383fa1dff0e56c1e"),
    "kev4b": ("jaredpalmer/kev-4b", "139fdd94f1b6a6ad80cc15e08fcb99cac885a101"),
}


def main(root):
    source = json.loads((root / "source.json").read_text())
    result = {"source": source, "models": {}}
    for name, (repo, revision) in MODELS.items():
        path = Path(snapshot_download(repo, revision=revision,
                    allow_patterns=["*.json", "*.safetensors", "*.pt", "*.txt", "*.jinja", "README.md"], max_workers=4))
        meta = torch.load(path / "head.pt", map_location="cpu", weights_only=True)
        base, base_revision = meta["base"], meta["base_revision"]
        assert base_revision and len(base_revision) == 40
        print(name, "adapter cached; downloading", base, base_revision, flush=True)
        base_path = snapshot_download(base, revision=base_revision,
                    allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "LICENSE"], max_workers=4)
        result["models"][name] = {
            "model": repo, "revision": revision, "path": str(path), "base": base,
            "base_revision": base_revision, "base_path": str(base_path),
            "temperature": meta.get("temperature", 1.0),
            "head_sha256": hashlib.sha256((path / "head.pt").read_bytes()).hexdigest(),
            "adapter_sha256": hashlib.sha256((path / "adapter_model.safetensors").read_bytes()).hexdigest(),
        }
        (root / "models.json").write_text(json.dumps(result, indent=2) + "\n")
        print(name, "ready", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    main(ap.parse_args().root)
