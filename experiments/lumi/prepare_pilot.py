"""Download pinned Kev sources and prepare the English half of a modest pilot.

Run on the login node for data preparation only; model inference uses Slurm.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import load_recipe, prepare
from probe import PARENT, REVISION


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    cfg = load_recipe(repo / "recipes/qwen3-1.7b.yaml")
    cfg.update(parent=PARENT, revision=REVISION)
    d = cfg["data"]
    for entry in d["custom"]:
        entry["path"] = str(repo / entry["path"])
    d["demo_dir"] = str(repo / "demo")
    d.update(out=str(a.out / "english"), pool_per_source=160,
             train_cap_per_source=100, official_test_per_source=20,
             showcase_per_source={k: 4 for k in d["showcase_per_source"]},
             variants_per_source=1, unseen_per_source=20)
    d["policy"].update(composition_groups_per_shape=4, contrastive_pairs_per_family=6,
                       train_cap=160, heldout_groups_per_shape=2,
                       heldout_contrastive_pairs=4, showcase_heldout_pairs=2)
    cfg["train"].update(language_balance={"it": .5, "en": .5}, eval_every=100, eval_batch=2)
    cfg["teacher"].update(batch_tokens=4096)
    (a.out / "base-recipe.json").write_text(json.dumps(cfg, indent=2) + "\n")
    manifest = prepare(cfg)
    print(json.dumps(manifest["files"], indent=2), flush=True)


if __name__ == "__main__":
    main()
