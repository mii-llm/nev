"""Counterbalanced A100 comparison; every output and failure is retained."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time

from agent import ARMS, GENERATOR_REPO, GENERATOR_REVISION, NEV_REPO, NEV_REVISION, HybridAgent, schemas


def score(case, result):
    exact = result['emitted_calls'] == case['expected_calls'] and not any(t['parse_error'] for t in result['trace'])
    sequential = (case['category'] != 'two_step' or
        len(result['executed_calls'])==2 and result['executed_calls'][0]['turn'] < result['executed_calls'][1]['turn'])
    text=result['final'].casefold()
    anchors=all(any(a.casefold() in text for a in group) for group in case['answer_anchor_groups'])
    behavior=True
    if case['category']=='missing':
        behavior='?' in text and any(k.casefold() in text for k in case['behavior_keywords'])
    elif case['category']=='unavailable':
        behavior=any(k.casefold() in text for k in case['behavior_keywords'])
    expected_names={c['name'] for c in case['expected_calls']}
    return {'calls_exact':exact,'sequential':sequential,'answer_anchors_pass':anchors,
            'behavior_heuristic_pass':behavior,
            'strict_mechanical_pass':exact and sequential and anchors and behavior and bool(text) and not result['errors'] and not result['truncated'],
            'required_tools_available':expected_names.issubset(result['available_tools']) if expected_names else None}


def summarize(rows):
    summary={}
    for arm in ARMS:
        subset=[r for r in rows if r['arm']==arm]
        if not subset:continue
        cells={}
        for lang in ['en','it']:
            selected=[r for r in subset if r['language']==lang]
            if not selected:continue
            cells[lang]={'n':len(selected),'calls_exact':sum(r['score']['calls_exact'] for r in selected),
                'strict_mechanical_pass':sum(r['score']['strict_mechanical_pass'] for r in selected),
                'median_ms':statistics.median(r['total_ms'] for r in selected),
                'mean_ms':statistics.mean(r['total_ms'] for r in selected),
                'mean_generated_tokens':statistics.mean(r['generated_tokens'] for r in selected),
                'by_category':{cat:{'n':sum(r['category']==cat for r in selected),
                    'calls_exact':sum(r['score']['calls_exact'] for r in selected if r['category']==cat),
                    'strict_mechanical_pass':sum(r['score']['strict_mechanical_pass'] for r in selected if r['category']==cat)}
                    for cat in sorted({r['category'] for r in selected})}}
        summary[arm]=cells
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=Path,default=Path(__file__).with_name('cases.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a new output file')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(a.cases.read_text()); cases=data['cases']
    if a.limit:cases=cases[:a.limit]
    source=Path(__file__).parent
    report={'status':'incomplete','scope':data['scope'],'scoring':data['scoring'],
        'generator':{'repository':GENERATOR_REPO,'revision':GENERATOR_REVISION,'precision':'bf16'},
        'nev':{'repository':NEV_REPO,'revision':NEV_REVISION,'variant':'v3','precision':'fp32'},
        'cases_sha256':hashlib.sha256(a.cases.read_bytes()).hexdigest(),
        'source_sha256':{f:hashlib.sha256((source/f).read_bytes()).hexdigest() for f in ['agent.py','run_pilot.py']},
        'tool_schemas':{lang:schemas(lang) for lang in ['en','it']},'python':platform.python_version(),
        'settings':{'max_new_tokens_per_turn':192,'max_tool_rounds':3,'greedy':True,'memory_cap_gib':8,
                    'arm_order_seed':20261012,'shortlist_size':2,'timing':'Resident models, shared GPU, synchronized wall clock; mock tool overhead only. Nev rank is computed once per case and its measured cost attributed to each hybrid arm.'},
        'gpu_samples':[],'rows':[]}
    def sample_gpu():
        try:return subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=5).strip()
        except Exception:return 'unavailable'
    report['gpu_samples'].append(sample_gpu())
    agent=HybridAgent()
    import torch, transformers
    report.update(torch=torch.__version__,transformers=transformers.__version__,cuda=torch.version.cuda)
    # Separate engineering warmup; outputs are not scored.
    warmup='Please retrieve the invoice for ORD-5000 and give me its filename.'
    agent.rank(warmup,'en');agent.run(warmup,'en','nesso_only')
    started=time.perf_counter()
    try:
        rng=random.Random(20261012)
        base_order=ARMS.copy();rng.shuffle(base_order)
        for i,case in enumerate(cases):
            ranking=agent.rank(case['message'],case['language'])
            order=base_order[i%3:]+base_order[:i%3]
            for arm in order:
                result=agent.run(case['message'],case['language'],arm,ranking)
                row={k:case[k] for k in ['id','pair','category','language']}
                row.update(result);row['score']=score(case,result)
                report['rows'].append(row)
                report['summary']=summarize(report['rows'])
                report['elapsed_seconds']=time.perf_counter()-started
                a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(f"{len(report['rows'])}/{len(cases)*3} {case['id']} {arm} exact={row['score']['calls_exact']} pass={row['score']['strict_mechanical_pass']} ms={row['total_ms']:.0f}",flush=True)
            if i%10==0:report['gpu_samples'].append(sample_gpu())
        report['status']='complete'
    finally:
        report['elapsed_seconds']=time.perf_counter()-started
        report['peak_allocated_mib']=torch.cuda.max_memory_allocated()/1024**2
        report['peak_reserved_mib']=torch.cuda.max_memory_reserved()/1024**2
        report['gpu_samples'].append(sample_gpu())
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('SUMMARY',json.dumps(report['summary']),flush=True)

if __name__=='__main__':main()
