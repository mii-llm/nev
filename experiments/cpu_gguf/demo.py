import argparse
import json
import os
from pathlib import Path
import time
p=argparse.ArgumentParser(description='Nesso3 + Nev on this Mac CPU; simulated read-only tools.')
p.add_argument('--language',choices=['en','it','both'],default='both');p.add_argument('--message');p.add_argument('--toolset',default='sensors')
p.add_argument('--engine',choices=['gguf','torch'],default='gguf');p.add_argument('--precision',choices=['f16','q8'],default='f16')
p.add_argument('--threads',type=int,default=4);p.add_argument('--arm',choices=['nesso_only','shuffled','nev_ranked','nev_gated'],default='nev_ranked')
p.add_argument('--output',type=Path);args=p.parse_args()
if args.output and args.output.exists():p.error('Choose a new output path')
if args.engine=='gguf':os.environ['USE_TORCH']='0'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from cpu_backend import Backend,ROOT
from abstract_agent.runtime import GenericAgent,render
from abstract_agent.fixtures import FixtureExecutor
kits=json.loads((ROOT/'abstract_agent/toolsets.json').read_text());kit=kits[args.toolset]
start=time.perf_counter();backend=Backend(args.precision,args.threads,args.engine);load_seconds=time.perf_counter()-start;rows=[]
try:
 for lang in (['en','it'] if args.language=='both' else [args.language]):
  message=args.message or ('Read temperature sensor S-6K3.' if lang=='en' else 'Leggi la temperatura del sensore S-6K3.')
  row=GenericAgent(backend).run(message,lang,kit['schemas'][lang],FixtureExecutor(kit['responses']),args.arm,7100)
  row.update(language=lang,request=message);rows.append(row);print(render(row),flush=True)
finally:backend.close()
report={'engine':args.engine,'precision':args.precision if args.engine=='gguf' else 'fp32','cpu_only':True,'threads':args.threads,'load_seconds':load_seconds,'rows':rows,'generation_metrics':backend.generation_metrics}
if args.output:
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
