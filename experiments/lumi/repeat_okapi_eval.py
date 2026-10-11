"""Repeat the frozen external panel on a later dev-selected checkpoint."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import shutil

from okapi_eval import digest, run, summarize


def prepare(root, out, latest=False):
    old = root / "runs/bilingual-all-v1/decision-index-okapi-v1"
    manifest = json.loads((old / "manifest.json").read_text())
    assert digest(old / "rows.jsonl") == manifest["rows_sha256"]
    metrics = json.loads((root / "runs/bilingual-all-v1/full-gold/training_metrics.json").read_text())
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(old / "rows.jsonl", out / "rows.jsonl")
    snapshot_meta = {}
    if latest:
        import torch
        snapshot = out / "snapshot.pt"
        # The trainer uses atomic replacement. Keep this open inode for the copy.
        with (root / "runs/bilingual-all-v1/full-gold/latest.pt").open("rb") as src, snapshot.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        state = torch.load(snapshot, map_location="cpu", weights_only=True)
        metrics["selected_step"] = state["progress"]["step"]
        snapshot_meta = {"snapshot_sha256": digest(snapshot), "snapshot_identity": state["identity"]}
    else:
        shutil.copytree(Path(metrics["selected_path"]), out / "checkpoint")
    baselines = ["results/report.json", "results/decision.jsonl", "results/parent.jsonl",
                 "laya-results/report.json", "laya-results/laya.jsonl"]
    for relative in baselines:
        dst = out / "baselines" / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old / relative, dst)
    previous_runs = {
        "recent": "okapi-checkpoint-review-20261004",
        "prior_latest": "okapi-latest-review-20261004",
    }
    for baseline_name, run_name in previous_runs.items():
        recent = root / "runs/bilingual-all-v1" / run_name / "results"
        if not (recent / "report.json").exists():
            continue
        recent_report = json.loads((recent / "report.json").read_text())
        assert recent_report["status"] == "complete"
        assert recent_report["manifest_sha256"] == digest(recent.parent / "manifest.json")
        assert json.loads((recent.parent / "manifest.json").read_text())["rows_sha256"] == manifest["rows_sha256"]
        for name in ("report.json", "decision.jsonl"):
            relative = baseline_name + "/" + name
            dst = out / "baselines" / relative
            dst.parent.mkdir(exist_ok=True)
            shutil.copy2(recent / name, dst)
            baselines.append(relative)
    assert json.loads((out / "baselines/results/report.json").read_text())["status"] == "complete"
    assert json.loads((out / "baselines/laya-results/report.json").read_text())["status"] == "complete"
    manifest.update(checkpoint_step=metrics["selected_step"],
        checkpoint_selected_by=("most recent atomic recovery snapshot; not selected by benchmark score" if latest else
                                "latest best existing training dev NLL; external benchmark not used"),
        checkpoint_files_sha256={str(p.relative_to(out / "checkpoint")): digest(p)
                                 for p in (out / "checkpoint").rglob("*") if p.is_file()},
        previous_manifest_sha256=digest(old / "manifest.json"),
        baseline_files_sha256={relative: digest(out / "baselines" / relative) for relative in baselines},
        **snapshot_meta)
    code = out / "eval-source"
    code.mkdir()
    for name in ("okapi_eval.py", "repeat_okapi_eval.py"):
        shutil.copy2(Path(__file__).resolve().parent / name, code / name)
    manifest["eval_source_sha256"] = {p.name: digest(p) for p in code.iterdir()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("PREPARED", str(out), "step", manifest["checkpoint_step"], flush=True)


def evaluate(root, out):
    manifest = json.loads((out / "manifest.json").read_text())
    for relative, expected in manifest["baseline_files_sha256"].items():
        assert digest(out / "baselines" / relative) == expected
    for name, expected in manifest["eval_source_sha256"].items():
        assert digest(out / "eval-source" / name) == expected
    if "snapshot_sha256" in manifest:
        import sys
        import torch
        source = root / "runs/bilingual-all-v1/training-source"
        sys.path.insert(0, str(source))
        from decision_model.model import DecisionModel
        assert digest(out / "snapshot.pt") == manifest["snapshot_sha256"]
        state = torch.load(out / "snapshot.pt", map_location="cpu", weights_only=True)
        assert state["identity"] == manifest["snapshot_identity"]
        assert state["progress"]["step"] == manifest["checkpoint_step"]
        identity = state["identity"]
        for name, expected in identity["code_sha256"].items():
            assert digest(source / name) == expected
        assert identity["manifest_sha256"] == manifest["training_manifest_sha256"]
        cfg = identity["recipe"]
        model = DecisionModel.from_parent(cfg["parent"], cfg["revision"], device="cuda", dtype=torch.float32,
                                         lora=cfg["train"]["lora"], head_dim=cfg["train"]["head_dim"])
        params = {name: p for name,p in model.named_parameters() if p.requires_grad}
        assert params.keys() == state["parameters"].keys()
        with torch.no_grad():
            for name,p in params.items():
                p.copy_(state["parameters"][name])
        model.save_run(out / "checkpoint", extra={"step": manifest["checkpoint_step"],
                                                  "snapshot_sha256": manifest["snapshot_sha256"]})
        manifest["checkpoint_files_sha256"] = {str(p.relative_to(out / "checkpoint")): digest(p)
                                                for p in (out / "checkpoint").rglob("*") if p.is_file()}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        del model, params, state
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        print("LATEST_CHECKPOINT_MATERIALIZED", manifest["checkpoint_step"], flush=True)
    run(root, out)
    load = lambda p: [json.loads(x) for x in p.read_text().splitlines()]
    previous = json.loads((out / "baselines/results/report.json").read_text())
    predictions = {
        "decision_current": load(out / "results/decision.jsonl"),
        "decision_previous": load(out / "baselines/results/decision.jsonl"),
        "parent": load(out / "baselines/results/parent.jsonl"),
        "laya": load(out / "baselines/laya-results/laya.jsonl")}
    for baseline_name in ("recent", "prior_latest"):
        recent = out / "baselines" / baseline_name / "report.json"
        if recent.exists():
            recent_step = json.loads(recent.read_text())["checkpoint_step"]
            predictions["decision_step_" + str(recent_step)] = load(recent.parent / "decision.jsonl")
    panel = load(out / "rows.jsonl")
    for rows in predictions.values():
        assert [r["id"] for r in rows] == [r["id"] for r in panel]
        assert all(r["expected"] == p["expected"]["q1"] for r,p in zip(rows, panel))
    supported = set.intersection(*({r["id"] for r in rows if r["status"] == "ok"}
                                   for rows in predictions.values()))
    pairs = defaultdict(list)
    for r in panel:
        pairs[(r["family"], r["pair_id"])].append(r["id"])
    paired = {uid for ids in pairs.values() if len(ids) == 2 and set(ids) <= supported for uid in ids}
    report = {"status": "complete", "current_step": manifest["checkpoint_step"],
        "previous_step": previous["checkpoint_step"], "rows_sha256": manifest["rows_sha256"],
        "full_panel": {name: summarize(rows) for name,rows in predictions.items()},
        "bilingual_common_supported": {name: summarize([r for r in rows if r["id"] in paired])
                                         for name,rows in predictions.items()},
        "limitations": manifest["limitations"] + [
            "Laya's native option limit restricts the common-supported subset",
            "External panel is reused for diagnostics; not a new independent test",
            "Parent and Laya baselines reused from the original frozen evaluation"]}
    report["paired_accuracy_changes"] = {
        name: paired_changes(predictions["decision_current"], rows)
        for name,rows in predictions.items() if name.startswith("decision") and name != "decision_current"}
    (out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print("COMPARISON_COMPLETE", json.dumps(report["full_panel"]["decision_current"]), flush=True)


def paired_changes(current, previous):
    """Bootstrap source pairs together so EN/IT translations are not independent."""
    import numpy as np
    assert [r["id"] for r in current] == [r["id"] for r in previous]
    result = {}
    for language in ("all", "en", "it"):
        groups = defaultdict(list)
        for a,b in zip(current, previous):
            if language != "all" and a["language"] != language:
                continue
            groups[(a["family"], a["pair_id"])].append(int(a["correct"])-int(b["correct"]))
        assert len({len(v) for v in groups.values()}) == 1
        values = np.array([np.mean(v) for v in groups.values()])
        rng = np.random.default_rng(20261004)
        samples = np.array([rng.choice(values, size=len(values), replace=True).mean() for _ in range(10000)])
        result[language] = {"accuracy_delta": float(values.mean()), "bootstrap_95": np.quantile(samples, [.025,.975]).tolist(),
                            "source_pairs": len(values), "resamples": 10000}
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--latest", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare(a.root, a.out, a.latest)
    else:
        evaluate(a.root, a.out)
