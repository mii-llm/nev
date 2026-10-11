"""Produce a compact comparison after both trained runs and baselines finish."""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from run_bilingual_pilot import summarize
from decision_model.data import read_jsonl, write_json


def accuracy_delta(a, b, repetitions=1000):
    """Paired bootstrap of complete semantic groups; a minus b accuracy."""
    lookup = {(r["record_id"], r["qid"]): r for r in b}
    groups = defaultdict(list)
    def correct(r):
        return int(max(range(len(r["probs"])), key=r["probs"].__getitem__) == r["label"])
    for r in a:
        other = lookup[(r["record_id"], r["qid"])]
        assert r["keys"] == other["keys"] and r["label"] == other["label"]
        groups[r["group_id"]].append(correct(r) - correct(other))
    totals = [(sum(v), len(v)) for v in groups.values()]
    rng = random.Random(20260929)
    samples = []
    for _ in range(repetitions):
        selected = rng.choices(totals, k=len(totals))
        samples.append(sum(s for s, n in selected) / sum(n for s, n in selected))
    samples.sort()
    return {"accuracy_difference": sum(s for s, n in totals) / sum(n for s, n in totals),
            "interval_95_percent": [samples[int(.025 * repetitions)], samples[int(.975 * repetitions)]],
            "semantic_groups": len(totals), "bootstrap_repetitions": repetitions,
            "note": "Exploratory paired group bootstrap; does not capture seed, translation or teacher-selection uncertainty."}


def main(root):
    reports = {m: json.loads((root / m / "report.json").read_text()) for m in ("gold", "distilled")}
    assert all(r["status"] == "complete" for r in reports.values())
    # Select using development performance only, before inspecting final test results.
    selected = min(reports, key=lambda m: reports[m]["panels"]["dev"]["raw"]["source_language_macro_record_nll"])
    result = {"selected_by_dev": selected,
              "selection_rule": "minimum exported model raw dev source/language macro record NLL",
              "teacher_comparison": json.loads((root / "comparison" / "selection.json").read_text()),
              "manifest_counts": json.loads((root / "data" / "manifest.json").read_text())["counts"],
              "full_panels": {m: r["panels"] for m, r in reports.items()}, "common_eligible_panels": {},
              "distilled_minus_gold_accuracy": {}}
    lines = ["# Nesso2 bilingual pilot results", "", f"Selected by development NLL: **{selected}**.", "",
             "50% Italian / 50% English by records and training loss. Synthetic Italian; single seed; pilot only.", "",
             "The following comparison uses exactly the questions eligible for both language-model baselines.", "",
             "| Panel | System | Language | Questions | Accuracy | NLL | ECE |",
             "|---|---|---|---:|---:|---:|---:|"]
    for panel in ("test", "unseen"):
        rows = {m: read_jsonl(root / m / f"{panel}-calibrated.jsonl") for m in reports}
        result["distilled_minus_gold_accuracy"][panel] = {
            lang: accuracy_delta([r for r in rows["distilled"] if r["language"] == lang],
                                 [r for r in rows["gold"] if r["language"] == lang]) for lang in ("en", "it")}
        rows.update({m: read_jsonl(root / "baselines" / f"{m}-{panel}.jsonl") for m in ("original_nesso2", "selected_teacher")})
        common = set.intersection(*({(r["record_id"], r["qid"]) for r in rs} for rs in rows.values()))
        result["common_eligible_panels"][panel] = {}
        for name, rs in rows.items():
            summary = summarize([r for r in rs if (r["record_id"], r["qid"]) in common])
            result["common_eligible_panels"][panel][name] = summary
            for lang, s in summary["by_language"].items():
                lines.append(f"| {panel} | {name} | {lang} | {s['questions']} | {s['accuracy']:.3f} | {s['nll']:.3f} | {s['ece_10']:.3f} |")
    lines.extend(["", "Full question coverage, including Banking77, is recorded separately in summary.json.",
                  "Exported students use fitted calibration temperatures; language-model baselines use uncalibrated cyclic label probabilities.",
                  "Original-model and selected-teacher baselines do not select the artifact. No test result controls training or selection.", ""])
    write_json(root / "summary.json", result)
    (root / "SELECTED_MODEL.txt").write_text(str(root / selected / "model") + "\nSelected using development data only; pilot artifact, not a production release.\n")
    (root / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    main(ap.parse_args().root)
