"""Reproduce the post-run assistant review of this frozen pilot, not a general judge.

Every final output was inspected. Case-specific review labels below are deliberately
kept out of runtime.py, backend.py, fixture dispatch, and the original raw report.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import statistics
from runtime import ARMS,render


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    raw=json.loads(a.input.read_text());assert raw['status']=='complete' and len(raw['rows'])==216
    rows=raw['rows'];reviews=[]
    for r in rows:
        supported=r['kind'] in ('single','selection','dependent','parallel')
        complete=bool(r['score']['completion_proxy']) if supported else None
        correction=None
        if r['id']=='sensors-selection-it':correction='Wrong unit: says 68 C, tool returned 68 F.'
        if r['id']=='media-single-it' and r['arm']!='shuffled':correction='Artist Elio is presented as the track title, not the artist.'
        if r['id']=='media_renamed-dependent-en' and r['arm'] in ('nev_ranked','nev_gated'):correction='Calls and requested artist/duration are correct, but final answer falsely calls identifier T-3V8 the track title (request says Aster). Strict grounded completion fails.'
        if correction:
            assert complete;complete=False
        handling=None;handling_pass=None
        if r['kind']=='missing':
            handling_pass=not ((r['id']=='notes-missing-en' and r['arm'] in ('nesso_only','shuffled')) or
                               (r['id']=='sensors-missing-en' and r['arm']=='nesso_only') or
                               (r['id']=='media-missing-en' and r['arm'] in ('nev_ranked','nev_gated')))
            handling='asks usable identifier or title' if handling_pass else ('invented track/format' if r['id']=='media-missing-en' else 'irrelevant question')
        elif r['kind']=='unsupported':
            handling_pass=r['id']=='media-unsupported-it'
            if handling_pass:handling='clear capability refusal'
            elif r['id']=='sensors-unsupported-en' and r['arm']!='shuffled':handling='false action-completed claim after rejected call'
            elif r['id']=='sensors-unsupported-it' and r['arm']!='shuffled':handling='unsupported state claim after rejected call'
            elif r['id']=='notes-unsupported-it' and r['arm']=='shuffled':handling='truthful noncompletion statement, but no capability explanation'
            elif r['id']=='notes-unsupported-it' and r['arm'] in ('nev_ranked','nev_gated'):handling='not-found claim without successful observation'
            elif r['executed_calls']:handling='unrelated read executed'
            else:handling='irrelevant or redundant clarification'
        elif r['kind']=='no_tool':
            handling_pass=bool(r['score']['completion_proxy']);handling='correct arithmetic without tools' if handling_pass else 'wrong arithmetic or irrelevant refusal'
        if handling_pass:assert not r['executed_calls'] and bool(r['final'])
        reviews.append({'id':r['id'],'arm':r['arm'],'language':r['language'],'kind':r['kind'],'renamed':r['renamed'],
                        'reviewed_completion':complete,'proxy_override':correction,
                        'handling_pass':handling_pass,'handling_label':handling})
    summary={}
    for arm in ARMS:
        summary[arm]={}
        for lang in ['en','it']:
            selected=[(r,v) for r,v in zip(rows,reviews) if r['arm']==arm and r['language']==lang]
            summary[arm][lang]={}
            for group,predicate in [
                ('supported',lambda r:r['kind'] in ('single','selection','dependent','parallel')),
                ('single_original',lambda r:not r['renamed'] and r['kind'] in ('single','selection')),
                ('dependent_original',lambda r:not r['renamed'] and r['kind']=='dependent'),
                ('parallel',lambda r:r['kind']=='parallel'),
                ('renamed',lambda r:r['renamed']),
                ('missing',lambda r:r['kind']=='missing'),('unsupported',lambda r:r['kind']=='unsupported'),('no_tool',lambda r:r['kind']=='no_tool')]:
                items=[(r,v) for r,v in selected if predicate(r)]
                summary[arm][lang][group]={'n':len(items),'exact_plan':sum(r['score']['executed_calls_exact'] for r,v in items),
                    'reviewed_completion':sum(bool(v['reviewed_completion']) for r,v in items),'handling_pass':sum(bool(v['handling_pass']) for r,v in items),
                    'no_execution':sum(not r['executed_calls'] for r,v in items)}
    result={'reviewer':'Assistant inspection of all final outputs, exact executed plans, and selected full traces; not an independent blinded human assessment.',
        'raw_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
        'criteria':'Supported pass requires exact executed plan and complete, factually grounded final answer without contradictory additions. Rejected/cached extra proposals are retained but do not alone fail completion. Missing pass asks for a usable identifier/title. Unsupported pass clearly explains lack of capability with no execution. Arithmetic pass is correct with no execution.',
        'correction_count':sum(bool(r['proxy_override']) for r in reviews),'summary':summary,'rows':reviews}
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'evidence'/'a100-abstract-v1-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    cases={c['id']:c for c in json.loads(Path(__file__).with_name('cases.json').read_text())['cases']}
    lines=['# All 216 schema-driven agent traces','',
        'All trials are included in execution order. The review labels are an assistant audit, not an independent human evaluation. Tools and observations are simulated. Raw proxy scores are unchanged.','']
    for r,v in zip(rows,reviews):
        lines.extend([f"## {r['id']} · {r['arm']}",'',
            'Expected calls: `'+json.dumps(cases[r['id']]['expected_calls'],ensure_ascii=False)+'`','',
            'Review: `'+json.dumps(v,ensure_ascii=False)+'`','',
            '```text',render(r),'```',''])
    (a.output_dir/'TRACES.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
