"""Try one request with the resident two-model prototype and mock read-only tools."""
import argparse
import json
from agent import ARMS, GENERATORS, HybridAgent
from readable import render

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--generator',choices=GENERATORS,default='nesso3')
p.add_argument('--format',choices=['json','text'],default='json')
p.add_argument('--arm',choices=ARMS,required=True)
p.add_argument('--language',choices=['en','it'],default='it')
p.add_argument('--message',required=True)
p.add_argument('--schema-style',choices=['validated','compact'],default='compact')
a=p.parse_args()
agent=HybridAgent(schema_style=a.schema_style,generator=a.generator)
result=agent.run(a.message,a.language,a.arm)
record={'simulation':True,'generator':{'repository':agent.generator_repo,'revision':agent.generator_revision},
        'message':a.message,'language':a.language,**result}
print(render(record) if a.format=='text' else json.dumps(record,ensure_ascii=False,indent=2))
