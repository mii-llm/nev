"""Compare teachers on dev, then train/evaluate paired bilingual experiments.

The gold-only control and distilled model use the same seed, data and schedule.
Test/unseen never select the teacher, checkpoint or calibration temperature.
"""
import argparse
import copy
import gc
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import digest, load_split, write_json, write_jsonl
from decision_model.schema import DecisionRequest, question_keys


def approved_data(root):
    review = json.loads((root / "data" / "quality-review.json").read_text())
    assert review["status"] == "approved_for_pilot", "Translation review has not approved this pilot corpus"
    assert review["manifest_sha256"] == digest(root / "data" / "manifest.json"), "Data changed after translation review"


def stats(rows):
    if not rows:
        return {"questions": 0}
    nll, correct, brier, masses = [], [], [], []
    bins = [[] for _ in range(10)]
    per_record = defaultdict(list)
    for r in rows:
        p, y = r["probs"], r["label"]
        pred = max(range(len(p)), key=p.__getitem__)
        loss = -math.log(max(p[y], 1e-12))
        nll.append(loss)
        correct.append(int(pred == y))
        per_record[r["record_id"]].append(loss)
        brier.append(sum((v - int(i == y)) ** 2 for i, v in enumerate(p)))
        bins[min(9, int(p[pred] * 10))].append((p[pred], int(pred == y)))
        if r.get("mass_on_labels") is not None:
            masses.append(r["mass_on_labels"])
    mean = lambda xs: sum(xs) / len(xs)
    return {"questions": len(rows), "records": len(per_record), "accuracy": mean(correct), "nll": mean(nll),
            "record_mean_nll": mean([mean(v) for v in per_record.values()]), "brier": mean(brier),
            "ece_10": sum(abs(sum(p - y for p, y in b)) for b in bins) / len(rows),
            "mean_mass_on_labels": mean(masses) if masses else None}


def summarize(rows):
    out = {"overall": stats(rows)}
    for dim in ("language", "source_family", "type"):
        out["by_" + dim] = {k: stats([r for r in rows if r[dim] == k]) for k in sorted({r[dim] for r in rows})}
    cells = {(r["language"], r["source_family"]) for r in rows}
    out["source_language_macro_record_nll"] = sum(stats([r for r in rows if (r["language"], r["source_family"]) == k])["record_mean_nll"] for k in cells) / len(cells)
    return out


def teacher_rows(scorer, records):
    rows, skipped = [], []
    for start in range(0, len(records), 32):
        part = records[start:start + 32]
        details = scorer.score_many([DecisionRequest.model_validate(r["request"]) for r in part], "cyclic")
        for r, d in zip(part, details):
            for qid, value in d.items():
                base = {k: r[k] for k in ("record_id", "group_id", "language", "source_family")}
                base.update(qid=qid, type=r["request"]["questions"][qid]["type"])
                if not value["eligible"]:
                    skipped.append({**base, "reason": value["reason"]})
                    continue
                keys = list(value["probs"])
                rows.append({**base, "keys": keys, "label": keys.index(r["supervision"][qid]["gold"]),
                             "probs": list(value["probs"].values()), "mass_on_labels": value["mass_on_labels"]})
        print(f"teacher evaluation: {start + len(part)}/{len(records)}", flush=True)
    return rows, skipped


def free():
    import torch
    gc.collect()
    torch.cuda.empty_cache()


def compare(root, configs):
    approved_data(root)
    from decision_model.targets import ParentScorer, collect
    out = root / "comparison"
    out.mkdir(exist_ok=True)
    cfg = json.loads((root / "base-recipe.json").read_text())
    cfg["data"]["out"] = str(root / "data")
    cfg["teacher"]["out"] = str(root / "targets")
    records = load_split(root / "data", "dev")
    results, identities, row_sets = {}, {}, {}
    for name, path in configs.items():
        identity = json.loads(path.read_text())
        identities[name] = identity
        scorer = ParentScorer(identity["model"], identity["revision"], device="cuda", batch_tokens=4096)
        rows, skipped = teacher_rows(scorer, records)
        row_sets[name] = {(r["record_id"], r["qid"]) for r in rows}
        results[name] = {"identity": identity, **summarize(rows), "ineligible": dict(Counter(r["reason"] for r in skipped))}
        write_jsonl(out / f"{name}-dev.jsonl", rows)
        write_jsonl(out / f"{name}-ineligible.jsonl", skipped)
        del scorer
        free()
    assert len({frozenset(s) for s in row_sets.values()}) == 1, "Teachers must cover the same questions"
    selected = min(results, key=lambda k: results[k]["source_language_macro_record_nll"])
    report = {"selected": selected, "selection": "minimum dev NLL, mean within record, then equally across source/language cells",
              "data_manifest_sha256": digest(root / "data" / "manifest.json"), "results": results,
              "limitations": ["Pilot-sized dev set; selection is provisional.",
                 "Italian is machine translated; translation quality and style can bias the comparison.",
                 "Only the common eligible question set is compared; 77-option Banking77 is excluded."]}
    write_json(out / "selection.json", report)
    cfg["teacher"].update(identities[selected])
    write_json(root / "selected-recipe.json", cfg)
    print(json.dumps(report, indent=2), flush=True)
    path, meta = collect(cfg, device="cuda", chunk=64)
    assert meta["complete"]
    write_json(out / "targets-complete.json", {"path": str(path), "metadata": meta})


