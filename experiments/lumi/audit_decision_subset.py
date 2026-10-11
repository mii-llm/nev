"""CPU-only schema, pairing, capacity and source-integrity audit after translation."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from prepare_decision_subset import digest, load, save, map_request


def main(root, out):
    source = root / "runs/bilingual-all-v1/training-source"
    sys.path.insert(0, str(source))
    from transformers import AutoTokenizer
    from decision_model.schema import AdmissionError, DecisionRequest
    from decision_model.render import encode_request
    manifest = json.loads((out / "manifest.json").read_text())
    for path, expected in manifest["source_files_sha256"].items():
        assert digest(out / path) == expected
    for step, files in manifest["checkpoint_files_sha256"].items():
        for path, expected in files.items():
            assert digest(out / "checkpoints" / step / path) == expected
    cp = json.loads((out / "checkpoints/74000/run.json").read_text())
    tok = AutoTokenizer.from_pretrained(cp["parent"], revision=cp["revision"], local_files_only=True)
    audit, pairs, groups = [], defaultdict(list), defaultdict(set)
    collisions = []
    for panel in ("selection", "confirmation"):
        assert digest(out / (panel + ".jsonl")) == manifest["panel_sha256"][panel]
        for row in load(out / (panel + ".jsonl")):
            pairs[row["pair_id"]].append(row)
            groups[row["group_id"]].add(panel)
            req = DecisionRequest.model_validate({"state": row["state"], "questions": row["questions"]})
            item = {"id": row["id"], "family": row["family"], "language": row["language"], "panel": panel}
            try:
                encoded, _ = encode_request(tok, req)
                item.update(status="supported", tokens=len(encoded["ids"]))
            except AdmissionError as exc:
                item.update(status="unsupported", reason=str(exc))
            audit.append(item)
            for qid, q in row["questions"].items():
                inverse = defaultdict(list)
                for key, value in q["criteria"].items():
                    inverse[" ".join(value.casefold().split())].append(key)
                if any(len(keys) > 1 for keys in inverse.values()):
                    collisions.append({"id": row["id"], "question": qid,
                                       "collisions": {text: keys for text, keys in inverse.items() if len(keys) > 1}})
    assert all(len(value) == 1 for value in groups.values()), "Source group crosses panels"
    assert len(pairs) == 902 and all(len(rs) == 2 for rs in pairs.values())
    for rs in pairs.values():
        en, it = sorted(rs, key=lambda r: r["language"])
        assert [en["language"], it["language"]] == ["en", "it"]
        assert en["expected"] == it["expected"]
        for qid in en["questions"]:
            assert list(en["questions"][qid]["criteria"]) == list(it["questions"][qid]["criteria"])
        if en["family"] == "When2Call MCQ":
            def strip_descriptions(value):
                if isinstance(value, dict):
                    return {key: strip_descriptions(v) for key, v in value.items() if key != "description"}
                if isinstance(value, list):
                    return [strip_descriptions(v) for v in value]
                return value
            assert strip_descriptions(en["state"]["tools"]) == strip_descriptions(it["state"]["tools"])
    save(out / "capacity-audit.json", audit)
    save(out / "translation-option-collisions.json", collisions)
    counts = Counter(r["family"] + "/" + r["language"] + "/" + r["status"] for r in audit)
    manifest.update(capacity_counts=dict(counts), capacity_audit_sha256=digest(out / "capacity-audit.json"),
        option_collision_rows=len(collisions),
        frozen_runtime_sha256={str(p.relative_to(source)): digest(p) for p in (source / "decision_model").rglob("*.py")},
        evaluation_files_sha256={p.name: digest(p) for p in (out / "preparation-source").iterdir() if p.is_file()},
        status="awaiting_semantic_review")
    save(out / "manifest.json", manifest)
    print(json.dumps({"capacity": counts, "option_collision_rows": len(collisions), "status": manifest["status"]}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main(args.root, args.out)
