"""Freeze an isolated bilingual operational pilot; CPU-only preparation."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from practical_data import generate, sha, validate_pairs


def main(root, out):
    source = root / "training-source"
    sys.path.insert(0, str(source))
    from decision_model.data import digest, load_split, write_json, write_jsonl
    from decision_model.render import encode_request
    from decision_model.schema import DecisionRequest
    from transformers import AutoTokenizer

    if (out / "manifest.json").exists():
        raise ValueError("Refusing to replace a frozen experiment")
    previous = root / "decision-index-english-selection-v1"
    reference = json.loads((previous / "manifest.json").read_text())
    runtime = reference["frozen_runtime_sha256"]
    for name, expected in runtime.items():
        assert digest(source / name) == expected, name
    for name in ("experiments/lumi/train_full.py", "experiments/lumi/run_bilingual_pilot.py"):
        runtime[name] = digest(source / name)
    checkpoints = {}
    for step in ("74000", "142000"):
        checkpoint = previous / "checkpoints" / step
        checksums = reference["checkpoint_files_sha256"][step]
        for name, expected in checksums.items():
            assert digest(checkpoint / name) == expected, name
        checkpoints[step] = {"path": str(checkpoint.resolve()), "sha256": checksums}
    splits = generate()
    new_requests = {sha(r["request"]) for rows in splits.values() for r in rows}
    original = root / "data-reviewed"
    old = load_split(original, "train")
    pools = defaultdict(lambda: defaultdict(list))
    for r in old:
        assert sha(r["request"]) not in new_requests, "New request exactly overlaps original train"
        pools[r["source_family"]][r["provenance"]["parallel_record"]].append(r)
    candidates = {s: [p for _, p in sorted(groups.items(), key=lambda item: sha(item[0]))]
                  for s, groups in pools.items()}
    replay = []
    for i in range(max(map(len, candidates.values()))):
        for s in sorted(candidates):
            if i < len(candidates[s]):
                replay.extend(candidates[s][i])
                if len(replay) == 2048:
                    break
        if len(replay) == 2048:
            break
    assert len(replay) == 2048
    splits["train"] += replay
    del old, pools, candidates
    guard_pairs = defaultdict(list)
    for r in load_split(original, "dev"):
        guard_pairs[(r["source_family"], r["provenance"]["parallel_record"])].append(r)
    by_source = defaultdict(list)
    for (s, pid), pair in guard_pairs.items():
        by_source[s].append((sha(pid), pair))
    splits["guard"] = [r for s in sorted(by_source) for _, pair in sorted(by_source[s])[:16] for r in pair]
    del guard_pairs, by_source
    counts = validate_pairs(splits)
    checkpoint_meta = json.loads((Path(checkpoints["74000"]["path"]) / "run.json").read_text())
    tok = AutoTokenizer.from_pretrained(checkpoint_meta["parent"], revision=checkpoint_meta["revision"], local_files_only=True)
    audit = {}
    for split, rows in splits.items():
        lengths = [len(encode_request(tok, DecisionRequest.model_validate(r["request"]))[0]["ids"]) for r in rows]
        audit[split] = {"records": len(rows), "max_packed_tokens": max(lengths), "all_supported": True}
    data = out / "data"
    data.mkdir(exist_ok=False)
    for split, rows in splits.items():
        write_jsonl(data / (split + ".jsonl"), rows)
    files = {p.name: {"sha256": digest(p), "records": len(splits[p.stem])} for p in sorted(data.glob("*.jsonl"))}
    write_json(data / "manifest.json", {"files": files})
    config = {"seed": 20261009, "updates": 512, "accumulation": 8, "lr": 1e-5,
              "weight_decay": .01, "clip": 1., "eval_every": 128,
              "max_guard_nll_increase": .05, "max_guard_accuracy_drop": .02,
              "calibration_temperature_grid": {"low": .25, "high": 4., "points": 81},
              "confidence_threshold_grid": [.5, .6, .7, .8, .85, .9, .95, .975, .99],
              "calibration_risk_target": .10, "calibration_min_accepted_per_language": 30}
    write_json(out / "config.json", config)
    manifest = {"status": "ready", "scope": "Synthetic rule-following pilot, not real-world validation",
        "root": str(root), "counts": counts, "capacity": audit, "checkpoints": checkpoints,
        "frozen_runtime_sha256": runtime, "data_manifest_sha256": digest(data / "manifest.json"),
        "config_sha256": digest(out / "config.json"), "original_manifest_sha256": digest(original / "manifest.json"),
        "source_sha256": {p.name: digest(p) for p in (out / "source").iterdir() if p.is_file()},
        "overlap_audit": "Zero exact full-request matches between generated cases and all original train records",
        "selection": "Lowest new-dev task/language macro NLL among 74k, 142k and eligible follow-up snapshots; ties prefer 74k",
        "guard": "Follow-up eligibility requires original-dev NLL <= baseline + .05 and per-language accuracy >= baseline - .02",
        "split_discipline": "Distinct complete fact configurations; EN/IT pairs stay together; test uses different instruction wording; no test scoring until candidate selection and calibration are frozen",
        "limitations": ["Templates and rule families are shared across splits; this measures within-family transfer",
                        "Synthetic label-balanced cases; not representative traffic or independently authored benchmark",
                        "Bilingual templates authored and reviewed by Codex, not native-speaker certified",
                        "Calibration thresholds are exploratory and do not provide a production risk guarantee",
                        "One training seed and one learning rate; no claim of optimal settings"]}
    write_json(out / "manifest.json", manifest)
    print(json.dumps({"status": "ready", "counts": counts, "updates": config["updates"]}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    main(a.root, a.out)
