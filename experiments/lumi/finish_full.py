"""Calibrate and export a completed full-data run, then evaluate frozen panels."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch
from decision_model.calibrate import calibrate
from decision_model.data import digest, load_split, write_json, write_jsonl
from decision_model.export import export
from decision_model.model import DecisionModel
from experiments.lumi.run_bilingual_pilot import free, model_rows, summarize


def main(root):
    run = root / "full-gold"
    metrics = json.loads((run / "training_metrics.json").read_text())
    if not metrics["complete"]:
        raise ValueError("Full training is not complete; do not export an intermediate model as final")
    config = json.loads((run / "training_config.json").read_text())
    cfg = config["identity"]["recipe"]
    data = root / "data-reviewed"
    if digest(data / "manifest.json") != config["identity"]["manifest_sha256"]:
        raise ValueError("Data changed since training")
    selected = Path(metrics["selected_path"])
    calibration = calibrate(cfg, selected, data, run / "calibration.json", batch=2)
    calibration.update(selected_dev_nll=metrics["best_nll"],
                       selected_dev_metric="source_language_macro_record_nll on the fixed development sample")
    write_json(run / "calibration.json", calibration)
    print("Calibration complete", flush=True)
    free()
    proof = export(selected, run / "model", calibration=calibration,
        conversion={"experiment": root.name, "mode": "full-gold", "manifest_sha256": digest(data / "manifest.json")},
        dtype=torch.bfloat16, device="cuda", check_requests=[r["request"] for r in load_split(data, "calibration")[:4]])
    free()
    model = DecisionModel.from_pretrained(run / "model", device="cuda")
    panels = {}
    for name, directory, split in (("prior_pilot_test", root.parent / "bilingual-v2/data", "test"),
                                    ("prior_pilot_unseen", root.parent / "bilingual-v2/data", "unseen"),
                                    ("full_test", data, "test"), ("full_unseen", data, "unseen")):
        records = load_split(directory, split)
        rows = model_rows(model, records, temperature=calibration["temperature"])
        write_jsonl(run / f"{name}.jsonl", rows)
        panels[name] = summarize(rows)
        write_json(run / "evaluation-progress.json", panels)
        print(name, json.dumps(panels[name]["by_language"]), flush=True)
    report = {"status": "complete", "mode": "full-gold", "training": metrics, "calibration": calibration,
              "panels": panels, "export_equivalence": proof, "data_manifest_sha256": digest(data / "manifest.json"),
              "limitations": ["Italian is synthetic and only a limited semantic sample was reviewed",
                "All source rows considered, then deduplication, holdout and quality filters; original source-label noise remains",
                "Single seed; no claim of causal comparison with larger released Kev backbones",
                "Final tests use the exported BF16 artifact; no test-based checkpoint or temperature selection"]}
    write_json(run / "report.json", report)
    write_json(run / "model/evaluation.json", report)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    main(ap.parse_args().root)
