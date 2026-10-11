"""Freeze a small paired Okapi panel; no training or translation generation."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

SEED = 20261003
SOURCES = {
    "MMLU": ("m_mmlu", "test", "18e6c8e65b2010a9819fcd8152718b17f8c551a7"),
    "HellaSwag": ("m_hellaswag", "val", "9d31dc982bd6285e081e3e3136332a38b9c1d7b7"),
    "ARC-Challenge": ("m_arc", "test", "69b0991ee606079105c4f9e271bcc1fef0014e03"),
}
REPOS = {"decision-index": "87d4650b42b377c0291a89c1f1a879f9b31082bf",
         "lm-evaluation-harness": "d6de81643928d653435c431bae19945d41d32520"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_objects(path):
    # Upstream .jsonl files contain pretty-printed, multiline JSON objects.
    text = Path(path).read_text()
    decoder, pos, rows = json.JSONDecoder(), 0, []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            break
        obj, pos = decoder.raw_decode(text, pos)
        rows.append(obj)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate source IDs")
    return {r["id"]: r for r in rows}


def mc_options(row):
    pairs = [(letter, row.get("option_" + letter.lower())) for letter in "ABCDE"]
    pairs = [(letter, value) for letter, value in pairs if value]
    keys, options = zip(*pairs)
    # Preserve the gold's original letter before compacting missing slots.
    return list(options), keys.index(str(row["answer"]).strip())


def normalize(value):
    return " ".join(str(value).casefold().split())


def prepare(root, out):
    from huggingface_hub import hf_hub_download
    refs = root / "references"
    for repo, revision in REPOS.items():
        actual = subprocess.check_output(["git", "-C", str(refs / repo), "rev-parse", "HEAD"], text=True).strip()
        assert actual == revision, (repo, actual)
    sys.path.insert(0, str(refs / "decision-index"))
    from decision_index.suite.build.layout import choice_row
    from decision_model.schema import DecisionRequest

    def module(task):
        p = refs / "lm-evaluation-harness/lm_eval/tasks/okapi" / task / "utils.py"
        spec = importlib.util.spec_from_file_location(task, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    arc, hella = module("arc_multilingual"), module("hellaswag_multilingual")
    out.mkdir(parents=True, exist_ok=False)
    rows, audit, files = [], {}, {}
    for family, (name, split, revision) in SOURCES.items():
        langs = {}
        for lang in ("en", "it"):
            path = Path(hf_hub_download("alexandrainst/" + name, f"data/{lang}/{split}.jsonl",
                repo_type="dataset", revision=revision, local_dir=refs / "okapi-data" / name))
            files[str(path)] = digest(path)
            langs[lang] = read_objects(path)
        common = sorted(set(langs["en"]) & set(langs["it"]))
        eligible, rejected = {}, []
        for uid in common:
            pair = []
            try:
                for lang in ("en", "it"):
                    r = langs[lang][uid]
                    if family == "HellaSwag":
                        ctx = r["ctx_a"] + " " + r["ctx_b"].capitalize()
                        query = hella.preprocess(r["activity_label"] + ": " + ctx)
                        options = [hella.preprocess(x) for x in r["endings"]]
                        gold = int(str(r["label"]).strip())
                        prompt = ("Which continuation is most plausible?" if lang == "en" else
                                  "Quale continuazione è più plausibile?") + "\n" + query
                    else:
                        query = r["instruction"].strip()
                        options, gold = mc_options(r)
                        if family == "ARC-Challenge":
                            query = arc.preprocess(query)
                            options = [arc.preprocess(x) for x in options]
                        prompt = query
                    assert query and all(isinstance(x, str) and x.strip() for x in options)
                    assert len(set(options)) == len(options) and 0 <= gold < len(options)
                    item = choice_row(family, split, uid + ":" + lang, prompt, options, gold,
                                      dataset="alexandrainst/" + name, revision=revision)
                    item.update(language=lang, pair_id=uid, subject=uid.split("/")[0] if family == "MMLU" else None,
                                overlap_query=query)
                    DecisionRequest.model_validate({"state": item["state"], "questions": item["questions"]})
                    pair.append(item)
                assert len(pair[0]["questions"]["q1"]["criteria"]) == len(pair[1]["questions"]["q1"]["criteria"])
                eligible[uid] = pair
            except (ValueError, AssertionError, KeyError, TypeError) as error:
                rejected.append({"id": uid, "reason": str(error) or type(error).__name__})
        order = lambda uid: hashlib.sha256(f"{SEED}:{family}:{uid}".encode()).hexdigest()
        if family == "MMLU":
            strata = defaultdict(list)
            for uid in eligible:
                strata[uid.split("/")[0]].append(uid)
            assert len(strata) == 57
            selected = [uid for subject in sorted(strata) for uid in sorted(strata[subject], key=order)[:4]]
            assert len(selected) == 228
        else:
            selected = sorted(eligible, key=order)[:200]
            assert len(selected) == 200
        rows.extend(r for uid in selected for r in eligible[uid])
        audit[family] = {"raw_counts": {k: len(v) for k, v in langs.items()}, "common_ids": len(common),
                         "eligible_pairs": len(eligible), "selected_pairs": len(selected), "rejected_pairs": rejected,
                         "different_gold_positions": sum(p[0]["expected"] != p[1]["expected"] for p in eligible.values())}

    # Exact whole-field match only: this is not a claim of complete decontamination.
    queries = {normalize(r["overlap_query"]) for r in rows}
    overlaps, families = [], Counter()
    train = root / "runs/bilingual-all-v1/data-reviewed/train.jsonl"
    with train.open() as stream:
        for line in stream:
            r = json.loads(line)
            families[r["source_family"]] += 1
            req = r["request"]
            fields = [req["state"]] + [q.get("instructions", "") for q in req["questions"].values()]
            if any(isinstance(x, str) and normalize(x) in queries for x in fields):
                overlaps.append(r["record_id"])
    assert not overlaps, ("Evaluation query matches training input", overlaps)
    assert not any(any(t in x.lower() for t in ("mmlu", "hellaswag", "arc")) for x in families)
    live = root / "runs/bilingual-all-v1/full-gold"
    metrics = json.loads((live / "training_metrics.json").read_text())
    checkpoint = Path(metrics["selected_path"])
    shutil.copytree(checkpoint, out / "checkpoint")
    cp_hashes = {str(p.relative_to(out / "checkpoint")): digest(p) for p in (out / "checkpoint").rglob("*") if p.is_file()}
    dest = out / "rows.jsonl"
    dest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    manifest = {"status": "prepared", "seed": SEED, "repositories": REPOS, "sources": SOURCES,
        "source_files_sha256": files, "rows_sha256": digest(dest), "records": len(rows), "audit": audit,
        "selection": "Four pairs per MMLU subject; 200 pairs per other task; SHA256 order; common source IDs; zero shot",
        "checkpoint_step": metrics["selected_step"], "checkpoint_selected_by": "existing training dev NLL before external evaluation",
        "checkpoint_files_sha256": cp_hashes, "training_manifest_sha256": digest(train.parent / "manifest.json"),
        "training_sources": dict(families), "exact_training_field_overlaps": overlaps,
        "limitations": ["Exploratory subset, not a full Decision Index score or official lm-eval run",
            "Okapi translations and each language's source option order/labels are retained; translation quality is not certified",
            "HellaSwag retains Okapi activity labels, which can remain English in Italian rows",
            "Decision Index choice_row format with Okapi preprocessing; no full-suite hash parity is claimed",
            "MMLU subject-balanced sample differs from full-test micro weighting",
            "Only exact full-field training overlap checked; parent pretraining contamination is unknown",
            "No external labels used for training, calibration, or checkpoint selection"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"records": len(rows), "checkpoint_step": metrics["selected_step"], "audit": audit}, indent=2), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    prepare(args.root, args.out)
