"""Frozen workflow/controller comparison; old single-read results are a regression reference."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
from agent import HybridAgent, GENERATORS, NEV_REPO, NEV_REVISION
from workflow import run_workflow


def score(case,result,variant):
    actual=[e['call'] for e in result['executed_calls']]
    exact=actual==case['expected_calls']
    text=result['final'].casefold()
    anchors=all(any(a.casefold() in text for a in group) for group in case['answer_anchor_groups'])
    # Payment queries ask for the list too. Avoid the earlier total-only false positives.
    if any(c['name']=='list_transactions' for c in case['expected_calls']):
        anchors=anchors and any(v in text for v in ['24.5','24,5']) and any(v in text for v in ['39.25','39,25']) and 'eur' in text
    supported=case['expected_route'] in ('single','multi')
    return {'executed_calls_exact':exact,'no_execution':not actual,
        'supported_completion_proxy':bool(exact and anchors and text and (variant=='baseline' or result['status']=='complete')) if supported else None,
        'gate_route_exact':result['route']==case['expected_route'] if variant=='workflow' else None,
        'gate_pass':result['route']==case['expected_route'] and not actual and bool(text) if variant=='workflow' and not supported else None}


def summarize(rows):
    report={}
    for group in sorted({r['group'] for r in rows}):
        report[group]={}
        for variant in ['baseline','workflow']:
            report[group][variant]={}
            for lang in ['en','it']:
                selected=[r for r in rows if r['group']==group and r['variant']==variant and r['language']==lang]
                if not selected:continue
                report[group][variant][lang]={'n':len(selected),**{key:sum(bool(r['score'][key]) for r in selected)
                    for key in ['executed_calls_exact','no_execution','supported_completion_proxy','gate_pass']},
                    'median_ms':statistics.median(r['total_ms'] for r in selected)}
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh path')
    source=Path(__file__).parent;data=json.loads((source/'workflow_cases.json').read_text())
    report={'status':'incomplete','scope':data['scope'],'generator':dict(zip(['repository','revision'],GENERATORS['nesso3'])),
        'nev':{'repository':NEV_REPO,'revision':NEV_REVISION,'variant':'v3'},
        'source_sha256':{f:hashlib.sha256((source/f).read_bytes()).hexdigest() for f in ['workflow.py','agent.py','single_read.py','run_workflow_eval.py','workflow_cases.json']},
        'settings':{'comparison':'Original Nev-ranked free loop on 36 new requests; unified workflow on all 60. Alternating run order.',
            'scope_gate':'Full-match bilingual application grammar; unsupported stems checked before all clauses; not general language understanding.',
            'multi_step':'Up to four fully specified sequential read operations; no output-dependent or conditional planning.',
            'timing':'Shared A100, warm resident models. Workflow includes parsing and all model preflights, validation and sequential mock execution. Deferred grammar requests skip models.'},'rows':[]}
    report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.free,utilization.gpu','--format=csv'],text=True)
    agent=HybridAgent(generator='nesso3')
    import torch,transformers
    report.update(torch=torch.__version__,transformers=transformers.__version__,cuda=torch.version.cuda)
    agent.run('Get the invoice for order ORD-5000 and tell me the filename.','en','nev_ranked',policy='single_read')
    start=time.perf_counter();a.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        for index,case in enumerate(data['cases']):
            variants=['baseline','workflow'] if case['compare_baseline'] else ['workflow']
            if index%2:variants.reverse()
            for variant in variants:
                result=(run_workflow(agent,case['message'],case['language']) if variant=='workflow' else
                        agent.run(case['message'],case['language'],'nev_ranked',policy='baseline'))
                row={k:case[k] for k in ['id','group','language','message']}
                row.update(result);row['variant']=variant;row['score']=score(case,result,variant)
                report['rows'].append(row);report['summary']=summarize(report['rows'])
                a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(f"{len(report['rows'])}/96 {case['id']} {variant} {row['score']}",flush=True)
        report['status']='complete'
    finally:
        report['elapsed_seconds']=time.perf_counter()-start
        report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/1024**2
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
