"""Try one request with the resident two-model prototype and mock read-only tools."""
import argparse
import json
from agent import ARMS, GENERATORS, POLICIES, HybridAgent
from readable import render

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--policy',choices=POLICIES+['workflow'],default='baseline',help='single_read: caller guarantees exactly one supported read request; final prose is formatted by code')
p.add_argument('--generator',choices=GENERATORS,default='nesso3')
p.add_argument('--format',choices=['json','text'],default='json')
p.add_argument('--arm',choices=ARMS,required=True)
p.add_argument('--language',choices=['en','it'],default='it')
p.add_argument('--message',required=True)
p.add_argument('--schema-style',choices=['validated','compact'],default='compact')
a=p.parse_args()
if a.policy=='workflow':
    from workflow import compile_plan, run_workflow, render_workflow
    if a.arm!='nev_ranked':p.error('workflow requires --arm nev_ranked')
    plan=compile_plan(a.message,a.language)
    agent=HybridAgent(schema_style=a.schema_style,generator=a.generator) if plan['route'] in ('single','multi') else None
    result=run_workflow(agent,a.message,a.language)
    renderer=render_workflow
else:
    agent=HybridAgent(schema_style=a.schema_style,generator=a.generator)
    result=agent.run(a.message,a.language,a.arm,policy=a.policy)
    renderer=render
repo,revision=GENERATORS[a.generator]
record={'simulation':True,'generator':{'repository':repo,'revision':revision},
        'message':a.message,'language':a.language,**result}
print(renderer(record) if a.format=='text' else json.dumps(record,ensure_ascii=False,indent=2))
