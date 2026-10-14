"""Small paired end-to-end CPU comparison, including known model failure cases."""
import argparse
import json
import os
from pathlib import Path
import statistics
import threading
import time
p=argparse.ArgumentParser();p.add_argument('--engine',choices=['gguf','torch'],default='gguf');p.add_argument('--precision',choices=['f16','q8'],default='q8');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if args.output.exists():p.error('Choose a fresh output path')
if args.engine=='gguf':os.environ['USE_TORCH']='0'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import psutil
from cpu_backend import Backend,ROOT
from abstract_agent.runtime import GenericAgent,render
from abstract_agent.fixtures import FixtureExecutor
cases=json.loads((ROOT/'abstract_agent/cases.json').read_text())['cases'];kits=json.loads((ROOT/'abstract_agent/toolsets.json').read_text())
selected=[c for c in cases if not c['renamed'] and (c['kind']=='single' or (c['toolset']=='sensors' and c['kind'] in ['selection','dependent','unsupported']))]
report={'status':'incomplete','engine':args.engine,'precision':args.precision if args.engine=='gguf' else 'fp32','cpu_only':True,'threads':4,'scope':'12 paired authored requests; 10 supported and two unavailable actions; original request text and mock outputs. Shared Mac, warm timings, four CPU threads. No accuracy claim beyond this sample.','rows':[]}
peak=[0];stop=threading.Event()
def sample():
 while not stop.is_set():
  try:
   me=psutil.Process();rss=me.memory_info().rss+sum(c.memory_info().rss for c in me.children(recursive=True) if c.is_running());peak[0]=max(peak[0],rss)
  except (psutil.Error,ProcessLookupError):pass
  stop.wait(.05)
monitor=threading.Thread(target=sample,daemon=True);monitor.start()
start=time.perf_counter();backend=Backend(args.precision,4,args.engine);report['load_seconds']=time.perf_counter()-start
try:
 backend.generate([{'role':'system','content':'Reply briefly.'},{'role':'user','content':'Hello.'}])
 kit=kits['notes'];backend.rank('Read note N-8R6.','en',kit['schemas']['en'],[],[],False)
 backend.generation_metrics.clear()
 for c in selected:
  kit=kits[c['toolset']];row=GenericAgent(backend).run(c['request'],c['language'],kit['schemas'][c['language']],FixtureExecutor(kit['responses']),'nev_ranked',7100)
  row.update({k:c[k] for k in ['id','language','kind','request']})
  actual=[e['call'] for e in row['executed_calls']];exact=actual==c['expected_calls']
  if c['kind']=='dependent':exact=exact and len(actual)==2 and row['executed_calls'][0]['turn']<row['executed_calls'][1]['turn']
  anchors=bool(row['final']) and all(any(a.casefold() in row['final'].casefold() for a in g) for g in c['answer_anchor_groups'])
  row['score']={'exact_plan':exact,'answer_anchor_proxy':exact and anchors and row['status']=='answered' if c['expected_calls'] else None}
  report['rows'].append(row);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(c['id'],row['status'],round(row['total_ms']),repr(row['final']),flush=True)
 report['generation_metrics']=backend.generation_metrics;report['status']='complete'
finally:
 backend.close();stop.set();monitor.join()
 report['peak_summed_rss_mib']=peak[0]/1024**2
 report['memory_note']='50 ms samples of Python plus child-worker RSS; includes shared/mapped pages and can double count them. Not physical footprint.'
 args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 args.output.with_suffix('.txt').write_text('\n\n'.join(render(r) for r in report['rows']))
