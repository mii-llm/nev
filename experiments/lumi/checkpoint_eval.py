"""Independent larger-dev checkpoint evaluation without changing the live trainer."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def run(root):
    # Use the exact model, renderer and selection helpers frozen for this run.
    source = root / "training-source"
    sys.path.insert(0, str(source))
    import torch
    from decision_model.data import digest, load_split, write_json, write_jsonl
    from decision_model.model import DecisionModel
    from experiments.lumi.train_full import paired_sample
    from experiments.lumi.run_bilingual_pilot import free, model_rows, summarize

    run_dir = root / "full-gold"
    out = run_dir / "checkpoint-evaluations" / ("job-" + os.environ["SLURM_JOB_ID"])
    out.mkdir(parents=True, exist_ok=False)
    # The trainer replaces latest.pt atomically. An open source inode remains
    # stable even if another checkpoint is renamed into place during this copy.
    snapshot = out / "snapshot.pt"
    with (run_dir / "latest.pt").open("rb") as src, snapshot.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    state = torch.load(snapshot, map_location="cpu", weights_only=True)
    identity = state["identity"]
    cfg = identity["recipe"]
    data = root / "data-reviewed"
    if digest(data / "manifest.json") != identity["manifest_sha256"]:
        raise ValueError("Data differs from checkpoint")
    for name, expected in identity["code_sha256"].items():
        if digest(source / name) != expected:
            raise ValueError("Frozen source differs from checkpoint")
    records = paired_sample(load_split(data, "dev"), 256)
    record_ids = [r["record_id"] for r in records]
    report = {"step": state["progress"]["step"], "snapshot_sha256": digest(snapshot),
              "data_manifest_sha256": identity["manifest_sha256"], "records": len(records),
              "dev_record_ids": record_ids, "panels": {}, "status": "running",
              "numerics": "FP32 weights with BF16 autocast, matching training validation",
              "scope": "Fixed source-stratified dev pairs, up to 256 pairs/source; no test or calibration data",
              "limitations": ["This dev panel overlaps the smaller checkpoint-selection panel",
                              "Metrics are development diagnostics, not an independent final test"]}
    write_json(out / "report.json", report)
    t = cfg["train"]
    for name in ("initial", "checkpoint"):
        if name == "initial":
            model = DecisionModel.from_run(run_dir / "checkpoints/step-0", device="cuda", dtype=torch.float32)
        else:
            model = DecisionModel.from_parent(cfg["parent"], cfg["revision"], device="cuda", dtype=torch.float32,
                lora=t["lora"], head_dim=t["head_dim"])
            params = {k: p for k, p in model.named_parameters() if p.requires_grad}
            if params.keys() != state["parameters"].keys():
                raise ValueError("Checkpoint trainable parameter names differ")
            with torch.no_grad():
                for k, p in params.items():
                    p.copy_(state["parameters"][k])
        model.eval()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            rows = model_rows(model, records)
        report["panels"][name] = summarize(rows)
        write_jsonl(out / f"{name}-dev.jsonl", rows)
        write_json(out / "report.json", report)
        print(name, json.dumps(report["panels"][name]["by_language"]), flush=True)
        del model, rows
        free()
    a, b = report["panels"]["initial"], report["panels"]["checkpoint"]
    report["change"] = {"macro_record_nll": b["source_language_macro_record_nll"] - a["source_language_macro_record_nll"],
                        "accuracy_by_language": {lang: b["by_language"][lang]["accuracy"]-a["by_language"][lang]["accuracy"] for lang in ("en", "it")},
                        "record_nll_by_source": {s:b["by_source_family"][s]["record_mean_nll"]-a["by_source_family"][s]["record_mean_nll"] for s in a["by_source_family"]}}
    report["status"] = "complete"
    write_json(out / "report.json", report)
    print(json.dumps({"step": report["step"], "records": len(records), "change": report["change"]}, indent=2), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    run(ap.parse_args().root)
