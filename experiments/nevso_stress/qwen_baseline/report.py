"""Report Qwen against all three frozen Nesso3 arms; keep metrics distinct."""
import json
from pathlib import Path


def write_report(output,rows,baseline,metadata):
    root=Path(__file__).resolve().parents[1]
    cases={c['id']:c for c in json.loads((root/'suite.json').read_text())['cases']}
    if not all(r['id'] in cases for r in rows):return  # The separate pilot has no stress score.
    original=[json.loads(s) for s in Path(baseline).read_text().splitlines()]
    arms=['nesso_only','nev_ranked','nev_selected','qwen_only']
    panels=[('Confusable: correct calls','confusable','call_correct'),('Confusable: answer proxy','confusable','completion_proxy'),
            ('BFCL-derived: correct calls','external_single','call_correct'),('Missing input: RAW clarification proxy','missing','completion_proxy'),
            ('Dependent: completion proxy','dependent','completion_proxy'),('Unsupported: behavior proxy','unsupported','completion_proxy'),
            ('Direct: exact answer, no calls','direct','completion_proxy'),('Tool error: completion proxy','tool_error','completion_proxy'),
            ('Date: exact requested format','date_format','strict_completion_proxy')]
    def group(r):
        c=cases[r['id']]
        if c['category']=='unsupported_or_direct':return c['expected_behavior']
        if c['category']=='error_or_format':return 'tool_error' if c['expected_behavior']=='tool_error' else 'date_format'
        return c['category']
    lines=['# Qwen3-0.6B comparison on the frozen Nevso stress test','',
        f"Qwen status: **{metadata['status']}**, {len(rows)}/{metadata['expected_trials']} trials. Non-thinking, native tools template, greedy BF16, 192-token output cap.",'',
        'These are runtime-budget-matched results, not an official BFCL score or a maximum-capability Qwen evaluation. No reasoning tokens or model-specific sampling search were used. Qwen documentation recommends sampling; this run uses greedy decoding to match the existing baseline.',
        '', '**Do not interpret the raw clarification proxy as successful clarification:** it is known to accept wrong questions and refusals. Nesso3 has separate reviewed labels; Qwen needs the same review before that category is compared substantively.',
        '', '| Metric | Language | Nesso3 | Nev-ranked + Nesso3 | Nev-selected + Nesso3 | Qwen3-0.6B alone |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    table=[]
    for title,category,metric in panels:
        for lang in ['en','it']:
            values=[];record={'metric':title,'language':lang,'scores':{}}
            for arm in arms:
                selected=[r for r in (rows if arm=='qwen_only' else original) if r['arm']==arm and r['language']==lang and group(r)==category]
                vals=[r['score'][metric] for r in selected if r['score'].get(metric) is not None]
                record['scores'][arm]={'correct':sum(vals),'n':len(vals)}
                values.append(f'{sum(vals)}/{len(vals)} ({100*sum(vals)/len(vals):.1f}%)' if vals else '—')
            lines.append('| '+title+' | '+lang.upper()+' | '+' | '.join(values)+' |');table.append(record)
    lines += ['', 'Each language has 100 requests, each repeated with three seeded tool-order draws. Trial counts are correlated. Both runs use the same controller, fixtures, scoring and output cap, but each generator uses its native chat/tool template. The selected Nesso3 arm has one tool; standalone Qwen sees the full catalog.',
        '', 'Correct calls and complete answers are different metrics. Answer assertions are proxies, not a factual audit. The initial single-tool strategy cannot perform a second distinct tool call. BFCL training overlap is unknown. No blanket model ranking or causal size claim follows from these small panels.']
    Path(output,'COMPARISON.md').write_text('\n'.join(lines)+'\n')
    Path(output,'comparison.json').write_text(json.dumps(table,indent=2)+'\n')
