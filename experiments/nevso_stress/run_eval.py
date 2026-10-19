"""Frozen bilingual evaluation: native CUDA or CPU GGUF, with resumable traces."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import sys
import time
from collections import defaultdict

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
CPU=REPO/'experiments/cpu_gguf'
sys.path.insert(0,str(CPU))
from abstract_agent.runtime import GenericAgent, parse_calls, render
from abstract_agent.fixtures import FixtureExecutor
from jsonschema import Draft202012Validator

ARMS=['nesso_only','nev_ranked','nev_selected']

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def schema_errors(calls,schemas):
    tools={s['function']['name']:s['function']['parameters'] for s in schemas}
    errors=[]
    for c in calls:
        if not isinstance(c['name'],str) or c['name'] not in tools:errors.append('unknown_tool');continue
        p=copy.deepcopy(tools[c['name']]);p.setdefault('additionalProperties',False)
        if list(Draft202012Validator(p).iter_errors(c['arguments'])):errors.append('schema_violation')
    return errors


def equivalent(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
    return a==b


def reference_match(calls,case):
    """Flat alternative-value comparison; deliberately not the official BFCL checker."""
    if len(calls)!=1:return False
    c=calls[0];name,reference=next(iter(case['reference'].items()))
    if c['name']!=name or not isinstance(c['arguments'],dict):return False
    schema=next(s['function']['parameters'] for s in case['schemas'] if s['function']['name']==name)
    args=c['arguments']
    for key,values in reference.items():
        if key not in args:
            if key in schema.get('required',[]):return False
            if '' in values:continue
            default=schema['properties'].get(key,{}).get('default',object())
            if any(equivalent(default,v) for v in values):continue
            return False
        if not any(equivalent(args[key],v) for v in values):return False
    for key,value in args.items():
        if key in reference:continue
        prop=schema['properties'].get(key,{})
        if 'default' not in prop or not equivalent(value,prop['default']):return False
    return True


def score(case,row):
    emitted=row.get('emitted_calls',[])
    if case['expected_behavior']=='call_only':
        expected_name=next(iter(case['reference']))
        ref=reference_match(emitted,case)
        return {'tool_name_correct':len(emitted)==1 and emitted[0]['name']==expected_name,
                'reference_arguments_match':ref,
                'call_correct':ref and not row['errors'] and row['status']=='call_generated',
                'completion_proxy':None,'no_call_behavior_proxy':None,
                'attempted_calls':len(emitted),'blocked_calls':0}
    expected=case['expected_calls'];actual=[e['call'] for e in row['executed_calls']]
    exact=actual==expected
    if case.get('dependent') and exact:
        exact=row['executed_calls'][1]['turn']>row['executed_calls'][0]['turn']
    text=row['final'].strip();lower=text.casefold();behavior=case['expected_behavior']
    answered=row['status']=='answered' and bool(text)
    anchors=answered and all(any(s.casefold() in lower for s in group) for group in case['answer_anchor_groups'])
    no_calls=not emitted and not actual
    clarify=bool(re.search(r'\?|\b(provide|specify|which|what|need|indica|specifica|quale|fornisci|serve|necessari)',lower))
    clarify=clarify and any(c in lower for c in case.get('clarification_concepts',[]))
    unsupported=bool(re.search(r"cannot|can't|unable|not (?:available|supported|possible)|no (?:tool|function)|do not (?:have|support)|don't (?:have|support)|non (?:posso|è possibile|dispon|support)|nessun[oa]? strument|non ho|solo (?:leggere|consultare)|only (?:read|retrieve)",lower))
    error_ack=bool(re.search(r'not.found|no (?:matching|record|data|information)|could not|couldn.t|unable|non (?:trov|ho trovato|risult|dispon)|nessun|inesistent|errore|error',lower))
    if behavior=='clarify':complete=answered and no_calls and clarify
    elif behavior=='unsupported':complete=answered and no_calls and unsupported
    elif behavior=='direct':complete=answered and no_calls and text==case['exact_answer']
    elif behavior=='tool_error':complete=answered and exact and error_ack
    else:complete=exact and anchors
    strict=complete and ('exact_answer' not in case or text==case['exact_answer'])
    return {'call_correct':exact if expected else None,
            'completion_proxy':bool(complete),'strict_completion_proxy':bool(strict),
            'no_call_behavior_proxy':bool(complete) if not expected else None,
            'attempted_calls':len(emitted),
            'blocked_calls':sum(v['error'] is not None for t in row['trace'] for v in t.get('validation',[])),
            'answer_assertions_pass':bool(anchors) if behavior=='answer' else None}


def ordered_schemas(case,order):
    schemas=copy.deepcopy(case['schemas'])
    seed=int(hashlib.sha256((case['pair_id']+':'+str(order)).encode()).hexdigest()[:12],16)
    random.Random(seed).shuffle(schemas)
    return schemas


def prepare(backend,case,schemas,arm):
    ranking=None
    if arm!='nesso_only':
        ranking=backend.rank(case['request'],case['language'],schemas,[],[],False)
        schemas=sorted(schemas,key=lambda s:-ranking['probabilities'][s['function']['name']])
        if arm=='nev_selected':schemas=schemas[:1]
    return schemas,ranking


def run_one(backend,case,schemas,fixtures,arm,order):
    start=time.perf_counter()
    visible,ranking=prepare(backend,case,schemas,arm)
    if case['expected_behavior']=='call_only':
        context='Sei un assistente operativo. Usa gli strumenti disponibili quando serve.' if case['language']=='it' else 'You are an operational assistant. Use the available tools when needed.'
        system=context+'\n<tools>\n'+json.dumps(visible,ensure_ascii=False,separators=(',',':'))+'\n</tools>'
        raw,tokens,truncated=backend.generate([{'role':'system','content':system},{'role':'user','content':case['request']}])
        calls,error=parse_calls(raw)
        errors=([error] if error else [])+(['truncated'] if truncated else [])+schema_errors(calls,visible)
        row={'status':'invalid_output' if errors else ('call_generated' if calls else 'answered'),
             'final':raw if not calls else '', 'raw_completion':raw,'emitted_calls':calls,'executed_calls':[],
             'errors':errors,'generated_tokens':tokens,'trace':[]}
    else:
        row=GenericAgent(backend).run(case['request'],case['language'],visible,FixtureExecutor(fixtures),'nesso_only',order)
    row.update(id=case['id'],pair_id=case['pair_id'],language=case['language'],category=case['category'],
               source=case['source'],domain=case['domain'],arm=arm,order=order,request=case['request'],
               quality_flag=case.get('quality_flag'),initial_tool_order=[s['function']['name'] for s in schemas],
               initial_ranking=ranking,total_ms=(time.perf_counter()-start)*1000)
    row['score']=score(case,row)
    return row


def summarize(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r['category'],r['language'],r['arm'])].append(r)
    result=[]
    for (category,lang,arm),rs in sorted(groups.items()):
        out={'category':category,'language':lang,'arm':arm,'trials':len(rs),'requests':len({r['id'] for r in rs}),
             'infrastructure_errors':sum(r['status']=='infrastructure_error' for r in rs),
             'median_ms':statistics.median(r['total_ms'] for r in rs),
             'p95_ms':sorted(r['total_ms'] for r in rs)[max(0,int(.95*len(rs))-1)]}
        for metric in ['tool_name_correct','call_correct','reference_arguments_match','completion_proxy','strict_completion_proxy','no_call_behavior_proxy']:
            vals=[r['score'][metric] for r in rs if r['score'].get(metric) is not None]
            if vals:out[metric]={'correct':sum(vals),'n':len(vals)}
        out['blocked_calls']=sum(r['score'].get('blocked_calls',0) for r in rs)
        result.append(out)
    return result


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine',choices=['cuda','gguf'],default='cuda')
    p.add_argument('--suite',type=Path,default=ROOT/'suite.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--orders',type=int,nargs='+',default=[0,1,2])
    p.add_argument('--resume',action='store_true')
    p.add_argument('--threads',type=int,default=4)
    a=p.parse_args()
    frozen=json.loads((ROOT/'FREEZE.json').read_text())
    for rel,sha in frozen['sha256'].items():
        if digest(REPO/rel)!=sha:raise RuntimeError('Frozen source changed: '+rel)
    data=json.loads(a.suite.read_text());cases=data['cases']
    if a.suite.resolve() not in [(ROOT/'suite.json').resolve(),(ROOT/'pilot.json').resolve()]:p.error('Use a frozen suite')
    if len(set(a.orders))!=len(a.orders) or any(o not in [0,1,2] for o in a.orders):p.error('Orders must be unique, from 0, 1, 2')
    if a.output.exists() and not a.resume:p.error('Output exists; use --resume or a new directory')
    if a.resume and not (a.output/'metadata.json').exists():p.error('No saved run to resume')
    a.output.mkdir(parents=True,exist_ok=True)
    os.environ.update(HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',USE_TORCH='1' if a.engine=='cuda' else '0')
    metadata={'status':'running','engine':a.engine,'precision':'nesso3_bf16_nev_fp32' if a.engine=='cuda' else 'q8',
              'freeze_sha256':digest(ROOT/'FREEZE.json'),'suite_sha256':digest(a.suite),'orders':a.orders,
              'expected_trials':len(cases)*3*len(a.orders),'python':platform.python_version(),
              'scoring':'Custom BFCL reference/schema comparison; workflow completion assertions are proxies pending trace review. No combined overall score.',
              'selected_boundary':'Single initial Nev selection is deliberately unchanged; dependent tasks expose its architectural restriction.',
              'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    rows=[]
    if a.resume:
        old=json.loads((a.output/'metadata.json').read_text())
        for k in ['engine','precision','freeze_sha256','suite_sha256','orders']:
            if old[k]!=metadata[k]:raise RuntimeError('Resume configuration mismatch: '+k)
        metadata=old;metadata['status']='running'
        rows=[json.loads(s) for s in (a.output/'rows.jsonl').read_text().splitlines()]
    def save():
        (a.output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
        (a.output/'summary.json').write_text(json.dumps(summarize(rows),indent=2)+'\n')
    save()
    module=load_module('native_backend',REPO/'experiments/abstract_agent/backend.py') if a.engine=='cuda' else load_module('gguf_backend',CPU/'cpu_backend.py')
    start=time.perf_counter();backend=module.Backend() if a.engine=='cuda' else module.Backend('q8',a.threads)
    metadata['load_seconds']=time.perf_counter()-start
    if a.engine=='cuda':
        import subprocess
        metadata['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv'],text=True)
        metadata['torch_version']=backend.torch.__version__
        metadata['model_revisions']={'nesso3':module.GENERATOR,'nev':module.NEV}
    else:metadata['release']=json.loads((CPU/'release.json').read_text())
    done={(r['id'],r['arm'],r['order']) for r in rows}
    pair_ids=sorted({c['pair_id'] for c in cases});random.Random(20261019).shuffle(pair_ids)
    cases=sorted(cases,key=lambda c:(pair_ids.index(c['pair_id']),c['language']))
    try:
        backend.generate([{'role':'system','content':'Reply briefly.'},{'role':'user','content':'Hello.'}])
        backend.rank('Hello.','en',cases[0]['schemas'],[],[],False)
        for order in a.orders:
            for i,case in enumerate(cases):
                schemas=ordered_schemas(case,order)
                offset=(i+order)%3
                for arm in ARMS[offset:]+ARMS[:offset]:
                    if (case['id'],arm,order) in done:continue
                    start=time.perf_counter()
                    try:row=run_one(backend,case,schemas,data['fixtures'],arm,order)
                    except Exception as exc:
                        # Preserve infrastructure failures without falsely counting them as completed model evaluations.
                        row={'id':case['id'],'pair_id':case['pair_id'],'language':case['language'],'category':case['category'],
                             'source':case['source'],'domain':case['domain'],'arm':arm,'order':order,'status':'infrastructure_error',
                             'error':repr(exc),'score':{},'total_ms':(time.perf_counter()-start)*1000}
                        metadata['status']='failed'
                        (a.output/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                        raise
                    with (a.output/'rows.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
                    rows.append(row);done.add((case['id'],arm,order))
                    with (a.output/'traces.txt').open('a') as f:
                        f.write('\n'+'='*70+'\n'+f"{case['id']} | {arm} | order {order}\n")
                        f.write((render(row) if row['trace'] else 'User: '+case['request']+'\nNesso3: '+row.get('raw_completion',''))+'\n')
                        f.write('Score: '+json.dumps(row['score'])+'\n')
                    save()
                    print(f"{len(rows)}/{metadata['expected_trials']} {case['id']} {arm} order={order} {row['score']} {row['total_ms']/1000:.2f}s",flush=True)
        metadata['status']='complete'
    except BaseException:
        metadata['status']='failed'
        raise
    finally:
        if a.engine=='cuda':
            metadata['peak_allocated_mib']=backend.torch.cuda.max_memory_allocated()/1024**2
            metadata['peak_reserved_mib']=backend.torch.cuda.max_memory_reserved()/1024**2
        backend.close();metadata['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    print('COMPLETE '+str(a.output),flush=True)

if __name__=='__main__':main()
