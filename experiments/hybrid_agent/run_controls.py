"""Compare original loop, a short prompt, and an explicit single-read controller."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
from agent import HybridAgent, POLICIES, GENERATORS, NEV_REPO, NEV_REVISION
from run_pilot import score


def completion_score(case, result):
    original=score(case,result)
    # Keep raw generation scoring, including extra/rejected calls, unchanged.
    executed=[entry['call'] for entry in result['executed_calls']]
    completion=(executed==case['expected_calls'] and original['answer_anchors_pass']
                and bool(result['final']) and not result.get('blocked_reason') and not result['truncated'])
    return {**original,'application_completion_proxy':completion,
            'first_call_exact':bool(result['emitted_calls']) and result['emitted_calls'][0]==case['expected_calls'][0],
            'nev_top1_exact':result['ranking']['names'][0]==case['expected_calls'][0]['name']}


def summarize(rows):
    result={}
    for split in ['development','fresh']:
        result[split]={}
        for policy in POLICIES:
            result[split][policy]={}
            for lang in ['en','it']:
                group=[r for r in rows if r['split']==split and r['policy']==policy and r['language']==lang]
                if not group:continue
                result[split][policy][lang]={'n':len(group),**{metric:sum(r['score'][metric] for r in group)
                    for metric in ['strict_mechanical_pass','application_completion_proxy','first_call_exact','nev_top1_exact']},
                    'deferrals':sum(bool(r['blocked_reason']) for r in group),
                    'median_ms':statistics.median(r['total_ms'] for r in group)}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh output path')
    source=Path(__file__).parent
    cases_path=source/'control_cases.json'
    data=json.loads(cases_path.read_text())
    report={'status':'incomplete','scope':data['scope'],
        'generator':dict(zip(['repository','revision'],GENERATORS['nesso3'])),
        'nev':{'repository':NEV_REPO,'revision':NEV_REVISION,'variant':'v3'},
        'source_sha256':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in
                         ['agent.py','single_read.py','run_controls.py','run_pilot.py','control_cases.json']},
        'settings':{'all_tools_available':True,'arm':'nev_ranked','greedy':True,'max_new_tokens':192,
            'policy_order':'rotating per request','single_read_scope':'Established by application, not inferred by controller',
            'completion_proxy':'Exact executed call plus answer anchors, no truncation/deferral. Extra rejected generation is retained and still fails raw strict metric.',
            'timing':'Shared A100, warm resident models, includes Nev routing cost, excludes real API latency'},'rows':[]}
    report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.free,utilization.gpu','--format=csv'],text=True)
    agent=HybridAgent(generator='nesso3')
    import torch, transformers
    report.update(torch=torch.__version__,transformers=transformers.__version__,cuda=torch.version.cuda)
    warmup='Get the invoice for ORD-5000.'
    ranking=agent.rank(warmup,'en')
    agent.run(warmup,'en','nev_ranked',ranking)
    start=time.perf_counter()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        for index,case in enumerate(data['cases']):
            ranking=agent.rank(case['message'],case['language'])
            offset=index%len(POLICIES)
            for policy in POLICIES[offset:]+POLICIES[:offset]:
                result=agent.run(case['message'],case['language'],'nev_ranked',ranking,policy=policy)
                row={k:case[k] for k in ['id','pair','split','category','language','message']}
                row.update(result);row['score']=completion_score(case,result)
                report['rows'].append(row);report['summary']=summarize(report['rows'])
                report['elapsed_seconds']=time.perf_counter()-start
                a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(f"{len(report['rows'])}/72 {case['id']} {policy} strict={row['score']['strict_mechanical_pass']} completed={row['score']['application_completion_proxy']}",flush=True)
        report['status']='complete'
    finally:
        report['elapsed_seconds']=time.perf_counter()-start
        report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/1024**2
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
