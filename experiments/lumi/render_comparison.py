"""Render the verified comparison and historical panels without mixing denominators."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/nesso2"
EVIDENCE = DOC / "evidence"


def pct(x):
    return "—" if x is None else f"{100*x:.2f}%"


def name(x):
    if x == "v2_74k_plus_256": return "Selected v2: 74k + 256"
    if x == "laya": return "Laya multilingual"
    if x == "parent": return "Original Nesso2 parent"
    if x.startswith("nesso_"): return "Nesso2 " + x[6:]
    return x


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def model_order(model):
    if model == "parent": return (0, 0)
    if model.startswith("nesso_"): return (1, int(model[6:]))
    if model == "v2_74k_plus_256": return (2, 0)
    return (3, 0)


def main():
    report = json.loads((EVIDENCE / "latest-comparison-report.json").read_text())
    assert report["status"] == "complete"
    out = ["# Nesso2 and Laya: complete comparison", "Generated from preserved results, 10 October 2026.",
           "The latest selected candidate is **74k + 256 practical-v2 updates**. The training run ended at +640; +256 was selected by development NLL before its final test. No checkpoint was reselected from the comparisons below.",
           "All numbers are accuracy. EN and IT are shown separately. These are frozen diagnostic subsets, not official full-suite leaderboard scores. The panels were reused during development. Italian benchmark translations are synthetic; Decision Index Italian received partial review."]
    out += ["## Main findings", "The selected v2 model reaches **43.75% EN / 45.90% IT** on the practical test, versus Laya's **43.65% / 39.06%**. English differs by only one correct answer out of 1,024: treat it as tied. Italian differs by 70 correct answers (+6.84 percentage points). Relative to original 74k, v2 gains +4.39 EN / +6.35 IT points.",
            "On the 513 common Okapi cases per language, v2 scores 31.19% EN / 31.77% IT, compared with 74k's 30.60% / 31.38% and Laya's 30.02% / 27.10%. This is a small change from 74k, with no aggregate regression on this panel.",
            "Laya is stronger on ANLI and much stronger on CLINC intent classification. Nesso is stronger on the When2Call subset. Consequently the Decision Index aggregate depends on task weighting and coverage: read the per-task scores rather than declaring one universal winner. Practical improvements do not establish general reasoning capability.",
            "All 2,048 practical requests fit Laya. Three native probability ties were recorded and resolved by the documented first-semantic-key rule; native output probabilities are rounded to four decimal places. This reinforces treating the one-answer English difference as a tie.",
            "GPU job 22697632 completed with exit code 0 in 4m30s on one LUMI dev-g MI250X allocation. The 35 archived evidence files were verified individually after download."]
    titles = {"practical_v2": "Practical v2: unseen wording and facts", "okapi": "Okapi: ARC-Challenge, HellaSwag, MMLU", "decision_index": "Decision Index: ANLI, CLINC, When2Call"}
    for panel in ("practical_v2", "okapi", "decision_index"):
        p = report["panels"][panel]
        out += ["## " + titles[panel],
                f"Full panel: {p['full_requests']:,} requests. Bilingual common support: {p['common_bilingual_requests']:,} requests. Common support keeps a source case only if both EN and IT fit every listed model. Full-panel accuracy counts unsupported requests as wrong."]
        if panel == "practical_v2":
            out += ["Four synthetic rule families, 256 cases/task/language. Uniform random choice averages 35.42%. These results do not establish production readiness."]
        if panel == "decision_index":
            out += ["151 CLINC intents and 150 cases each for ANLI and When2Call per language. This is not the official Decision Index composite. When2Call was later deprioritized; it remains here for completeness."]
        for subset, title in (("common_bilingual", "Same supported bilingual cases"), ("full", "Full panel, including capacity failures")):
            if subset == "full" and p["common_bilingual_requests"] == p["full_requests"]:
                out += ["Full-panel and common-support results are identical here; no requests were excluded."]
                continue
            models = dict(sorted(p[subset].items(), key=lambda item:model_order(item[0])))
            out += ["### " + title]
            rows = []
            for model, m in models.items():
                en, it = (m["by_language"][l] for l in ("en", "it"))
                rows.append([name(model), pct(en["accuracy"]), pct(it["accuracy"]), f"{en['answered']}/{en['n']}", f"{it['answered']}/{it['n']}"])
            out += [table(["Model", "EN micro", "IT micro", "EN answered", "IT answered"], rows)]
            if panel == "decision_index":
                out += [table(["Model", "EN task-macro", "IT task-macro"], [[name(model),pct(m['by_language']['en']['task_macro_accuracy']),pct(m['by_language']['it']['task_macro_accuracy'])] for model,m in models.items()])]
            out += ["Per-task scores (same denominator for all models within this table):"]
            rows = []
            for cell in sorted(next(iter(models.values()))["cells"]):
                for model,m in models.items():
                    c=m["cells"][cell]
                    rows.append([cell,name(model),c["n"],pct(c["accuracy"])])
            out += [table(["Task/language","Model","N","Accuracy"],rows)]
    out += ["## Earlier practical v1: a different test", "512 requests per language. This panel uses different cases and wording from v2; compare models within a panel, not absolute scores between versions."]
    v1=json.loads((EVIDENCE/'practical-v1-report.json').read_text())
    out += [table(["Model", "EN", "IT"], [["74k + 512 (v1)" if m=='adapted-512' else 'Nesso2 '+m, pct(d['raw']['by_language']['en']['accuracy']),pct(d['raw']['by_language']['it']['accuracy'])] for m,d in v1['models'].items()])]
    out += ["Laya and the selected v2 model were not run on the v1 panel."]
    for version in ('v1','v2'):
        t=json.loads((EVIDENCE/f'practical-{version}-training.json').read_text())
        out += [f"### Practical {version} development history (not final test)", table(["Additional updates", "Dev EN", "Dev IT", "Dev macro NLL", "Guard passed"],[[r['name'],pct(r['dev']['by_language']['en']['accuracy']),pct(r['dev']['by_language']['it']['accuracy']),f"{r['dev']['macro_nll']:.5f}",r['eligible']] for r in t['history']])]
    f=json.loads((EVIDENCE/'full-training-report.json').read_text())
    out += ["## Full-data model: original-domain and unseen-source panels", "These are the exported **142k** model's scores, not the latest practical-v2 model. Laya was not measured on these panels. Training used 713,198 records, exactly half EN/half IT.", table(["Panel", "Questions/language", "EN", "IT"], [[p,d['by_language']['en']['questions'],pct(d['by_language']['en']['accuracy']),pct(d['by_language']['it']['accuracy'])] for p,d in f['panels'].items()])]
    out += ["## Earlier pilot and published Kev references", "Historical figures below come from the preserved LUMI README. The small pilot used only 1,684 training records. Published Kev uses larger backbones and may have seen some reserved training-pool examples. Its FP32 inference differs from the Nesso2 BF16 exports; this compares finished systems, not architectures in isolation.", table(["Model", "Pilot test EN (341)", "Pilot test IT (341)", "Unseen EN (57)", "Unseen IT (57)"],[['Small Nesso2 gold pilot','38.4%','36.4%','42.1%','33.3%'],['Small Nesso2 distilled pilot','37.0%','34.6%','38.6%','33.3%'],['Published Kev-0.8B','80.4%','73.6%','66.7%','45.6%'],['Published Kev-4B','84.8%','80.1%','75.4%','73.7%'],['Full-data Nesso2 142k',pct(f['panels']['prior_pilot_test']['by_language']['en']['accuracy']),pct(f['panels']['prior_pilot_test']['by_language']['it']['accuracy']),pct(f['panels']['prior_pilot_unseen']['by_language']['en']['accuracy']),pct(f['panels']['prior_pilot_unseen']['by_language']['it']['accuracy'])]]),
    "Pilot common eligible panel, excluding Banking77 from every model (303 questions per language):",
    table(['System','EN','IT'],[['Original Nesso2, cyclic LM scoring','41.9%','41.3%'],['Small gold decision pilot','42.9%','40.9%'],['Small distilled decision pilot','40.9%','38.9%'],['Nesso-4B teacher, cyclic LM scoring','74.6%','71.6%']]),
    "Official test/validation-only pilot subset (129 questions/language): gold pilot 42.6% EN / 38.8% IT; Kev-0.8B 85.3% / 81.4%; Kev-4B 83.7% / 79.8%. Pretraining exposure remains unknown.",
    "Teacher selection development panel (298 questions/language, not test): Nesso-4B 72.5% EN / 72.1% IT, macro record NLL 1.0894; Qwen-4B 72.8% / 69.8%, NLL 4.0458. Nesso-4B was selected, but that small distillation run did not establish an improvement over gold-only training.",
    "## Confidence and runtime", "Practical v2: no confidence threshold qualified for any Nesso candidate. Accepted coverage is zero; this does not mean zero prediction errors. Selected-model calibrated temperature is .73204, with 48 wrong Italian test predictions at confidence >=90%. Laya's confidence policy was not fitted on this panel.",
    "Practical v1: its .7 threshold failed on changed wording (EN accepted-case error 59.57%, IT 67.31%). The earlier confidence policy must not be used for deployment.",
    "Selected v2 batch-1 latency on AMD MI250X: median 72.06 ms, p95 80.92 ms, peak allocated memory 1.90 GiB. Includes tokenization, excludes model loading and networking; FP32 parameters with BF16 autocast. No matched Laya latency claim is made.",
    "## Provenance and interpretation", *['- '+s for s in report['limitations']],
    "- Scores near each other on these small samples are descriptive differences, not established improvements.",
    "- Nesso2 parent is a language-model scoring baseline; the fine-tuned checkpoints use the learned decision head.",
    "- Laya is convaiinnovations/laya-multilingual, pinned model revision e4e9ddf21a7b1903b7acffd8814ad4307bf63a67 and code revision fa9a2a7070b1789912a49ae24603bbfb1a78b001.",
    "Evidence: [machine-readable comparison](evidence/latest-comparison-report.json), [experiment log](EXPERIMENT_LOG.md), [original full-data report](evidence/full-training-report.json), [v1 report](evidence/practical-v1-report.json), [v2 report](evidence/practical-v2-report.json), [early experiments](../../experiments/lumi/README.md)."]
    (DOC/'COMPARISON.md').write_text('\n\n'.join(out)+'\n')
    print(DOC/'COMPARISON.md')


if __name__ == '__main__': main()
