"""Create a separate reviewed corpus; preserve the original translation output."""
import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from decision_model.data import SPLITS, _check_disjoint, digest, load_split, write_json, write_jsonl
from experiments.lumi.bilingual_data import validate_pair

CORRECTIONS = {
    "returns": "resi",
    "entailment": "implicazione",
    "contradiction": "contraddizione",
    "is it illegal to have brass knuckles in canada?": "è illegale possedere un tirapugni in Canada?",
}


def correct_schema(en, it, counts):
    if isinstance(en, str):
        if en in CORRECTIONS and it != CORRECTIONS[en]:
            counts[en] += 1
            return CORRECTIONS[en]
        return it
    if isinstance(en, dict):
        return {k: correct_schema(v, it[k], counts) for k, v in en.items()}
    if isinstance(en, list):
        return [correct_schema(a, b, counts) for a, b in zip(en, it)]
    return it


def untranslated_hypothesis(en, it):
    if en["source_family"] != "mnli":
        return False
    for qid, q in en["request"]["questions"].items():
        a, b = q["instructions"], it["request"]["questions"][qid]["instructions"]
        if isinstance(a, dict):
            a, b = a["question"], b["question"]
        # Source wrapper is fixed by the pinned converter; variants use the same quotes.
        match = re.search(r'"(.*)"', a)
        if match and len(match[1].split()) >= 4 and match[1].casefold() in b.casefold():
            return True
    return False


def run(root):
    original = root / "data"
    out = root / "data-reviewed"
    if out.exists():
        raise FileExistsError("Reviewed output exists; do not silently overwrite a training input")
    out.mkdir()
    manifest = copy.deepcopy(json.loads((original / "manifest.json").read_text()))
    audit = {}
    # Check group isolation without retaining all decoded corpora simultaneously.
    owners = {}
    for split in SPLITS:
        records = load_split(original, split)
        rejected, corrections = set(), Counter()
        assert len(records) % 2 == 0
        for i in range(0, len(records), 2):
            en, it = records[i:i+2]
            assert en["language"] == "en" and it["language"] == "it"
            assert en["provenance"]["parallel_record"] == it["provenance"]["parallel_record"]
            assert en["group_id"] == it["group_id"] and en["supervision"] == it["supervision"]
            validate_pair(en["request"], it["request"])
            if untranslated_hypothesis(en, it):
                rejected.add(en["group_id"])
        kept = []
        for i in range(0, len(records), 2):
            en, it = records[i:i+2]
            if en["group_id"] in rejected:
                continue
            it["request"]["questions"] = correct_schema(en["request"]["questions"], it["request"]["questions"], corrections)
            validate_pair(en["request"], it["request"])
            for r in (en, it):
                for key in (("group", r["group_id"]), ("text", r["source_family"], r["language"], r["provenance"]["rendered_state_sha256"])):
                    if owners.setdefault(key, split) != split:
                        raise ValueError("Cross-split overlap in reviewed data")
            kept.extend((en, it))
        _check_disjoint({split: kept})
        counts = Counter(r["language"] for r in kept)
        assert counts["en"] == counts["it"] and counts["en"] > 0
        path = out / f"{split}.jsonl"
        write_jsonl(path, kept)
        manifest["files"][path.name] = {"sha256": digest(path), "records": len(kept),
                                      "questions": sum(len(r["supervision"]) for r in kept)}
        manifest["counts"][split] = {"language": dict(counts), "source": dict(Counter(r["source_family"] for r in kept))}
        audit[split] = {"removed_groups": sorted(rejected), "removed_records": len(records)-len(kept),
                        "schema_corrections": dict(corrections)}
        print(split, dict(counts), "removed records", len(records)-len(kept), flush=True)
    manifest["review_postprocessing"] = {"original_manifest_sha256": digest(original / "manifest.json"),
        "code_sha256": digest(__file__), "corrections": CORRECTIONS, "audit": audit,
        "rule": "Exclude whole bilingual groups with verbatim English NLI hypotheses of at least four words; correct exact known schema translations; keep stable labels and states unchanged"}
    write_json(out / "manifest.json", manifest)
    reviewed = [json.loads(l) for l in (root / "translation-audit.jsonl").read_text().splitlines()]
    write_json(out / "quality-review.json", {"status": "approved_for_training", "manifest_sha256": digest(out / "manifest.json"),
        "reviewer": "Codex semantic spot review, not independent native-speaker certification",
        "reviewed_record_ids": [r["record_id"] for r in reviewed], "sample_pairs": len(reviewed)//2,
        "scope": "36 paired train/dev examples across nine sources; banking option descriptions only partially inspected; all pairs checked structurally",
        "findings": ["Corrected returns/residui, bare NLI label descriptions, and brass-knuckles/boxing-gloves question mistranslation",
                     "Excluded unchanged English hypotheses from Italian NLI prompts with all group siblings",
                     "Some original source labels and truncated source texts remain noisy; labels were not subjectively relabeled"],
        "limitations": ["Small semantic sample cannot certify 700k examples; residual translation errors remain possible",
                        "Italian remains synthetic; 50/50 means records and update weight, not tokens",
                        "Natural source mixture is dominated by MNLI; report macro source/language validation too"]})
    print("Reviewed manifest", digest(out / "manifest.json"), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    run(ap.parse_args().root)
