"""Frozen-panel comparison of the selected practical-v2 candidate and Laya.

Reuses verified old predictions, scores only missing model/panel combinations,
and reports identical bilingual common-support subsets as well as full panels.
"""
import argparse
from collections import defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]


def save(p, obj):
    p = Path(p)
    temp = p.with_suffix(p.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temp.replace(p)


def metric(rows):
    if not rows:
        return {"n": 0, "answered": 0, "accuracy": None}
    return {"n": len(rows), "answered": sum(r["status"] == "ok" for r in rows),
            "correct": sum(bool(r["correct"]) for r in rows),
            "accuracy": sum(bool(r["correct"]) for r in rows)/len(rows),
            "chance": sum(1/r["options"] for r in rows)/len(rows)}


def summarize(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[r["family"] + "/" + r["language"]].append(r)
    per_cell = {k: metric(v) for k,v in sorted(cells.items())}
    by_language = {}
    for lang in ("en", "it"):
        m = metric([r for r in rows if r["language"] == lang])
        cell_metrics = [v for k,v in per_cell.items() if k.endswith("/" + lang)]
        m["task_macro_accuracy"] = sum(v["accuracy"] for v in cell_metrics)/len(cell_metrics) if cell_metrics else None
        by_language[lang] = m
    return {"overall": metric(rows), "by_language": by_language, "cells": per_cell}


def common_panel(predictions):
    reference = next(iter(predictions.values()))
    ids = [r["id"] for r in reference]
    expected = {r["id"]: (r["expected"], r["family"], r["language"], r["pair_id"]) for r in reference}
    supported = set(ids)
    for rows in predictions.values():
        assert len(rows) == len({r["id"] for r in rows}) == len(ids), "Duplicate or missing IDs"
        assert {r["id"]: (r["expected"], r["family"], r["language"], r["pair_id"]) for r in rows} == expected, "Different input/gold alignment"
        supported &= {r["id"] for r in rows if r["status"] == "ok"}
    pairs = defaultdict(list)
    for r in reference:
        pairs[(r["family"], r["pair_id"])].append(r)
    assert all(len(rs) == 2 and {r["language"] for r in rs} == {"en", "it"} for rs in pairs.values())
    matched = {r["id"] for rs in pairs.values() if {r["id"] for r in rs} <= supported for r in rs}
    return {"full": {m: summarize(rows) for m,rows in predictions.items()},
            "common_bilingual": {m: summarize([r for r in rows if r["id"] in matched]) for m,rows in predictions.items()},
            "common_bilingual_requests": len(matched), "full_requests": len(reference),
            "common_ids_sha256": hashlib.sha256("\n".join(sorted(matched)).encode()).hexdigest()}


def external_meta(row):
    qid, = row["questions"]
    return {"id": row["id"], "pair_id": row["pair_id"], "family": row["family"], "language": row["language"],
            "options": len(row["questions"][qid]["criteria"]), "expected": row["expected"][qid]}


def practical_rows(records):
    result = []
    for r in records:
        qid, = r["request"]["questions"]
        q = r["request"]["questions"][qid]
        result.append({"id": r["record_id"], "pair_id": r["group_id"], "family": r["source_family"],
                       "language": r["language"], "state": r["request"]["state"], "questions": r["request"]["questions"],
                       "expected": {qid: r["supervision"][qid]["gold"]}})
    return result


def existing_practical(logits, panel):
    records = {r["record_id"]: r for r in logits}
    result = []
    for row in panel:
        r = records[row["id"]]
        pred = max(range(len(r["logits"])), key=r["logits"].__getitem__)
        assert r["keys"][r["label"]] == next(iter(row["expected"].values()))
        result.append({**external_meta(row), "status": "ok", "choice": r["keys"][pred], "correct": pred == r["label"]})
    return result


def decode_answer(question, answer):
    """Discrete gold uses argmax, including ordinal tasks, not rounded expected score."""
    typ = question["type"]
    if typ == "noul":
        p = float(answer["noul"])
        probabilities = {"false": 1-p, "true": p}
    else:
        probabilities = answer["probabilities"]
    keys = list(question["criteria"]) if typ == "choice" else [str(i) for i in range(len(question["criteria"]))] if typ == "score" else ["false", "true"]
    assert set(probabilities) == set(keys)
    assert all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
    assert abs(sum(probabilities.values()) - 1) <= .01
    choice = answer["choice"] if typ == "choice" else max(keys, key=probabilities.__getitem__)
    assert choice in keys
    tie = sum(p == max(probabilities.values()) for p in probabilities.values()) > 1
    return choice, probabilities, tie


def check_laya_encoding(tok, state, question):
    """Same full/native token comparison as the existing adapter, for all 3 native types."""
    from laya.common import build_sequence, render_options, serialize_state, encode_text
    q = {"t": question["type"], "ins": question["instructions"], "crit": question["criteria"]}
    assert q["t"] in ("choice", "score", "noul") and isinstance(q["ins"], str)
    encode = lambda text: encode_text(tok, text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
    opts = [encode(" " + x) for x in render_options(q)]
    expected = [tok.cls_token_id] + encode(q["t"] + " question: " + q["ins"]) + [tok.sep_token_id]
    markers = []
    for opt in opts:
        markers.append(len(expected))
        expected += [tok.mask_token_id] + opt
    expected += [tok.sep_token_id] + encode(serialize_state(state)) + [tok.sep_token_id]
    actual, actual_markers = build_sequence(tok, state, q, 8192, 8184)
    return not any(len(x) > 48 for x in opts) and expected == actual and markers == actual_markers


def main(root, out, preflight=False):
    run_root = root / "runs/bilingual-all-v1"
    pilot = run_root / "practical-pilot-v2"
    source = run_root / "training-source"
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(root / "references/decision-index"))

    selection = json.loads((pilot / "results/selection.json").read_text())
    pilot_report = json.loads((pilot / "results/report.json").read_text())
    pm = json.loads((pilot / "manifest.json").read_text())
    assert pilot_report["status"] == "complete"
    assert selection["identity"]["manifest_sha256"] == digest(pilot / "manifest.json")
    selected = selection["selected_before_test"]
    checkpoint = Path(next(path for _,name,path in selection["candidates"] if name == selected))
    assert selected == "adapted-256", "Unexpected selected candidate; review before changing comparison identity"
    for name,h in pm["frozen_runtime_sha256"].items():
        assert digest(source / name) == h
    cp = json.loads((checkpoint / "run.json").read_text())
    assert cp["identity"] == selection["identity"] and cp["additional_updates"] == 256
    latest_name = "v2_74k_plus_256"
    out.mkdir(exist_ok=True)
    provenance = {"selected_model": latest_name, "selection_sha256": digest(pilot / "results/selection.json"),
        "pilot_manifest_sha256": digest(pilot / "manifest.json"),
        "checkpoint_sha256": {str(p.relative_to(checkpoint)):digest(p) for p in checkpoint.rglob("*") if p.is_file()},
        "source_sha256": {p.name:digest(p) for p in (out / "source").iterdir() if p.is_file()},
        "inputs": {}, "baseline_sha256": {}}
    panels, predictions = {}, {}
    okapi = run_root / "decision-index-okapi-v1"
    om = json.loads((okapi / "manifest.json").read_text())
    for repo, rev in om["repositories"].items():
        assert subprocess.check_output(["git", "-C", str(root / "references" / repo), "rev-parse", "HEAD"], universal_newlines=True).strip() == rev
    assert digest(okapi / "rows.jsonl") == om["rows_sha256"]
    panels["okapi"] = load(okapi / "rows.jsonl")
    provenance["inputs"]["okapi"] = om["rows_sha256"]
    predictions["okapi"] = {}

    def baseline(path):
        provenance["baseline_sha256"][str(path.relative_to(run_root))] = digest(path)
        return load(path)

    for directory in [okapi] + sorted(run_root.glob("okapi-*")):
        report = directory / "results/report.json"
        manifest = directory / "manifest.json"
        if not report.exists() or not manifest.exists():
            continue
        r = json.loads(report.read_text())
        m = json.loads(manifest.read_text())
        if r["status"] != "complete":
            continue
        assert r["manifest_sha256"] == digest(manifest)
        assert m["rows_sha256"] == om["rows_sha256"], "Historical Okapi panel changed"
        name = "nesso_" + str(r["checkpoint_step"])
        rows = baseline(directory / "results/decision.jsonl")
        if name in predictions["okapi"]:
            assert [(x["id"],x["correct"]) for x in predictions["okapi"][name]] == [(x["id"],x["correct"]) for x in rows]
        predictions["okapi"][name] = rows
    predictions["okapi"]["parent"] = baseline(okapi / "results/parent.jsonl")
    lr = json.loads((okapi / "laya-results/report.json").read_text())
    assert lr["status"] == "complete" and lr["panel_manifest_sha256"] == digest(okapi / "manifest.json")
    predictions["okapi"]["laya"] = baseline(okapi / "laya-results/laya.jsonl")

    panels["decision_index"] = []
    predictions["decision_index"] = {m: [] for m in ("nesso_74000", "nesso_142000", "parent", "laya")}
    for language in ("english", "italian"):
        d = run_root / ("decision-index-" + language + "-selection-v1")
        m = json.loads((d / "manifest.json").read_text())
        assert digest(d / "selection.jsonl") == m["panel_sha256"]["selection"]
        provenance["inputs"]["decision_index_" + language] = m["panel_sha256"]["selection"]
        rows = load(d / "selection.jsonl")
        panels["decision_index"] += rows
        for name in ("74000", "142000", "parent", "laya"):
            r = json.loads((d / "results/selection" / name / "report.json").read_text())
            assert r["status"] == "complete" and r["manifest_sha256"] == digest(d / "manifest.json")
            old = {r["id"]:r for r in baseline(d / "results/selection" / name / "predictions.jsonl")}
            model_name = "nesso_" + name if name.isdigit() else name
            predictions["decision_index"][model_name] += [{**external_meta(r), "status":old[r["id"]]["status"], "correct":old[r["id"]]["correct"]} for r in rows]

    data_manifest = json.loads((pilot / "data/manifest.json").read_text())
    assert digest(pilot / "data/manifest.json") == pm["data_manifest_sha256"]
    assert digest(pilot / "data/test.jsonl") == data_manifest["files"]["test.jsonl"]["sha256"]
    panels["practical_v2"] = practical_rows(load(pilot / "data/test.jsonl"))
    provenance["inputs"]["practical_v2"] = digest(pilot / "data/test.jsonl")
    predictions["practical_v2"] = {}
    for name in ("74000", "142000", selected):
        path = pilot / "results" / (name + "-test-logits.json")
        provenance["baseline_sha256"][str(path.relative_to(run_root))] = digest(path)
        rows = json.loads(path.read_text())["rows"]
        predictions["practical_v2"][latest_name if name == selected else "nesso_"+name] = existing_practical(rows, panels["practical_v2"])

    if (out / "manifest.json").exists():
        assert json.loads((out / "manifest.json").read_text()) == provenance, "Do not resume changed inputs/code/model"
    else:
        save(out / "manifest.json", provenance)
    for panel, rows in predictions.items():
        common_panel(rows)
    if preflight:
        print("PREFLIGHT OK", {p:len(rows) for p,rows in panels.items()}, flush=True)
        return
    if (out / "report.json").exists():
        print("Already complete", flush=True)
        return
    import torch
    from decision_index.engines import Unsupported, validate
    from decision_subset_engine import NessoEngine, LayaEngine
    save(out / "environment.json", {"torch": torch.__version__, "hip":torch.version.hip, "gpu":torch.cuda.get_device_name()})

    def score(engine, panel, model_name):
        path = out / (panel + "-" + model_name + ".jsonl")
        old = {r["id"]:r for r in load(path)} if path.exists() else {}
        assert len(old) <= len(panels[panel])
        started = time.monotonic()
        with path.open("a") as stream:
            for i,row in enumerate(panels[panel]):
                meta = external_meta(row)
                if row["id"] in old:
                    assert all(old[row["id"]][k] == v for k,v in meta.items())
                    continue
                qid, = row["questions"]
                try:
                    response,_ = engine(row["state"], row["questions"])
                    if row["questions"][qid]["type"] == "score":
                        # This pinned Decision Index validator only supports choice/noul.
                        assert set(response["answers"]) == {qid}
                        assert response["answers"][qid]["type"] == "score"
                    else:
                        validate(row["questions"], response)
                    ans = response["answers"][qid]
                    choice, probabilities, tied = decode_answer(row["questions"][qid], ans)
                    result = {**meta, "status":"ok", "choice":choice, "correct":choice == meta["expected"],
                              "probabilities":probabilities, "rounded_probability_tie":tied,
                              "nll":-math.log(max(probabilities[meta["expected"]],1e-30))}
                except Unsupported as exc:
                    result = {**meta, "status":"unsupported", "correct":False, "reason":str(exc)}
                stream.write(json.dumps(result,ensure_ascii=False)+"\n")
                stream.flush()
                old[row["id"]] = result
                if (i+1)%200 == 0:
                    print(panel,model_name,i+1,"/",len(panels[panel]),"seconds",round(time.monotonic()-started),flush=True)
        assert set(old) == {r["id"] for r in panels[panel]}
        return [old[r["id"]] for r in panels[panel]]

    engine = NessoEngine(str(checkpoint))
    for panel in ("okapi", "decision_index"):
        predictions[panel][latest_name] = score(engine, panel, latest_name)
    del engine
    gc.collect()
    torch.cuda.empty_cache()
    engine = LayaEngine(str(root))
    save(out / "laya-provenance.json", engine.provenance)
    # Keep Laya's native noul/score formats; do not convert these tasks to choice.
    def native_laya(state, questions):
        for q in questions.values():
            if not check_laya_encoding(engine.agent.tok, state, q):
                raise Unsupported("Native Laya tokenization would truncate")
        response = engine.agent.predict(state, questions, max_len=8192, head_max_len=8184)
        assert not response["usage"].get("truncated",False) and engine.agent.cpu_fallback_count == 0
        return response,None
    predictions["practical_v2"]["laya"] = score(native_laya, "practical_v2", "laya")
    report = {"status":"complete", "selected_model":latest_name, "manifest_sha256":digest(out/"manifest.json"),
              "panels":{p:common_panel(rows) for p,rows in predictions.items()},
              "limitations":["Reused diagnostic panels; not new independent model-selection tests",
                  "Full scores count unsupported as wrong; common scores retain both languages supported by every listed model",
                  "Separate datasets and averaging conventions must not be merged into one overall score",
                  "Practical v2 is synthetic; no claim of production readiness or a valid confidence policy",
                  "Laya uses native renderer, pinned weights and shipped temperatures, with 8192/8184 context/head limits and no truncation",
                  "Laya discrete score/noul decisions use native rounded probabilities (argmax, first semantic key for ties); ties are recorded per case",
                  "Nesso external evaluations use the same frozen native rows engine and T=1 as prior comparisons"]}
    save(out / "report.json", report)
    print("COMPLETE",json.dumps({p:{m:s["by_language"] for m,s in v["common_bilingual"].items()} for p,v in report["panels"].items()}),flush=True)


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight",action="store_true")
    a=ap.parse_args()
    main(a.root,a.out,a.preflight)
