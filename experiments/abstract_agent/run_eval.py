"""Run the frozen schema-driven pilot; gold labels are used only after each run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time
from backend import Backend,GENERATOR,NEV
from fixtures import FixtureExecutor
from runtime import ARMS,GenericAgent


def score(case,row):
    calls=[e['call'] for e in row['executed_calls']];expected=case['expected_calls']
    key=lambda c:json.dumps(c,sort_keys=True)
    exact=sorted(map(key,calls))==sorted(map(key,expected)) if case['kind']=='parallel' else calls==expected
    if case['kind']=='dependent':exact=exact and len(calls)==2 and row['executed_calls'][0]['turn']<row['executed_calls'][1]['turn']
    final=row['final'].casefold()
    anchors=bool(final) and all(any(a.casefold() in final for a in group) for group in case['answer_anchor_groups'])
    # Do not pretend keyword rules measure honest refusal or good clarification.
    completion=exact and anchors and row['status']=='answered' if expected or case['kind']=='no_tool' else None
    first=row['emitted_calls'][0] if row['emitted_calls'] else None
    return {'first_call_exact':first in expected if expected else first is None,
            'executed_calls_exact':exact,'completion_proxy':completion,'no_execution':not calls,
            'extra_executions':sum(c not in expected for c in calls),
            'has_validation_error':any(e in ('schema_violation','argument_not_grounded','unknown_tool') for e in row['errors'])}


def summarize(rows):
    result={}
    for arm in ARMS:
        result[arm]={}
        for lang in ['en','it']:
            selected=[r for r in rows if r['arm']==arm and r['language']==lang]
            if not selected:continue
            supported=[r for r in selected if r['kind'] not in ('missing','unsupported','no_tool')]
            times=sorted(r['total_ms'] for r in selected)
            result[arm][lang]={'n':len(selected),'supported_n':len(supported),
                'exact_plan':sum(r['score']['executed_calls_exact'] for r in supported),
                'completion_proxy':sum(bool(r['score']['completion_proxy']) for r in supported),
                'extra_execution_requests':sum(r['score']['extra_executions']>0 for r in selected),
                'validation_error_requests':sum(r['score']['has_validation_error'] for r in selected),
                'blocked_requests':sum(r['status']=='blocked_by_nev' for r in selected),
                'median_ms':statistics.median(times),'p95_ms':times[math.ceil(.95*len(times))-1]}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh output file')
    source=Path(__file__).parent;data=json.loads((source/'cases.json').read_text());kits=json.loads((source/'toolsets.json').read_text())
    report={'status':'incomplete','scope':data['scope'],'generator':GENERATOR,'nev':NEV,
            'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(source.iterdir()) if f.suffix in ('.py','.json')},
            'settings':{'max_turns':4,'max_new_tokens':192,'max_calls_per_batch':4,'max_executions':8,'seed':7100,
                'timing':'Shared A100; both models resident in every arm; synchronized whole request, including ranking, validation and mocks. Not device timings.',
                'arm_order':'Rotated by case index; shuffled arm uses deterministic per-case seed.',
                'scoring':'Exact executed plan plus answer anchors is a proxy. Missing/unsupported answers require separate manual audit. No hidden answer template.'},'rows':[]}
    report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.free,utilization.gpu','--format=csv'],text=True)
    backend=Backend();agent=GenericAgent(backend)
    import torch,transformers
    report.update(torch=torch.__version__,transformers=transformers.__version__,cuda=torch.version.cuda,model_memory_mib=backend.memory)
    # Warm inference once; not a scored case and no model/prompt tuning follows it.
    warm=kits['notes']['schemas']['en'];backend.generate([{'role':'system','content':'Reply briefly.'},{'role':'user','content':'Hello.'}])
    backend.rank('Hello.','en',warm,[],[],False)
    start=time.perf_counter();a.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        for i,case in enumerate(data['cases']):
            kit=kits[case['toolset']]
            for arm in ARMS[i%4:]+ARMS[:i%4]:
                row=agent.run(case['request'],case['language'],kit['schemas'][case['language']],FixtureExecutor(kit['responses']),arm,7100+i)
                row.update({k:case[k] for k in ['id','toolset','kind','language','request','renamed']});row['score']=score(case,row)
                report['rows'].append(row);report['summary']=summarize(report['rows'])
                a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(f"{len(report['rows'])}/{len(data['cases'])*4} {case['id']} {arm} {row['status']} {row['score']}",flush=True)
        report['status']='complete'
    finally:
        report['elapsed_seconds']=time.perf_counter()-start;report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/1024**2
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
