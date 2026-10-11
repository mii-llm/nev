"""Release the unchanged English selection cases independently of Italian translation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from prepare_decision_subset import CATALOG, digest, dumps, jsonl, load, save


def main(root, source, out, *, language="en", translated_rows=None, translation_review=None):
    original = json.loads((source / "manifest.json").read_text())
    assert digest(source / "english.jsonl") == original["english_sha256"]
    assert not json.loads((source / "overlap-audit.json").read_text())["exact_matches"]
    assert not (out / "manifest.json").exists(), "Do not overwrite an existing panel"
    rows = [r for r in load(source / "english.jsonl") if r["panel"] == "selection"]
    assert Counter(r["family"] for r in rows) == {"ANLI": 150, "CLINC150+OOS": 151, "When2Call MCQ": 150}
    assert len({r["group_id"] for r in rows}) == len(rows)
    assert language in ("en", "it")
    if language == "it":
        assert translated_rows is not None and translation_review is not None
        assert [r["pair_id"] for r in rows] == [r["pair_id"] for r in translated_rows]
        for en, it in zip(rows, translated_rows):
            assert en["expected"] == it["expected"] and en["group_id"] == it["group_id"]
            assert list(en["questions"]) == list(it["questions"])
            for key in en["questions"]:
                assert list(en["questions"][key]["criteria"]) == list(it["questions"][key]["criteria"])
        rows = translated_rows
    frozen = root / "runs/bilingual-all-v1/training-source"
    old_report = json.loads((root / "runs/bilingual-all-v1/decision-index-okapi-v1/results/report.json").read_text())
    runtime = old_report["frozen_runtime_sha256"]
    for path, expected in runtime.items():
        assert digest(frozen / path) == expected, path
    sys.path.insert(0, str(frozen))
    from transformers import AutoTokenizer
    from decision_model.render import encode_request
    from decision_model.schema import AdmissionError, DecisionRequest
    (out / "checkpoints").mkdir(exist_ok=True)
    for step, files in original["checkpoint_files_sha256"].items():
        checkpoint = source / "checkpoints" / step
        for path, expected in files.items():
            assert digest(checkpoint / path) == expected
        (out / "checkpoints" / step).symlink_to(checkpoint, target_is_directory=True)
    cp = json.loads((source / "checkpoints/74000/run.json").read_text())
    tok = AutoTokenizer.from_pretrained(cp["parent"], revision=cp["revision"], local_files_only=True)
    audit = []
    for row in rows:
        row.update(id=row["pair_id"] + ":" + language, model="nesso2", language=language)
        payload = {key: row[key] for key in ("model", "state", "questions")}
        request = DecisionRequest.model_validate(payload)
        item = {"id": row["id"], "family": row["family"], "language": language, "panel": "selection"}
        try:
            encoded, _ = encode_request(tok, request)
            item.update(status="supported", tokens=len(encoded["ids"]))
        except AdmissionError as error:
            item.update(status="unsupported", reason=str(error))
        audit.append(item)
        row["_evaluation"] = {"run_id": "nesso-" + language + "-selection-v1:" + row["id"],
            "catalog_id": CATALOG[row["family"]], "dataset": row["family"], "track": row["stratum"],
            "group_id": row["group_id"], "language": language, "panel": "selection", "pair_id": row["pair_id"],
            "payload_sha256": hashlib.sha256(dumps(payload).encode()).hexdigest()}
    jsonl(out / "selection.jsonl", rows)
    save(out / "capacity-audit.json", audit)
    manifest = {"status": "ready_for_" + language + "_selection", "language": language,
        "decision_index_revision": original["decision_index_revision"],
        "source_manifest_sha256": digest(source / "manifest.json"), "english_sha256": original["english_sha256"],
        "panel_sha256": {"selection": digest(out / "selection.jsonl")},
        "capacity_audit_sha256": digest(out / "capacity-audit.json"),
        "checkpoint_files_sha256": original["checkpoint_files_sha256"], "frozen_runtime_sha256": runtime,
        "code_sha256": {},
        "evaluation_files_sha256": {p.name: digest(p) for p in (out / "preparation-source").iterdir() if p.is_file()},
        "limitations": original["limitations"] + [language + " selection cases only; confirmation remains unused", "Source-provided labels and option order retained"]}
    if translation_review is not None:
        manifest["translation_review"] = translation_review
    save(out / "manifest.json", manifest)
    save(out / "quality-review.json", {"status": "approved_for_diagnostic", "panel_sha256": manifest["panel_sha256"],
        "scope": language + " selection panel only", "reviewer": "Codex structural/provenance and limited translation review",
        "checks": ["Frozen English checksum", "Original gold labels and option keys retained", "451 unique source groups", "Zero previously audited exact English training-text matches", "Native schema and tokenizer capacity audit", "Checkpoint and frozen runtime hash validation"],
        "translation_review": translation_review,
        "limitations": "No claim of flawless source labels, absent pretraining contamination, or exhaustive Italian semantic review."})
    print(json.dumps({"status": manifest["status"], "requests": len(rows),
                      "capacity": dict(Counter(r["family"] + "/" + r["status"] for r in audit))}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main(args.root, args.source, args.out)
