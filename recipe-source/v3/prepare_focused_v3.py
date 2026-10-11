"""Freeze targeted v3 starting from selected v2; preserve all previous runs."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from practical_data import sha, validate_pairs
from focused_data_v3 import generate, BANKS, SIZES


def main(root, out):
    source = root / "training-source"
    sys.path.insert(0, str(source))
    from decision_model.data import digest, load_split, write_json, write_jsonl
    from decision_model.render import encode_request
    from decision_model.schema import DecisionRequest
    from transformers import AutoTokenizer

    if (out / "manifest.json").exists():
        raise ValueError("Refusing to replace a frozen experiment")
    recipe = json.loads((out / "source/nesso2-focused-v3.json").read_text())
    assert recipe["pairs_per_task"] == SIZES
    previous = root / "decision-index-english-selection-v1"
    reference = json.loads((previous / "manifest.json").read_text())
    runtime = reference["frozen_runtime_sha256"]
    for name, expected in runtime.items():
        assert digest(source / name) == expected, name
    for name in ("experiments/lumi/train_full.py", "experiments/lumi/run_bilingual_pilot.py", "decision_model/export.py"):
        runtime[name] = digest(source / name)
    pilot = root / "practical-pilot-v2"
    selection = json.loads((pilot / "results/selection.json").read_text())
    assert selection["selected_before_test"] == "adapted-256"
    assert selection["identity"]["manifest_sha256"] == digest(pilot / "manifest.json")
    checkpoint = pilot / "training/adapted-256"
    checksums = {str(p.relative_to(checkpoint)):digest(p) for p in checkpoint.rglob("*") if p.is_file()}
    cp_meta = json.loads((checkpoint / "run.json").read_text())
    assert cp_meta["identity"] == selection["identity"] and cp_meta["additional_updates"] == 256
    checkpoints = {"v2": {"path":str(checkpoint), "sha256":checksums}}
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
    # Explicitly rebalance the large-menu intent source across gold classes.
    banking = defaultdict(list)
    for pair in candidates.pop("banking77"):
        assert len(pair) == 2
        gold = tuple(v["gold"] for v in pair[0]["supervision"].values())
        banking[gold].append(pair)
    focused = []
    for i in range(max(map(len, banking.values()))):
        for gold in sorted(banking):
            if i < len(banking[gold]): focused.extend(banking[gold][i])
            if len(focused) == recipe["banking77_records"]: break
        if len(focused) == recipe["banking77_records"]: break
    assert len(focused) == recipe["banking77_records"]
    replay = []
    for i in range(max(map(len, candidates.values()))):
        for s in sorted(candidates):
            if i < len(candidates[s]): replay.extend(candidates[s][i])
            if len(replay) == recipe["replay_records"]: break
        if len(replay) == recipe["replay_records"]: break
    assert len(replay) == recipe["replay_records"]
    splits["train"] += focused + replay
    del old, pools, candidates, banking
    # This is a development guard only, never the previously inspected final test.
    splits["practical_guard"] = load_split(pilot / "data", "dev")
    guard_pairs = defaultdict(list)
    for r in load_split(original, "dev"):
        guard_pairs[(r["source_family"], r["provenance"]["parallel_record"])].append(r)
    by_source = defaultdict(list)
    for (s, pid), pair in guard_pairs.items():
        by_source[s].append((sha(pid), pair))
    splits["guard"] = [r for s in sorted(by_source) for _, pair in sorted(by_source[s])[:32] for r in pair]
    del guard_pairs, by_source
    counts = validate_pairs(splits)
    checkpoint_meta = json.loads((Path(checkpoints["v2"]["path"]) / "run.json").read_text())
    assert checkpoint_meta["parent"] == recipe["parent"] and checkpoint_meta["revision"] == recipe["revision"]
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
    config = recipe["train"]
    assert len(splits["train"]) == config["updates"] * config["accumulation"]
    write_json(out / "config.json", config)
    manifest = {"status": "ready", "scope": "Focused v3 intent/routing adaptation with separate original and practical retention guards",
        "root": str(root), "training_mixture": {"new_routing":1024,"new_intent":1024,"banking77":3072,"other_replay":3072}, "counts": counts, "capacity": audit, "checkpoints": checkpoints,
        "frozen_runtime_sha256": runtime, "data_manifest_sha256": digest(data / "manifest.json"),
        "config_sha256": digest(out / "config.json"), "original_manifest_sha256": digest(original / "manifest.json"),
        "recipe_sha256": digest(out / "source/nesso2-focused-v3.json"),
        "source_sha256": {p.name: digest(p) for p in (out / "source").iterdir() if p.is_file()},
        "overlap_audit": "Zero exact full-request matches between generated cases and all original train records",
        "selection": "Lowest new-dev task/language macro NLL among selected v2 and eligible snapshots; ties retain v2",
        "guard": "Both original-dev and practical-v2-dev: NLL <= v2 + .05, each language accuracy >= v2 - .02",
        "wording_banks": BANKS,
        "parent_experiment": {"name":"practical-pilot-v2", "manifest_sha256":digest(pilot / "manifest.json"),
                              "selection_sha256":digest(pilot / "results/selection.json")},
        "split_discipline": "EN/IT pairs stay together. New routing excludes every v1/v2 fact configuration. Synthetic intent final utterances never appear in train/dev/calibration. No final test scoring before selection and calibration. Replay uses original train only.",
        "limitations": ["Rule families are shared across splits; this measures within-family wording transfer",
                        "Synthetic 16-intent cases and routing are not representative traffic or independently authored benchmarks; improvement here does not establish CLINC generalization",
                        "Bilingual templates authored and reviewed by Codex, not native-speaker certified; no separate teacher was used",
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
