"""Render the archived v3 regression audit without mixing comparison supports."""
import argparse
import json
from pathlib import Path


def main(report_path, output):
    r = json.loads(report_path.read_text())
    assert r['status'] == 'complete'
    v2, v3, export = 'v2_74k_plus_256', 'v3_adapter_512', 'v3_merged_export'
    lines = ['# V3 regression audit', '',
        'Selected model: v2 +512 updates, fixed before this audit. Both the adapter and the merged FP32 export were scored with BF16 autocast on the original frozen bilingual panels. No training or checkpoint reselection occurred.', '',
        'V3 improves the older practical panel overall, driven by routing, but regresses on refunds and Italian urgency. External benchmark changes are mixed; Italian CLINC improves while English HellaSwag falls. The merged export shows the same tradeoff. This supports retaining v3 as a routing-focused candidate, not claiming a universal improvement over v2. Before a general-purpose release, address retention with task-level development guards and balanced replay; do not select checkpoints on these reused tests.', '',
        '## Changes from v2 on the full panels', '',
        'Accuracy percentages; unsupported requests count as incorrect. Every comparison below uses the same examples for v2 and v3. EN and IT are reported separately. Changes are percentage points, not relative percentages.', '',
        '| Panel/task | Language | N | V2 | V3 adapter | Change | V3 export |',
        '|---|---|---:|---:|---:|---:|---:|']
    for panel, p in r['panels'].items():
        for cell, metric in p['full'][v2]['cells'].items():
            task, lang = cell.rsplit('/', 1)
            old = metric['accuracy']*100
            new = p['full'][v3]['cells'][cell]['accuracy']*100
            merged = p['full'][export]['cells'][cell]['accuracy']*100
            lines.append(f'| {panel}: {task} | {lang.upper()} | {metric["n"]} | {old:.2f}% | {new:.2f}% | {new-old:+.2f} | {merged:.2f}% |')
    lines += ['', '## Laya comparison on identical bilingual support', '',
        'A paired English/Italian example is retained only if both versions fit every listed historical control and both v3 artifacts. These denominators can be smaller than the full-panel table, especially for HellaSwag and When2Call. Do not compare percentages across the two tables as though they used the same examples.', '',
        '| Panel/task | Language | N | V2 | V3 adapter | V3 export | Laya |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for panel, p in r['panels'].items():
        c = p['common_bilingual']
        for cell, metric in c[v2]['cells'].items():
            task, lang = cell.rsplit('/', 1)
            vals = [f'{c[m]["cells"][cell]["accuracy"]*100:.2f}%' for m in (v2,v3,export,'laya')]
            lines.append(f'| {panel}: {task} | {lang.upper()} | {metric["n"]} | ' + ' | '.join(vals) + ' |')
    lines += ['', '## Overall panel accuracy', '',
        'These are per-panel micro averages. No overall score combines the three different datasets.', '',
        '| Panel | Support | N/language | V2 EN / IT | V3 EN / IT | Export EN / IT | Laya EN / IT |',
        '|---|---|---:|---:|---:|---:|---:|']
    for panel,p in r['panels'].items():
        for support in ('full','common_bilingual'):
            c=p[support]
            n='/'.join(str(c[v2]['by_language'][l]['n']) for l in ('en','it'))
            vals=[' / '.join(f'{c[m]["by_language"][l]["accuracy"]*100:.2f}%' for l in ('en','it')) for m in (v2,v3,export,'laya')]
            lines.append(f'| {panel} | {support} | {n} | '+' | '.join(vals)+' |')
    lines += ['', '## Correctness transitions after merging', '',
        'Counts below compare exported versus adapter correctness, not all argmax changes: a changed answer can be wrong in both artifacts.', '',
        '| Panel | N | Newly correct | Newly wrong | Accuracy change (points) |',
        '|---|---:|---:|---:|---:|']
    for panel,cells in r['export_vs_adapter_full'].items():
        d=cells['all']
        lines.append(f'| {panel} | {d["n"]} | {d["gained"]} | {d["lost"]} | {d["delta_percentage_points"]:+.3f} |')
    lines += ['', '## Reproducibility and limits', '',
        '- LUMI job **22714887** completed successfully in **8m34s**, one MI250X GPU device. All remote files are under the authorized project scratch directory. The local archive contains 70 individually verified evidence files; SHA-256 `343ff137a7bb7d6b714c68377d8427cd0accd35b7352bbf6b5984b7da36fed4b`.',
        '- Run: `runs/bilingual-all-v1/focused-v3-regression-v1`. Inputs, frozen runtime, selected adapter and export weights were SHA-256 checked. All historical baseline metrics reproduced (floating summation tolerance 1e-12 across Python versions).',
        '- Each v3 artifact was scored on 1,256 Okapi, 902 Decision Index, and 2,048 practical-v2 requests. Half are English, half Italian. Practical native choice/boolean/ordinal tasks use packed logits; external choice tasks retain the previous rows renderer, T=1.',
        '- These are previously inspected diagnostic subsets, not official full-suite leaderboard scores or new independent selection tests. Italian text is synthetic and partially reviewed; pretraining contamination is unknown.',
        '- No confidence guarantee follows from accuracy, and the v3 confidence policy still has no qualifying threshold. No public upload occurred.',
        '- [Machine-readable report](evidence/focused-v3-regression-report.json), [manifest](evidence/focused-v3-regression-manifest.json), and [complete evidence archive](evidence/focused-v3-regression-completed.tar.gz). The report retains all historical controls, support counts and paired correctness gains/losses.', '']
    output.write_text('\n'.join(lines))


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('report',type=Path)
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    main(a.report,a.output)
