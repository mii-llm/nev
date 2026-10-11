"""Run a reviewed custom subset with upstream Decision Index; no composite score."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys

try:
    from .prepare_decision_subset import digest, load, save, jsonl
except ImportError:
    from prepare_decision_subset import digest, load, save, jsonl


def check_ready(out, panel, model):
    manifest = json.loads((out / "manifest.json").read_text())
    review = json.loads((out / "quality-review.json").read_text())
    assert "capacity_audit_sha256" in manifest, "Run the CPU capacity/integrity audit first"
    assert digest(out / "capacity-audit.json") == manifest["capacity_audit_sha256"]
    assert review["status"] == "approved_for_diagnostic"
    assert review["panel_sha256"] == manifest["panel_sha256"]
    assert digest(out / (panel + ".jsonl")) == manifest["panel_sha256"][panel]
    if panel == "confirmation":
        decision = json.loads((out / "selection-decision.json").read_text())
        assert decision["selection_sha256"] == manifest["panel_sha256"]["selection"]
        assert model in ("parent", "laya") or model == str(decision["checkpoint_step"])
    for name, expected in manifest["code_sha256"].items():
        assert digest(out / "preparation-source" / name) == expected, name
    for name, expected in manifest["evaluation_files_sha256"].items():
        assert digest(out / "preparation-source" / name) == expected, name
    if model not in ("parent", "laya"):
        for relative, expected in manifest["checkpoint_files_sha256"][model].items():
            assert digest(out / "checkpoints" / model / relative) == expected
    return manifest


def main(root, out, panel, model):
    manifest = check_ready(out, panel, model)
    refs = root / "references/decision-index"
    assert subprocess.check_output(["git", "-C", str(refs), "rev-parse", "HEAD"], text=True).strip() == manifest["decision_index_revision"]
    sys.path.insert(0, str(root / "runs/bilingual-all-v1/training-source"))
    for name, expected in manifest["frozen_runtime_sha256"].items():
        assert digest(root / "runs/bilingual-all-v1/training-source" / name) == expected
    sys.path.insert(0, str(refs))
    from decision_index.runner import run
    destination = out / "results" / panel / model
    destination.mkdir(parents=True, exist_ok=True)
    identity = {"manifest_sha256": digest(out / "manifest.json"),
                "script_sha256": digest(__file__), "engine_sha256": digest(Path(__file__).with_name("decision_subset_engine.py")),
                "panel": panel, "model": model}
    identity_path = destination / "identity.json"
    if identity_path.exists():
        assert json.loads(identity_path.read_text()) == identity, "Cannot resume changed evaluation"
    else:
        save(identity_path, identity)
    if model == "parent":
        meta = json.loads((out / "checkpoints/74000/run.json").read_text())
        engine, options = "transformers", {"model": meta["parent"], "revision": meta["revision"],
                                           "device": "cuda", "dtype": "bfloat16", "cache_prefix": False}
    elif model == "laya":
        engine, options = "decision_subset_engine:LayaEngine", {"root": str(root)}
    else:
        engine, options = "decision_subset_engine:NessoEngine", {"checkpoint": str(out / "checkpoints" / model)}
    run(engine, options, out / (panel + ".jsonl"), destination,
        corpus_sha256=manifest["panel_sha256"][panel], compact=True)
    records = {r["run_id"]: r for r in load(destination / "results.jsonl")}
    cells, predictions = defaultdict(list), []
    rows = load(out / (panel + ".jsonl"))
    assert set(records) == {r["_evaluation"]["run_id"] for r in rows}
    for row in rows:
        result = records[row["_evaluation"]["run_id"]]
        if result["status"] == "error":
            raise RuntimeError("Evaluation has inference errors; inspect upstream results and resume")
        qid, = row["questions"]
        correct = result["status"] == "ok" and result["response"]["answers"][qid]["choice"] == row["expected"][qid]
        prediction = {k: row[k] for k in ("id", "pair_id", "family", "language", "panel")}
        prediction.update(correct=bool(correct), status=result["status"])
        predictions.append(prediction)
        cells[row["family"] + "/" + row["language"]].append(prediction)
    scores = {key: {"n": len(rs), "answered": sum(r["status"] == "ok" for r in rs),
                    "accuracy": sum(r["correct"] for r in rs)/len(rs)} for key, rs in sorted(cells.items())}
    report = {"status": "complete", **identity, "cells": scores,
              "macro_accuracy": sum(v["accuracy"] for v in scores.values()) / len(scores),
              "language_macro_accuracy": {lang: sum(v["accuracy"] for key, v in scores.items() if key.endswith('/'+lang)) /
                                          sum(key.endswith('/'+lang) for key in scores)
                                          for lang in sorted({r["language"] for r in rows})},
              "limitations": manifest["limitations"]}
    save(destination / "report.json", report)
    jsonl(destination / "predictions.jsonl", predictions)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--panel", choices=["selection", "confirmation"], default="selection")
    ap.add_argument("--model", choices=["74000", "142000", "parent", "laya"], required=True)
    args = ap.parse_args()
    main(args.root, args.out, args.panel, args.model)