def model_rows(model, records, temperature=1.0):
    import torch
    from decision_model.render import to_record
    rows = []
    with torch.inference_mode():
        for start in range(0, len(records), 2):
            part = records[start:start + 2]
            requests = [DecisionRequest.model_validate(r["request"]) for r in part]
            encs = [model.encode(to_record(req)[0]) for req in requests]
            logits = model.forward_batch(encs, form="packed")
            for r, req, zs in zip(part, requests, logits):
                for (qid, q), z in zip(req.questions.items(), zs):
                    keys = question_keys(q.type, q.criteria)
                    p = torch.softmax(z.float() / temperature, -1).cpu().tolist()
                    rows.append({**{k: r[k] for k in ("record_id", "group_id", "language", "source_family")},
                                 "qid": qid, "type": q.type, "keys": keys, "probs": p,
                                 "label": keys.index(r["supervision"][qid]["gold"])})
    return rows


def train_run(root, mode):
    approved_data(root)
    import torch
    from decision_model.targets import collection_path
    from decision_model.train import train
    from decision_model.calibrate import calibrate
    from decision_model.export import MEASURED_END, MEASURED_START, export
    from decision_model.model import DecisionModel
    cfg = json.loads((root / "selected-recipe.json").read_text())
    selection = json.loads((root / "comparison" / "selection.json").read_text())
    assert selection["data_manifest_sha256"] == digest(root / "data" / "manifest.json")
    out = root / mode
    out.mkdir(exist_ok=True)
    targets = collection_path(cfg) if mode == "distilled" else None
    if targets is None:
        cfg["train"]["gold_weight"] = 1.0
    write_json(out / "recipe.json", cfg)
    metrics = train(cfg, root / "data", targets, out / "train", device="cuda")
    assert metrics["complete"]
    free()
    calibration = calibrate(cfg, out / "train" / "selected", root / "data", out / "calibration.json", batch=2)
    free()
    equivalence = export(out / "train" / "selected", out / "model", calibration=calibration,
                         conversion={"experiment": root.name, "mode": mode,
                                     "teacher": cfg["teacher"] if mode == "distilled" else None,
                                     "manifest_sha256": digest(root / "data" / "manifest.json")},
                         dtype=torch.bfloat16, device="cuda",
                         check_requests=[r["request"] for r in load_split(root / "data", "calibration")[:4]])
    free()
    model = DecisionModel.from_pretrained(out / "model", device="cuda")
    panels = {}
    for split in ("dev", "test", "unseen"):
        records = load_split(root / "data", split)
        raw = model_rows(model, records)
        # Reuse raw probabilities to apply the same scalar temperature without another model pass.
        calibrated = copy.deepcopy(raw)
        for r in calibrated:
            z = [math.log(max(p, 1e-30)) / calibration["temperature"] for p in r["probs"]]
            p = [math.exp(v - max(z)) for v in z]
            r["probs"] = [v / sum(p) for v in p]
        write_jsonl(out / f"{split}-raw.jsonl", raw)
        write_jsonl(out / f"{split}-calibrated.jsonl", calibrated)
        panels[split] = {"raw": summarize(raw), "calibrated": summarize(calibrated)}
    report = {"mode": mode, "training": metrics, "calibration": calibration, "panels": panels,
              "export_equivalence": equivalence, "status": "complete",
              "limitations": ["Small pilot, synthetic Italian, single seed; not a production quality claim.",
                              "Calibration is fitted on FP32 weights with BF16 autocast; reported tests use the exported BF16 artifact."]}
    write_json(out / "report.json", report)
    write_json(out / "model" / "evaluation.json", {"experiment": root.name, "mode": mode,
               "data_manifest_sha256": digest(root / "data" / "manifest.json"), "panels": panels,
               "limitations": report["limitations"]})
    lines = ["Pilot evaluation of this exported BF16 artifact, using the fitted scalar temperature.", "",
             "Equal Italian/English records; machine-translated Italian; one seed. Not a production validation.", "",
             "| Panel | Language | Questions | Accuracy | NLL | ECE |",
             "|---|---|---:|---:|---:|---:|"]
    for split, panel in panels.items():
        for lang, s in panel["calibrated"]["by_language"].items():
            lines.append(f"| {split} | {lang} | {s['questions']} | {s['accuracy']:.3f} | {s['nll']:.3f} | {s['ece_10']:.3f} |")
    card = out / "model" / "README.md"
    before, rest = card.read_text().split(MEASURED_START, 1)
    _, after = rest.split(MEASURED_END, 1)
    card.write_text(before + MEASURED_START + "\n" + "\n".join(lines) + "\n" + MEASURED_END + after)
    print(json.dumps({"mode": mode, "status": "complete", "panels": panels}, indent=2), flush=True)


def baselines(root):
    approved_data(root)
    from decision_model.targets import ParentScorer
    from probe import PARENT, REVISION
    cfg = json.loads((root / "selected-recipe.json").read_text())
    out = root / "baselines"
    out.mkdir(exist_ok=True)
    reports = {}
    for name, identity in (("original_nesso2", {"model": PARENT, "revision": REVISION}),
                           ("selected_teacher", cfg["teacher"])):
        scorer = ParentScorer(identity["model"], identity["revision"], device="cuda", batch_tokens=4096)
        reports[name] = {}
        for split in ("test", "unseen"):
            rows, skipped = teacher_rows(scorer, load_split(root / "data", split))
            write_jsonl(out / f"{name}-{split}.jsonl", rows)
            reports[name][split] = {**summarize(rows), "ineligible": dict(Counter(r["reason"] for r in skipped))}
        del scorer
        free()
    write_json(out / "report.json", reports)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["compare", "distilled", "gold", "baselines"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--configs", type=Path, required=True)
    a = ap.parse_args()
    if a.stage == "compare":
        compare(a.root, {"qwen3_4b": a.configs / "teacher-qwen3-4b.json", "nesso4b": a.configs / "teacher-nesso4b.json"})
    elif a.stage == "baselines":
        baselines(a.root)
    else:
        train_run(a.root, a.stage)
