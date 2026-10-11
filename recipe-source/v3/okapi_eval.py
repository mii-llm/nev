"""Small external diagnostic using Decision Index engines and paired Okapi rows."""
import argparse
from collections import defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wilson(correct, total):
    p, z = correct / total, 1.959963984540054
    center = (p + z*z/(2*total)) / (1+z*z/total)
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1+z*z/total)
    return [center-half, center+half]


def metrics(rows):
    n = len(rows)
    ok = [r for r in rows if r["status"] == "ok"]
    correct = sum(r.get("correct", False) for r in rows)
    chance = sum(1/r["options"] for r in rows)/n
    return {"n": n, "answered": len(ok), "errors_or_unsupported": n-len(ok),
            "accuracy": correct/n, "accuracy_wilson_95": wilson(correct, n),
            "chance": chance, "chance_corrected": max(0., (correct/n-chance)/(1-chance)),
            "nll_answered": sum(r["nll"] for r in ok)/len(ok) if ok else None}


def summarize(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[r["family"] + "/" + r["language"]].append(r)
    return {key: metrics(value) for key, value in sorted(cells.items())}


def run(root, out, smoke=False):
    source = root / "runs/bilingual-all-v1/training-source"
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(root / "references/decision-index"))
    import torch
    from decision_index.engines import Engine, Unsupported, validate
    from decision_index.engines.transformers_engine import TransformersEngine
    from decision_model.model import DecisionModel
    from decision_model.render import to_record
    from decision_model.schema import DecisionRequest, AdmissionError

    class NessoDecisionEngine(Engine):
        name = "nesso-decision"

        def __init__(self):
            self.model = DecisionModel.from_run(out / "checkpoint", device="cuda", dtype=torch.float32)

        def __call__(self, state, questions):
            if any(q["type"] != "choice" for q in questions.values()):
                raise Unsupported("This diagnostic adapter supports choice questions")
            req = DecisionRequest.model_validate({"state": state, "questions": questions})
            rec, meta = to_record(req)
            try:
                enc = self.model.encode(rec)
            except AdmissionError as error:
                raise Unsupported(str(error)) from error
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                ps = self.model.probs(enc, form="rows", temperature=1.0)
            answers = {}
            for m, p in zip(meta, ps):
                probabilities = dict(zip(m["keys"], map(float, p)))
                answers[m["id"]] = {"type": "choice", "choice": max(probabilities, key=probabilities.get),
                                     "probabilities": probabilities}
            return {"model": self.name, "answers": answers, "usage": {"input_tokens": len(enc["ids"])}}, None

    manifest = json.loads((out / "manifest.json").read_text())
    assert digest(out / "rows.jsonl") == manifest["rows_sha256"]
    for name, expected in manifest["checkpoint_files_sha256"].items():
        assert digest(out / "checkpoint" / name) == expected
    import subprocess
    for repo, expected in manifest["repositories"].items():
        assert subprocess.check_output(["git", "-C", str(root / "references" / repo), "rev-parse", "HEAD"], text=True).strip() == expected
    rows = [json.loads(x) for x in (out / "rows.jsonl").read_text().splitlines()]
    if smoke:
        seen, selected = defaultdict(int), []
        for row in rows:
            key = row["family"], row["language"]
            if seen[key] < 2:
                selected.append(row)
                seen[key] += 1
        rows = selected
    run_dir = out / ("smoke" if smoke else "results")
    run_dir.mkdir(exist_ok=False)
    report = {"status": "running", "checkpoint_step": manifest["checkpoint_step"],
              "manifest_sha256": digest(out / "manifest.json"), "script_sha256": digest(__file__),
              "records_per_model": len(rows), "panels": {}, "limitations": manifest["limitations"],
              "numerics": {"decision": "FP32 weights, BF16 autocast, T=1 (uncalibrated)",
                           "parent": "Decision Index stock TransformersEngine, BF16, option-key log likelihood, fixed chat prompt"},
              "torch": torch.__version__, "gpu": torch.cuda.get_device_name(),
              "frozen_runtime_sha256": {str(p.relative_to(source)): digest(p) for p in (source / "decision_model").rglob("*.py")}}
    save = lambda: (run_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    cp = json.loads((out / "checkpoint/run.json").read_text())
    for name in ("decision", "parent"):
        engine = NessoDecisionEngine() if name == "decision" else TransformersEngine(
            model=cp["parent"], revision=cp["revision"], device="cuda", dtype="bfloat16", cache_prefix=False)
        engine.warmup()
        predictions, start = [], time.monotonic()
        with (run_dir / (name + ".jsonl")).open("w") as stream:
            for i, row in enumerate(rows):
                keys = list(row["questions"]["q1"]["criteria"])
                result = {k: row[k] for k in ("id", "pair_id", "family", "language", "subject")}
                result.update(options=len(keys), expected=row["expected"]["q1"])
                torch.cuda.synchronize()
                t0 = time.monotonic()
                try:
                    # Only state/questions enter the engine, never expected/provenance.
                    response, raw = engine(row["state"], row["questions"])
                    validate(row["questions"], response)
                    a = response["answers"]["q1"]
                    result.update(status="ok", response=response,
                        correct=a["choice"] == result["expected"],
                        nll=-math.log(max(a["probabilities"][result["expected"]], 1e-12)))
                except Unsupported as error:
                    result.update(status="unsupported", error=str(error), correct=False)
                torch.cuda.synchronize()
                result["wall_ms"] = 1000*(time.monotonic()-t0)
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                predictions.append(result)
                if (i+1) % 100 == 0 or i+1 == len(rows):
                    print(name, i+1, "/", len(rows), "seconds", round(time.monotonic()-start, 1), flush=True)
        report["panels"][name] = summarize(predictions)
        save()
        print(name, json.dumps(report["panels"][name]), flush=True)
        del engine
        gc.collect()
        torch.cuda.empty_cache()
    report["accuracy_delta_decision_minus_parent"] = {
        k: v["accuracy"]-report["panels"]["parent"][k]["accuracy"] for k,v in report["panels"]["decision"].items()}
    report["status"] = "complete"
    save()
    print("COMPLETE", str(run_dir / "report.json"), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    run(a.root, a.out, a.smoke)
