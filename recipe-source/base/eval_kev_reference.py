"""Score pinned published Kev models on unchanged Nesso2 pilot test/unseen records.

Uses the reference runtime's renderer, checkpoint loader and exact FP32 row path.
No test labels enter model inputs; shipped temperatures are kept, never refitted.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import digest, load_split, write_json, read_jsonl
from run_bilingual_pilot import approved_data, summarize


def evaluate(root, references, name):
    approved_data(root)
    provenance = json.loads((references / "models.json").read_text())
    identity = provenance["models"][name]
    source = provenance["source"]
    sys.path.insert(0, source["path"])
    import torch
    import transformers
    from kev.api import SystemOneRequest, to_record
    from kev.checkpoint import Checkpoint, LoadOptions
    from kev.model import ContextOverflow

    out = root / "kev-reference" / name
    out.mkdir(parents=True, exist_ok=True)
    config = {
        "identity": identity, "source": source,
        "data_manifest_sha256": digest(root / "data" / "manifest.json"),
        "script_sha256": digest(Path(__file__)),
        "source_file_sha256": {f: digest(Path(source["path"]) / f) for f in
                              ("kev/model.py", "kev/api.py", "kev/checkpoint.py")},
        "dtype": "float32", "merge": True, "attn": "sdpa_math", "autocast": False,
        "temperature": "checkpoint's shipped temperature; no refitting",
        "context": {"max_state": 8192, "max_branch": 8192, "max_packed": 32768},
    }
    cp = out / "config.json"
    if cp.exists():
        assert json.loads(cp.read_text()) == config, "Refusing to mix different evaluation configurations"
    write_json(cp, config)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    started = time.monotonic()
    tok, model = Checkpoint(identity["path"]).load("cuda", LoadOptions(dtype=torch.float32, merge=True,
                                                    attn="sdpa", backend="torch", fused=False, cuda_graphs=False))
    torch.cuda.reset_peak_memory_stats()
    print(name, "loaded", model.dtype, "temperature", model.head.temperature, flush=True)
    panels = {}
    for split in ("test", "unseen"):
        records = load_split(root / "data", split)
        dest = out / f"{split}-predictions.jsonl"
        done = read_jsonl(dest) if dest.exists() else []
        assert [r["record_id"] for r in done] == [r["record_id"] for r in records[:len(done)]]
        with dest.open("a") as stream, torch.inference_mode():
            for i, record in enumerate(records[len(done):], start=len(done)):
                req = SystemOneRequest.model_validate(record["request"])
                internal, meta = to_record(req)
                try:
                    enc = model.encode(tok, internal, max_state=8192, max_branch=8192, strict=True)
                    if len(enc["ids"]) > 32768:
                        raise ContextOverflow("packed record exceeds 32768 tokens")
                    logits = model.forward(enc)
                    assert len(logits) == len(meta)
                    rows = []
                    for m, z in zip(meta, logits):
                        keys, qid = m["keys"], m["id"]
                        p = torch.softmax(z.float(), -1).cpu().tolist()
                        assert len(p) == len(keys) and all(math.isfinite(v) and 0 <= v <= 1 for v in p)
                        assert abs(sum(p) - 1) < 1e-5
                        rows.append({**{k: record[k] for k in ("record_id", "group_id", "language", "source_family")},
                                     "qid": qid, "type": m["type"], "keys": keys,
                                     "label": keys.index(record["supervision"][qid]["gold"]), "probs": p})
                    prediction = {"record_id": record["record_id"], "rows": rows, "input_tokens": len(enc["ids"])}
                except ContextOverflow as error:
                    prediction = {"record_id": record["record_id"], "rows": [], "error": str(error)}
                stream.write(json.dumps(prediction, ensure_ascii=False) + "\n")
                stream.flush()
                done.append(prediction)
                if (i + 1) % 20 == 0 or i + 1 == len(records):
                    print(name, split, f"{i+1}/{len(records)}", f"elapsed={time.monotonic()-started:.1f}s", flush=True)
        assert len(done) == len(records)
        rows = [r for p in done for r in p["rows"]]
        from decision_model.data import write_jsonl
        write_jsonl(out / f"{split}.jsonl", rows)
        panels[split] = {"metrics": summarize(rows), "records_requested": len(records),
                         "rejected": [p for p in done if "error" in p]}
    write_json(out / "report.json", {"status": "complete", "config": config, "panels": panels,
               "wall_seconds": time.monotonic()-started, "peak_device_bytes": torch.cuda.max_memory_allocated(),
               "device": torch.cuda.get_device_name(), "torch": torch.__version__, "transformers": transformers.__version__,
               "temperature": model.head.temperature,
               "limitations": ["Published Kev checkpoints use different, larger training corpora and larger backbones.",
                  "Training overlap with our held-out pool has not been ruled out; inspect official-test and unseen-source panels separately.",
                  "Reference runtime uses FP32 exact inference; Nesso2 pilot metrics use its BF16 export.",
                  "Italian is synthetic. This comparison does not isolate architecture or model size."]})
    print(name, "COMPLETE", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--references", type=Path, required=True)
    ap.add_argument("--name", choices=["kev08b", "kev4b"], required=True)
    a = ap.parse_args()
    evaluate(a.root, a.references, a.name)
