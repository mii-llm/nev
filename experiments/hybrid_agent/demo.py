"""Try one request with the resident two-model prototype and mock read-only tools."""
import argparse
import json
from agent import ARMS, HybridAgent

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--arm',choices=ARMS,required=True)
p.add_argument('--language',choices=['en','it'],default='it')
p.add_argument('--message',required=True)
p.add_argument('--schema-style',choices=['validated','compact'],default='validated')
a=p.parse_args()
agent=HybridAgent(schema_style=a.schema_style)
result=agent.run(a.message,a.language,a.arm)
print(json.dumps({'simulation':True,'message':a.message,'language':a.language,**result},ensure_ascii=False,indent=2))
