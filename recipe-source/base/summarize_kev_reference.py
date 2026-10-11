"""Compare published Kev and Nesso2 outputs on identical, checksum-verified items."""
import argparse
import json
from pathlib import Path

from run_bilingual_pilot import approved_data, summarize
from summarize_pilot import accuracy_delta
from decision_model.data import digest, load_split, read_jsonl, write_json


def key(row):
    return row["record_id"], row["qid"]


def main(root):
    approved_data(root)
    out = root / "kev-reference"
    refs = {m: json.loads((out / m / "report.json").read_text()) for m in ("kev08b", "kev4b")}
    assert all(r["status"] == "complete" for r in refs.values())
    manifest = digest(root / "data" / "manifest.json")
    assert all(r["config"]["data_manifest_sha256"] == manifest for r in refs.values())
    result = {"manifest_sha256": manifest, "references": refs, "panels": {}, "deltas_vs_gold": {}}
    lines = ["# Published Kev vs Nesso2 decision models", "",
             "Measured on the same unchanged bilingual-v2 examples. Accuracy is per question.",
             "Gold-only Nesso2 was selected before this comparison, using development data.", "",
             "| Panel | System | Language | Questions | Accuracy | NLL | ECE |",
             "|---|---|---|---:|---:|---:|---:|"]
    for split in ("test", "unseen"):
        records = load_split(root / "data", split)
        official_ids = {r["record_id"] for r in records if r["provenance"].get("repo") and
                        r["provenance"].get("split") in ("test", "validation", "validation_matched")}
        systems = {m: read_jsonl(root / m / f"{split}-calibrated.jsonl") for m in ("gold", "distilled")}
        systems.update({m: read_jsonl(out / m / f"{split}.jsonl") for m in refs})
        lookups = {m: {key(r): r for r in rows} for m, rows in systems.items()}
        assert all(len(lookups[m]) == len(rows) for m, rows in systems.items()), "Duplicate question IDs"
        common = set.intersection(*(set(rs) for rs in lookups.values()))
        for k in common:
            assert all(rs[k]["keys"] == lookups["gold"][k]["keys"] and
                       rs[k]["label"] == lookups["gold"][k]["label"] for rs in lookups.values())
        result.setdefault("coverage", {})[split] = {m: len(rows) for m, rows in systems.items()}
        subsets = {split: common}
        if split == "test":
            subsets["official_test_only"] = {k for k in common if k[0] in official_ids}
        for panel, selected in subsets.items():
            rows = {m: [r for r in rs if key(r) in selected] for m, rs in systems.items()}
            result["panels"][panel] = {m: summarize(rs) for m, rs in rows.items()}
            result["deltas_vs_gold"][panel] = {m: {
                lang: accuracy_delta([r for r in rows[m] if r["language"] == lang],
                                     [r for r in rows["gold"] if r["language"] == lang])
                for lang in ("en", "it")} for m in refs}
            for m, summary in result["panels"][panel].items():
                for lang, s in summary["by_language"].items():
                    lines.append(f"| {panel} | {m} | {lang} | {s['questions']} | {s['accuracy']:.4f} | {s['nll']:.4f} | {s['ece_10']:.4f} |")
    limitations = [
        "Published references are jaredpalmer/kev, a separate implementation from the IluvatarLabs converter in this workspace.",
        "Published Kev uses larger backbones and substantially larger/different training corpora; this is not a controlled architecture comparison.",
        "Our full test includes rows reserved from public training pools and generated policies. Released-Kev training overlap has not been ruled out.",
        "Official-test-only excludes those training-pool and generated/custom records, but cannot prove absence of base-model pretraining or prior evaluation exposure.",
        "Unseen sources means unseen by our Nesso2 pilot training; it is not a guarantee about every upstream model's history.",
        "Reference inference is FP32 with its shipped temperature; Nesso2 inference uses BF16 exports with temperatures fitted only on our calibration split.",
        "Italian is machine translated; the dataset is small. No model was trained, calibrated or selected using these new test results.",
    ]
    result["limitations"] = limitations
    lines.extend(["", *["- " + s for s in limitations], "", "Pinned references:", ""])
    for name, r in refs.items():
        c = r["config"]["identity"]
        lines.append(f"- {name}: `{c['model']}@{c['revision']}`, base `{c['base']}@{c['base_revision']}`.")
    write_json(out / "comparison.json", result)
    (out / "comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    main(ap.parse_args().root)
