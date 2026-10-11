"""Focused v3 adaptation from selected v2, with two independent retention guards."""
import argparse
import copy
import json
import math
import random
import sys
import time
from pathlib import Path


def probabilities(logits, temperature=1.):
    z = [x / temperature for x in logits]
    p = [math.exp(x - max(z)) for x in z]
    return [v / sum(p) for v in p]


def wilson_upper(errors, n):
    if not n:
        return 1.
    z = 1.96
    p = errors / n
    return (p + z*z/(2*n) + z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1+z*z/n)


def metrics(rows, temperature=1., threshold=None):
    values = []
    for r in rows:
        p = probabilities(r["logits"], temperature)
        pred = max(range(len(p)), key=p.__getitem__)
        values.append((max(p), pred == r["label"], -math.log(max(p[r["label"]], 1e-30))))
    n = len(values)
    accepted = [v for v in values if threshold is not None and v[0] >= threshold]
    bins = [[v for v in values if min(9, int(v[0]*10)) == i] for i in range(10)]
    return {"n": n, "accuracy": sum(v[1] for v in values)/n,
            "nll": sum(v[2] for v in values)/n,
            "ece_10": sum(abs(sum(v[0]-v[1] for v in b)) for b in bins)/n,
            "accepted": len(accepted), "coverage": len(accepted)/n,
            "accepted_error_rate": sum(not v[1] for v in accepted)/len(accepted) if accepted else None,
            "accepted_error_wilson_upper": wilson_upper(sum(not v[1] for v in accepted), len(accepted)) if accepted else None,
            "wrong_with_confidence_at_least_90pct": sum(not v[1] and v[0] >= .9 for v in values)}


def summarize(rows, temperature=1., threshold=None):
    cells = {r["source_family"] + "/" + r["language"] for r in rows}
    out = {"overall": metrics(rows, temperature, threshold),
           "by_language": {l: metrics([r for r in rows if r["language"] == l], temperature, threshold) for l in ("en", "it")},
           "by_task_language": {k: metrics([r for r in rows if r["source_family"] + "/" + r["language"] == k], temperature, threshold) for k in sorted(cells)}}
    out["macro_nll"] = sum(v["nll"] for v in out["by_task_language"].values()) / len(cells)
    out["macro_accuracy"] = sum(v["accuracy"] for v in out["by_task_language"].values()) / len(cells)
    return out


def calibrate(fit_rows, policy_rows, cfg):
    grid = cfg["calibration_temperature_grid"]
    candidates = [math.exp(math.log(grid["low"]) + i/(grid["points"]-1)*math.log(grid["high"]/grid["low"])) for i in range(grid["points"])]
    temperature = min(candidates, key=lambda t: summarize(fit_rows, t)["macro_nll"])
    thresholds = []
    for threshold in cfg["confidence_threshold_grid"]:
        result = summarize(policy_rows, temperature, threshold)
        if all(v["accepted"] >= cfg["calibration_min_accepted_per_language"] and
               v["accepted_error_wilson_upper"] <= cfg["calibration_risk_target"] for v in result["by_language"].values()):
            thresholds.append((result["overall"]["coverage"], threshold))
    threshold = max(thresholds)[1] if thresholds else None
    return {"temperature": temperature, "threshold": threshold,
            "fallback": "Escalate all cases" if threshold is None else "Escalate below threshold",
            "temperature_fit": summarize(fit_rows, temperature),
            "calibration": summarize(policy_rows, temperature, threshold),
            "limitation": "Temperature and threshold use distinct facts and wording. Grid-selected empirical policy; Wilson bounds are exploratory, not a post-selection risk guarantee"}


def guard_pass(candidate, baseline, cfg):
    return (candidate["macro_nll"] <= baseline["macro_nll"] + cfg["max_guard_nll_increase"] and
            all(candidate["by_language"][l]["accuracy"] >= baseline["by_language"][l]["accuracy"] -
                cfg["max_guard_accuracy_drop"] for l in ("en", "it")))


def should_stop(history, baseline_nll, step, cfg):
    improving = [(i, h["dev"]["macro_nll"]) for i, h in enumerate(history)
                 if h["eligible"] and h["dev"]["macro_nll"] < baseline_nll]
    best_index = min(improving, key=lambda x: x[1])[0] if improving else -1
    stale = len(history) - best_index - 1
    return step >= cfg["minimum_updates_before_early_stop"] and stale >= cfg["early_stop_patience"]


