"""Qwen-only baseline reusing the frozen requests, controller and scoring."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import sys
import time

ROOT=Path(__file__).resolve().parent
STRESS=ROOT.parent
REPO=STRESS.parents[1]
sys.path.insert(0,str(STRESS))
from run_eval import digest, run_one, ordered_schemas, summarize
from abstract_agent.runtime import render
sys.path.insert(0,str(ROOT))
from backend import Backend,MODEL
from report import write_report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',type=Path,default=STRESS/'suite.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--orders',type=int,nargs='+',default=[0,1,2])
    p.add_argument('--baseline',type=Path,default=STRESS/'evidence/a100/rows.jsonl')
    p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    for freeze in [STRESS/'FREEZE.json',ROOT/'FREEZE.json']:
        for rel,sha in json.loads(freeze.read_text())['sha256'].items():
            if digest(REPO/rel)!=sha:raise RuntimeError('Frozen source changed: '+rel)
    qfreeze=json.loads((ROOT/'FREEZE.json').read_text())
    if digest(a.baseline)!=qfreeze['nesso_rows_sha256']:raise RuntimeError('Nesso baseline does not match frozen comparison')
    if a.suite.resolve() not in [(STRESS/'suite.json').resolve(),(STRESS/'pilot.json').resolve()]:p.error('Use frozen stress suite or separate pilot')
    if not a.orders or len(set(a.orders))!=len(a.orders) or any(o not in [0,1,2] for o in a.orders):p.error('Orders must be unique from 0, 1, 2')
    if a.output.exists() and not a.resume:p.error('Output exists; choose new path or --resume')
    if a.resume and not (a.output/'metadata.json').exists():p.error('Nothing to resume')
    os.environ.update(HF_HUB_OFFLINE='1',USE_TORCH='1',TOKENIZERS_PARALLELISM='false')
    data=json.loads(a.suite.read_text());cases=data['cases']
    metadata={'status':'running','model':MODEL,'engine':'cuda','precision':'qwen_bf16','thinking':False,
        'decoding':'greedy','max_new_tokens':192,'native_tools_template':True,'orders':a.orders,
        'suite_sha256':digest(a.suite),'freeze_sha256':digest(ROOT/'FREEZE.json'),
        'original_freeze_sha256':digest(STRESS/'FREEZE.json'),'nesso_rows_sha256':digest(a.baseline),
        'expected_trials':len(cases)*len(a.orders),'python':platform.python_version(),
        'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'comparison':'Qwen alone. Same frozen inputs, controller, order seeds, scoring and generation cap. Native Qwen tools template; thinking off. Greedy matches Nesso setting, differs from Qwen recommended sampling. Only Qwen resident; shared GPU timings not a controlled speed comparison.'}
    rows=[]
    if a.resume:
        old=json.loads((a.output/'metadata.json').read_text())
        for k in ['model','orders','suite_sha256','freeze_sha256','nesso_rows_sha256']:
            if json.dumps(old[k])!=json.dumps(metadata[k]):raise RuntimeError('Resume mismatch: '+k)
        metadata=old;metadata['status']='running'
        rows=[json.loads(s) for s in (a.output/'rows.jsonl').read_text().splitlines()]
    a.output.mkdir(parents=True,exist_ok=True)
    def save():
        for name,value in [('metadata.json',metadata),('summary.json',summarize(rows))]:
            tmp=a.output/(name+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(a.output/name)
    save();backend=None
    try:
        started=time.perf_counter();backend=Backend();metadata['load_seconds']=time.perf_counter()-started
        metadata.update(torch_version=backend.torch.__version__,chat_template_sha256=backend.template_sha256,
                        parameter_count=backend.parameter_count,model_allocated_mib=backend.model_allocated_mib)
        import subprocess
        metadata['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv'],text=True)
        backend.generate([{'role':'system','content':'Reply briefly.'},{'role':'user','content':'Hello.'}])
        # Verify native tools input actually renders before any scored request.
        from backend import native_messages
        sample=cases[0];system='Use tools when needed.\n<tools>\n'+json.dumps(sample['schemas'])+'\n</tools>'
        converted,tools=native_messages([{'role':'system','content':system},{'role':'user','content':sample['request']}])
        prompt=backend.tokenizer.apply_chat_template(converted,tools=tools,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        assert '<tools>' in prompt and '<tool_call>' in prompt and '<think>\n\n</think>' in prompt
        metadata['native_template_smoke_verified']=True
        done={(r['id'],r['order']) for r in rows}
        pairs=sorted({c['pair_id'] for c in cases});random.Random(20261019).shuffle(pairs)
        cases=sorted(cases,key=lambda c:(pairs.index(c['pair_id']),c['language']))
        for order in a.orders:
            for case in cases:
                if (case['id'],order) in done:continue
                start=len(backend.generation_metrics)
                try:
                    row=run_one(backend,case,ordered_schemas(case,order),data['fixtures'],'nesso_only',order)
                except Exception as exc:
                    (a.output/'failure.json').write_text(json.dumps({'id':case['id'],'order':order,'error':repr(exc)},indent=2)+'\n')
                    raise
                row['arm']='qwen_only';row['generator']='Qwen3-0.6B'
                row['generation_metrics']=backend.generation_metrics[start:]
                with (a.output/'rows.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
                with (a.output/'traces.txt').open('a') as f:
                    text=(render(row).replace('Nesso3:','Qwen3:') if row['trace'] else 'User: '+case['request']+'\nQwen3: '+row.get('raw_completion',''))
                    f.write('\n'+'='*70+'\n'+f"{case['id']} | qwen_only | order {order}\n"+text+'\nScore: '+json.dumps(row['score'])+'\n')
                rows.append(row);save()
                print(f"{len(rows)}/{metadata['expected_trials']} {case['id']} order={order} {row['score']} {row['total_ms']/1000:.2f}s",flush=True)
        metadata['status']='complete'
    except BaseException:
        metadata['status']='failed';raise
    finally:
        if backend is not None:
            metadata['peak_allocated_mib']=backend.torch.cuda.max_memory_allocated()/1024**2
            metadata['peak_reserved_mib']=backend.torch.cuda.max_memory_reserved()/1024**2
            backend.close()
        metadata['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    write_report(a.output,rows,a.baseline,metadata)
    print('COMPLETE '+str(a.output),flush=True)

if __name__=='__main__':main()
