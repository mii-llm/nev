"""Regression audit of selected v3 adapter and merged export on frozen bilingual panels.

Panel preparation/scoring mirror compare_latest; no training or selection occurs.
Baselines and weights must match previously archived hashes. Practical v2 uses
its original native packed path; external choice tasks use the frozen rows path.
"""
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from compare_latest import (load, save, common_panel, external_meta, practical_rows,
                            existing_practical, decode_answer)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def paired_delta(before, after):
    """Report correctness transitions on exactly aligned cases, including failures."""
    a = {r["id"]: r for r in before}
    b = {r["id"]: r for r in after}
    assert len(a) == len(before) == len(b) == len(after) and a.keys() == b.keys()
    for key in a:
        assert all(a[key][k] == b[key][k] for k in ("expected", "family", "language", "pair_id"))
    groups = {"all": list(a)}
    for r in before:
        groups.setdefault(r["language"], []).append(r["id"])
        groups.setdefault(r["family"] + "/" + r["language"], []).append(r["id"])
    out = {}
    for group, ids in groups.items():
        gained = sum(not a[i]["correct"] and b[i]["correct"] for i in ids)
        lost = sum(a[i]["correct"] and not b[i]["correct"] for i in ids)
        out[group] = {"n": len(ids), "gained": gained, "lost": lost,
                      "delta_percentage_points": 100 * (gained-lost) / len(ids)}
    return out


def verify_report(actual, expected, path=""):
    """Python versions differ in sum rounding; identities/counts remain exact."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for k in expected:
            verify_report(actual[k], expected[k], path + "/" + k)
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12), (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)


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
    out.mkdir(exist_ok=True, parents=True)
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

    # Pins copied from the already verified local completion archives.
    pins = json.loads((out / "source/regression-pins.json").read_text())
    prior = run_root / "practical-v2-benchmark-comparison-v1"
    assert digest(prior / "report.json") == pins["comparison/report.json"]["sha256"]
    assert digest(prior / "manifest.json") == pins["comparison/manifest.json"]["sha256"]
    assert provenance["inputs"] == json.loads((prior / "manifest.json").read_text())["inputs"]
    for name, h in provenance["baseline_sha256"].items():
        assert h == pins["baselines/" + name]["sha256"], name
    for filename, panel, model in (
        ("okapi-v2_74k_plus_256.jsonl", "okapi", latest_name),
        ("decision_index-v2_74k_plus_256.jsonl", "decision_index", latest_name),
        ("practical_v2-laya.jsonl", "practical_v2", "laya"),
    ):
        assert digest(prior / filename) == pins["comparison/" + filename]["sha256"]
        predictions[panel][model] = baseline(prior / filename)
    v3 = run_root / "focused-pilot-v3"
    assert digest(v3 / "artifact-sha256.json") == "c7046a13e6c73c9652bb372d1d597ca2589e5e41bd8cb89d0a26a6ec2636331e"
    artifacts = json.loads((v3 / "artifact-sha256.json").read_text())
    for name, h in artifacts.items():
        assert digest(v3 / name) == h, name
    provenance["v3_artifact_sha256"] = artifacts
    provenance["v3_root"] = str(v3)
    provenance["numerics"] = "FP32 parameters / BF16 autocast / T=1; external rows; practical packed logits"
    provenance["protocol"] = "Frozen diagnostic subsets; full and bilingual common support; no model selection"
    provenance["comparison_report_sha256"] = digest(prior / "report.json")
    if (out / "manifest.json").exists():
        assert json.loads((out / "manifest.json").read_text()) == provenance, "Changed inputs/code/model"
    else:
        save(out / "manifest.json", provenance)
    old_report = json.loads((prior / "report.json").read_text())
    for panel, rows in predictions.items():
        verify_report(common_panel(rows), old_report["panels"][panel], panel)
    if preflight:
        print("PREFLIGHT OK", {p:len(rows) for p,rows in panels.items()}, flush=True)
        return
    if (out / "report.json").exists():
        print("Already complete", flush=True)
        return
    import torch
    from decision_index.engines import Unsupported, validate
    from decision_subset_engine import NessoEngine
    from decision_model.model import DecisionModel
    from run_focused_v3 import infer
    save(out / "environment.json", {"torch":torch.__version__, "hip":torch.version.hip,
                                    "gpu":torch.cuda.get_device_name()})

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

    for name in ("v3_adapter_512", "v3_merged_export"):
        if name == "v3_adapter_512":
            engine = NessoEngine(str(v3 / "training/adapted-512"))
        else:
            # Same call implementation and admission policy, standalone merged weights.
            engine = NessoEngine.__new__(NessoEngine)
            engine.model = DecisionModel.from_pretrained(v3 / "private-export", device="cuda", dtype=torch.float32).eval()
        assert all(p.dtype == torch.float32 for p in engine.model.parameters())
        for panel in ("okapi", "decision_index"):
            predictions[panel][name] = score(engine, panel, name)
        raw_path = out / ("practical_v2-" + name + "-logits.json")
        if raw_path.exists():
            raw = json.loads(raw_path.read_text())
        else:
            rows, performance = infer(engine.model, load(pilot / "data/test.jsonl"))
            raw = {"rows":rows, "performance":performance}
            save(raw_path, raw)
        rows = existing_practical(raw["rows"], panels["practical_v2"])
        predictions["practical_v2"][name] = rows
        (out / ("practical_v2-"+name+".jsonl")).write_text("".join(json.dumps(r)+"\n" for r in rows))
        del engine
        gc.collect()
        torch.cuda.empty_cache()
        save(out / (name+"-summary.json"), {p:common_panel({latest_name:rs[latest_name],name:rs[name]}) for p,rs in predictions.items()})
        print("MODEL COMPLETE",name,flush=True)
    report = {"status":"complete", "selected_model":"v3_adapter_512", "manifest_sha256":digest(out / "manifest.json"),
              "panels":{p:common_panel(rows) for p,rows in predictions.items()},
              "v3_vs_v2":{p:common_panel({m:rs[m] for m in (latest_name,"v3_adapter_512","v3_merged_export")}) for p,rs in predictions.items()},
              "paired_full_deltas":{p:{name:paired_delta(rs[latest_name],rs[name]) for name in ("v3_adapter_512","v3_merged_export")} for p,rs in predictions.items()},
              "export_vs_adapter_full":{p:paired_delta(rs["v3_adapter_512"],rs["v3_merged_export"]) for p,rs in predictions.items()},
              "limitations":old_report["limitations"] + ["This audit does not select another checkpoint; v3 +512 was fixed in advance", "Practical v2 test was previously inspected; not an independent fresh test"]}
    save(out / "report.json", report)
    print("COMPLETE", flush=True)


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight",action="store_true")
    a=ap.parse_args()
    main(a.root,a.out,a.preflight)