def read_rows(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def infer(model, records):
    import torch
    from decision_model.render import to_record
    from decision_model.schema import DecisionRequest, question_keys
    model.eval()
    rows, latencies = [], []
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        # Warm up separately; timed requests include schema validation and tokenization.
        for r in records[:4]:
            enc = model.encode(to_record(DecisionRequest.model_validate(r["request"]))[0])
            model.forward_batch([enc], form="packed")
        torch.cuda.synchronize()
        for r in records:
            start = time.perf_counter()
            req = DecisionRequest.model_validate(r["request"])
            enc = model.encode(to_record(req)[0])
            zs = model.forward_batch([enc], form="packed")[0]
            torch.cuda.synchronize()
            latencies.append(1000*(time.perf_counter()-start))
            for (qid, q), z in zip(req.questions.items(), zs):
                keys = question_keys(q.type, q.criteria)
                logits = z.float().cpu().tolist()
                if not all(math.isfinite(v) for v in logits):
                    raise ValueError("Non-finite inference logits")
                rows.append({**{k: r[k] for k in ("record_id", "group_id", "source_family", "language")},
                             "template_id": r.get("provenance", {}).get("template_id"),
                             "qid": qid, "keys": keys, "logits": logits,
                             "label": keys.index(r["supervision"][qid]["gold"])})
    latency = sorted(latencies)
    return rows, {"batch_size": 1, "requests": len(records), "median_ms": latency[len(latency)//2],
                  "p95_ms": latency[min(len(latency)-1, math.ceil(.95*len(latency))-1)],
                  "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                  "gpu": torch.cuda.get_device_name(), "scope": "FP32 weights/BF16 autocast; includes tokenization; excludes model loading and network"}


def main(out):
    manifest = json.loads((out / "manifest.json").read_text())
    root = Path(manifest["root"])
    source = root / "training-source"
    sys.path.insert(0, str(source))
    import torch
    from decision_model.data import digest, load_split
    from decision_model.model import DecisionModel
    from decision_model.train import epoch_order, example, _encode, soft_ce
    from experiments.lumi.train_full import atomic_json, save_state, restore_state
    from experiments.lumi.run_bilingual_pilot import free

    for name, h in manifest["frozen_runtime_sha256"].items():
        assert digest(source / name) == h, name
    for name, h in manifest["source_sha256"].items():
        assert digest(out / "source" / name) == h, name
    assert digest(out / "data/manifest.json") == manifest["data_manifest_sha256"]
    assert digest(out / "config.json") == manifest["config_sha256"]
    for spec in manifest["checkpoints"].values():
        for name, h in spec["sha256"].items():
            assert digest(Path(spec["path"]) / name) == h, name
    cfg = json.loads((out / "config.json").read_text())
    results = out / "results"
    results.mkdir(exist_ok=True)
    identity = {"manifest_sha256": digest(out / "manifest.json")}
    if (results / "identity.json").exists():
        assert json.loads((results / "identity.json").read_text()) == identity
    else:
        atomic_json(results / "identity.json", identity)
    if (results / "report.json").exists():
        print("Evaluation already complete", flush=True)
        return
    import platform
    import importlib.metadata
    atomic_json(results / "environment.json", {"python": sys.version, "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in ("torch", "transformers", "peft", "safetensors", "tokenizers", "pydantic")},
        "torch_hip": torch.version.hip, "gpu": torch.cuda.get_device_name(), "identity": identity})
    data = out / "data"
    dev, guard = load_split(data, "dev"), load_split(data, "guard")
    practical_guard = load_split(data, "practical_guard")

    def evaluate(model, records, name):
        rows, perf = infer(model, records)
        atomic_json(results / (name + ".json"), {"rows": rows, "performance": perf})
        return summarize(rows)

    baselines = {}
    for step in ("v2",):
        target = results / ("baseline-" + step + ".json")
        if target.exists():
            baselines[step] = json.loads(target.read_text())
            continue
        model = DecisionModel.from_run(manifest["checkpoints"][step]["path"], device="cuda", dtype=torch.float32)
        baselines[step] = {"dev": evaluate(model, dev, step + "-dev"), "guard": evaluate(model, guard, step + "-guard"),
                           "practical_guard": evaluate(model, practical_guard, step + "-practical-guard")}
        atomic_json(target, baselines[step])
        print("BASELINE " + step + " " + json.dumps(baselines[step]), flush=True)
        del model
        free()

    # Explicitly load the adapter as trainable; the ordinary from_run loader is inference-only.
    from peft import PeftModel
    from safetensors.torch import load_file
    checkpoint = Path(manifest["checkpoints"]["v2"]["path"])
    meta = json.loads((checkpoint / "run.json").read_text())
    torch.manual_seed(cfg["seed"])
    model = DecisionModel.from_parent(meta["parent"], meta["revision"], device="cuda", dtype=torch.float32, head_dim=meta["head_dim"])
    model.lm = PeftModel.from_pretrained(model.lm, str(checkpoint / "adapter"), is_trainable=True).to(model.device)
    model.lora = meta["lora"]
    model.head.load_state_dict(load_file(checkpoint / "head.safetensors"))
    params = model.trainable_parameters()
    names = [n for n,p in model.named_parameters() if p.requires_grad]
    assert any("lora_A" in n for n in names) and any("lora_B" in n for n in names)
    assert all("lora_" in n or n.startswith("head.") for n in names)
    opt = torch.optim.AdamW(params, lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda step: min(1., (step+1)/cfg["warmup_updates"]))
    training = out / "training"
    training.mkdir(exist_ok=True)
    progress = {"step": 0, "history": [], "complete": False}
    latest = training / "latest.pt"
    if latest.exists():
        progress = restore_state(latest, model, opt, sched, identity)
    else:
        initial = evaluate(model, dev, "trainable-loader-dev")
        assert abs(initial["macro_nll"] - baselines["v2"]["dev"]["macro_nll"]) < 1e-6, "Trainable adapter load differs from baseline"
        atomic_json(training / "trainable-loader-check.json", {"passed": True, "trainable_tensors": len(names), "names": names})
    records = load_split(data, "train")
    order = epoch_order(records, random.Random(cfg["seed"]), language_balance={"en": .5, "it": .5}, accumulation=cfg["accumulation"])
    assert len(order) == cfg["updates"] * cfg["accumulation"]
    probe_names = [next(n for n in names if "lora_B" in n), next(n for n in names if n.startswith("head."))]
    probes = {n: dict(model.named_parameters())[n].detach().clone() for n in probe_names}
    start_time = time.monotonic()
    rolling_losses = []
    start_step = progress["step"]
    for step in range(cfg["updates"] if progress.get("complete") else progress["step"], cfg["updates"]):
        model.train()
        opt.zero_grad(set_to_none=True)
        batch = order[step*cfg["accumulation"]:(step+1)*cfg["accumulation"]]
        loss_sum = 0.
        for r in batch:
            req, targets = example(r, {}, random.Random(str(cfg["seed"]) + r["record_id"]), gold_weight=1.)
            enc = _encode(model, req)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model.forward_batch([enc], form="packed")[0]
            loss = sum(soft_ce(z.float(), torch.tensor(t, device=z.device)) for z,t in zip(logits, targets))/len(targets)
            assert torch.isfinite(loss), r["record_id"]
            (loss/len(batch)).backward()
            loss_sum += loss.item()
        torch.nn.utils.clip_grad_norm_(params, cfg["clip"], error_if_nonfinite=True)
        opt.step()
        sched.step()
        progress["step"] = step + 1
        rolling_losses.append(loss_sum/len(batch))
        if probes:
            changed = {n: float((dict(model.named_parameters())[n].detach() - old).abs().max()) for n, old in probes.items()}
            assert all(v > 0 for v in changed.values()), "Adapter/head failed to update"
            atomic_json(training / "parameter-update-check.json", {"step": step+1, "max_deltas": changed})
            probes.clear()
        if (step+1) % 32 == 0:
            event = {"step": step+1, "mean_loss_last_32_updates": sum(rolling_losses)/len(rolling_losses),
                     "session_wall_seconds": time.monotonic()-start_time,
                     "session_updates": step+1-start_step}
            with (training / "loss-history.jsonl").open("a") as f:
                f.write(json.dumps(event) + "\n")
            print("TRAIN " + json.dumps(event), flush=True)
            rolling_losses.clear()
        if (step+1) % cfg["eval_every"] == 0:
            name = "adapted-" + str(step+1)
            d = evaluate(model, dev, name + "-dev")
            g = evaluate(model, guard, name + "-guard")
            pg = evaluate(model, practical_guard, name + "-practical-guard")
            eligible = guard_pass(g, baselines["v2"]["guard"], cfg) and guard_pass(pg, baselines["v2"]["practical_guard"], cfg)
            model.save_run(training / name, extra={"additional_updates": step+1, "initialized_from": "v2_74000_plus_256", "identity": identity})
            entry = {"name": name, "dev": d, "guard": g, "practical_guard": pg, "eligible": eligible}
            progress["history"].append(entry)
            early_stop = should_stop(progress["history"], baselines["v2"]["dev"]["macro_nll"], step+1, cfg)
            progress["complete"] = step+1 == cfg["updates"] or early_stop
            progress["stopping_reason"] = "dev_plateau_or_regression" if early_stop else ("update_budget" if progress["complete"] else None)
            save_state(latest, model, opt, sched, progress, identity)
            atomic_json(training / "progress.json", progress)
            print("CHECKPOINT " + json.dumps(entry), flush=True)
            if progress["complete"]:
                break
    del opt, sched, params, model
    free()
    candidates = [(baselines[s]["dev"]["macro_nll"], s, manifest["checkpoints"][s]["path"]) for s in ("v2",)]
    eligible = [h for h in progress["history"] if h["eligible"]]
    best_adaptation = min(eligible, key=lambda h: h["dev"]["macro_nll"]) if eligible else None
    if best_adaptation:
        candidates.append((best_adaptation["dev"]["macro_nll"], best_adaptation["name"], str(training / best_adaptation["name"])))
    selected = min(candidates, key=lambda item: item[0])[1]
    decision = {"selected_before_test": selected, "candidates": candidates,
                "adaptation_eligible": best_adaptation is not None,
                "rule": manifest["selection"], "identity": identity}
    atomic_json(results / "selection.json", decision)
    calibration_fit = load_split(data, cfg["calibration_fit_split"])
    calibration_policy = load_split(data, cfg["calibration_policy_split"])
    calibrations = {}
    for _, name, path in candidates:
        model = DecisionModel.from_run(path, device="cuda", dtype=torch.float32)
        fit_rows, fit_perf = infer(model, calibration_fit)
        policy_rows, policy_perf = infer(model, calibration_policy)
        atomic_json(results / (name + "-calibration-fit-logits.json"), {"rows": fit_rows, "performance": fit_perf})
        atomic_json(results / (name + "-calibration-policy-logits.json"), {"rows": policy_rows, "performance": policy_perf})
        calibrations[name] = calibrate(fit_rows, policy_rows, cfg)
        del model
        free()
    atomic_json(results / "calibration.json", calibrations)
    # Only now open the final test. It cannot affect training, calibration or selection.
    test = load_split(data, "test")
    report = {"status": "running", "selection": decision, "models": {}, "limitations": manifest["limitations"]}
    for _, name, path in candidates:
        model = DecisionModel.from_run(path, device="cuda", dtype=torch.float32)
        rows, perf = infer(model, test)
        atomic_json(results / (name + "-test-logits.json"), {"rows": rows, "performance": perf})
        cal = calibrations[name]
        report["models"][name] = {"raw": summarize(rows), "calibrated": summarize(rows, cal["temperature"], cal["threshold"]),
                                  "by_template": {str(t): summarize([r for r in rows if r["template_id"] == t], cal["temperature"], cal["threshold"])
                                                  for t in sorted({r["template_id"] for r in rows})},
                                  "calibration": cal, "performance": perf}
        atomic_json(results / "partial-report.json", report)
        del model
        free()
    report["status"] = "complete"
    atomic_json(results / "report.json", report)
    print("COMPLETE " + json.dumps({"selected": selected, "models": {k:v["calibrated"]["by_language"] for k,v in report["models"].items()}}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    main(ap.parse_args().out)
