"""Prepare the full checked-in Kev recipe, preserving prior pilot holdouts."""
import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import PUBLIC, SPLITS, _load, digest, load_recipe, load_split, prepare, write_json, write_jsonl
from probe import PARENT, REVISION
from experiments.lumi.corpus_filters import filter_records, identifiers


def main(out, prior, all_source_rows=False, metadata_path=None, resume_english=False):
    out.mkdir(parents=True, exist_ok=True)
    if (out / "english" / "manifest.json").exists() and not resume_english:
        raise FileExistsError("Full corpus already exists; inspect it rather than overwrite it")
    if resume_english:
        original = out / "english" / "manifest-before-prior-holdout-exclusion.json"
        current = out / "english" / "manifest.json"
        if (out / "preparation.json").exists() or digest(original) != digest(current):
            raise ValueError("Resume requires the untouched pre-filter manifest and no completed preparation")
        # Verify every file before changing any of them.
        for split in SPLITS:
            load_split(out / "english", split)
    repo = Path(__file__).resolve().parents[2]
    cfg = load_recipe(repo / "recipes/qwen3-1.7b.yaml")
    cfg.update(parent=PARENT, revision=REVISION)
    for item in cfg["data"]["custom"]:
        item["path"] = str(repo / item["path"])
    cfg["data"].update(out=str(out / "english"), demo_dir=str(repo / "demo"))
    cfg["train"].update(language_balance={"it": .5, "en": .5}, eval_batch=2)
    cfg["teacher"].update(batch_tokens=4096)
    source_metadata = json.loads(metadata_path.read_text())["sources"] if metadata_path else None
    available = {}
    if all_source_rows:
        for name, spec in PUBLIC.items():
            repo_id, config, _, split, *_ = spec
            revision = cfg["data"]["sources"][name]["revision"]
            available[name] = len(_load(repo_id, config, split, revision))
            print("Available source training rows", name, available[name], flush=True)
        cfg["data"].update(pool_per_source=max(available.values()), train_cap_per_source=max(available.values()))
        # Public sources have finite full splits; generated policies do not.
        cfg["data"]["policy"].update(composition_groups_per_shape=480, contrastive_pairs_per_family=720,
                                      train_cap=20000, drop_cross_split_duplicate_groups=True)
    if resume_english:
        if json.loads((out / "base-recipe.json").read_text()) != cfg:
            raise ValueError("Resume recipe differs from the saved recipe")
        manifest = json.loads((out / "english" / "manifest.json").read_text())
    else:
        write_json(out / "base-recipe.json", cfg)
        manifest = prepare(cfg, source_metadata=source_metadata)
        write_json(out / "english" / "manifest-before-prior-holdout-exclusion.json", manifest)
    previous = {s: load_split(prior / "data", s) for s in SPLITS if s != "train"}
    protected = {s: set().union(*(identifiers(r) for r in rows)) for s, rows in previous.items()}
    all_holdouts = set().union(*protected.values())
    final_holdouts = set().union(*(protected[s] for s in ("test", "unseen", "showcase")))
    audit = {}
    for split in SPLITS:
        records = load_split(out / "english", split)
        forbidden = all_holdouts if split == "train" else final_holdouts if split in ("dev", "calibration") else set()
        kept, audit[split] = filter_records(records, forbidden, deduplicate=split in ("train", "dev", "calibration"))
        assert kept and not any(identifiers(r) & forbidden for r in kept)
        path = out / "english" / f"{split}.jsonl"
        write_jsonl(path, kept)
        qs = Counter(q["type"] for r in kept for q in r["request"]["questions"].values())
        manifest["files"][path.name] = {"sha256": digest(path), "records": len(kept), "questions": sum(qs.values())}
        manifest["counts"][split] = {"by_source": dict(Counter(r["source_family"] for r in kept)),
                                    "questions_by_primitive": dict(qs),
                                    "by_schema_family": dict(Counter(r["schema_family"] for r in kept))}
    manifest["prior_holdout_exclusion"] = {"prior_manifest_sha256": digest(prior / "data" / "manifest.json"),
                                          "rule": "Group, normalized source-text hash or source-row identity; all prior holdouts excluded from train, prior final panels excluded from dev/calibration",
                                          "audit": audit}
    manifest["expansion"] = {"all_source_rows": all_source_rows, "source_train_rows_available": available,
                             "cached_source_manifest_sha256": digest(metadata_path) if metadata_path else None}
    manifest["label_conflict_rule"] = "Drop all whole groups containing identical requests with different gold labels; no majority vote or relabeling"
    manifest["postprocessing_code_sha256"] = {p.name: digest(p) for p in
        (Path(__file__), Path(__file__).with_name("corpus_filters.py"))}
    write_json(out / "english" / "manifest.json", manifest)
    old_cache = prior / "translations-vllm-quoted-fewshot-v3.jsonl"
    new_cache = out / old_cache.name
    if not new_cache.exists():
        shutil.copyfile(old_cache, new_cache)
    write_json(out / "preparation.json", {"status": "english_prepared_translation_and_review_pending",
        "scope": ("All available public source training rows considered, then label/context/deduplication filters and grouped holdout split; 10x finite policy generation"
                  if all_source_rows else "Full checked-in IluvatarLabs Kev recipe, not every raw row of each public dataset or Jared Palmer's separate release corpus"),
        "source_train_rows_available": available,
        "recipe_sha256": digest(out / "base-recipe.json"), "english_manifest_sha256": digest(out / "english" / "manifest.json"),
        "records": {s: manifest["files"][f"{s}.jsonl"]["records"] for s in SPLITS}})
    print((out / "preparation.json").read_text(), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prior", type=Path, required=True)
    ap.add_argument("--all-source-rows", action="store_true")
    ap.add_argument("--source-metadata", type=Path)
    ap.add_argument("--resume-english", action="store_true")
    a = ap.parse_args()
    main(a.out, a.prior, a.all_source_rows, a.source_metadata, a.resume_english)
