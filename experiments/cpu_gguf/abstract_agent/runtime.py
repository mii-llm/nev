"""Schema-driven tool loop. No task/domain names, request grammar, or answer templates."""
import copy
import hashlib
import json
import random
import re
import time
from jsonschema import Draft202012Validator

ARMS=['nesso_only','shuffled','nev_ranked','nev_gated']
NONCALL=['__answer__','__clarify__','__unsupported__']


def parse_calls(text):
    if '<tool_call' not in text and '</tool_call>' not in text:return [],None
    matches=list(re.finditer(r'<tool_call>\s*(.*?)\s*</tool_call>',text,re.S))
    remainder=re.sub(r'<tool_call>\s*.*?\s*</tool_call>','',text,flags=re.S).strip()
    if not matches or remainder:return [],'malformed_or_mixed_tool_markup'
    try:calls=[json.loads(m.group(1)) for m in matches]
    except json.JSONDecodeError:return [],'invalid_json'
    if any(not isinstance(c,dict) or set(c)!={'name','arguments'} for c in calls):return [],'invalid_call_shape'
    return calls,None


def scalars(value):
    if isinstance(value,dict):return [s for v in value.values() for s in scalars(v)]
    if isinstance(value,list):return [s for v in value for s in scalars(v)]
    return [value]


def grounded(value,schema,user,observations):
    if 'enum' in schema and value in schema['enum']:return True
    if isinstance(value,dict):return all(grounded(v,schema.get('properties',{}).get(k,{}),user,observations) for k,v in value.items())
    if isinstance(value,list):return all(grounded(v,schema.get('items',{}),user,observations) for v in value)
    if any(type(value)==type(v) and value==v for o in observations for v in scalars(o)):return True
    if isinstance(value,str):
        return bool(value) and re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',user,re.I) is not None
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        return any(float(s)==value for s in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])',user))
    if isinstance(value,bool):return re.search(r'\b'+str(value).lower()+r'\b',user,re.I) is not None
    return value is None and 'null' in user.lower()


def validate_call(call,tools,user,observations):
    name=call.get('name')
    if not isinstance(name,str) or name not in tools:return 'unknown_tool'
    args=call.get('arguments')
    schema=copy.deepcopy(tools[name]['function']['parameters'])
    schema.setdefault('additionalProperties',False)
    if list(Draft202012Validator(schema).iter_errors(args)):return 'schema_violation'
    if not grounded(args,schema,user,observations):return 'argument_not_grounded'
    return None


class GenericAgent:
    def __init__(self,backend):self.backend=backend

    def run(self,request,language,schemas,executor,arm,seed):
        if arm not in ARMS:raise ValueError('Unknown arm')
        tools={s['function']['name']:s for s in schemas}
        if len(tools)!=len(schemas) or not tools:raise ValueError('Unique nonempty tool registry required')
        if set(tools)&set(NONCALL):raise ValueError('Reserved decision names')
        for s in tools.values():Draft202012Validator.check_schema(s['function']['parameters'])
        history=[{'role':'user','content':request}]
        emitted=[];executed=[];trace=[];observations=[];errors=[];cache={};rank_ms=0.0;tokens=0;final='';status='limit'
        self.backend.synchronize();started=time.perf_counter()
        for turn in range(4):
            names=list(tools);ranking=None
            if arm=='shuffled':random.Random(seed).shuffle(names)
            if arm in ('nev_ranked','nev_gated'):
                ranking=self.backend.rank(request,language,list(tools.values()),executed,observations,arm=='nev_gated')
                rank_ms+=ranking['elapsed_ms']
                names=sorted(names,key=lambda n:-ranking['probabilities'][n])
            context=('Sei un assistente operativo. Usa gli strumenti disponibili quando serve.' if language=='it' else
                     'You are an operational assistant. Use the available tools when needed.')
            system=context+'\n<tools>\n'+json.dumps([tools[n] for n in names],ensure_ascii=False,separators=(',',':'))+'\n</tools>'
            text,generated,truncated=self.backend.generate([{'role':'system','content':system}]+history)
            tokens+=generated;calls,parse_error=parse_calls(text)
            event={'turn':turn,'tool_order':names,'ranking':ranking,'assistant':text,'calls':calls,
                   'parse_error':parse_error,'truncated':truncated,'observations':[],'validation':[]}
            trace.append(event);history.append({'role':'assistant','content':text});emitted.extend(calls)
            if parse_error or truncated:
                errors.append(parse_error or 'truncated');status='invalid_output';break
            if not calls:final=text;status='answered';break
            if arm=='nev_gated' and ranking['choice'] in NONCALL:
                errors.append('blocked_by_nev:'+ranking['choice']);status='blocked_by_nev';break
            if len(calls)>4 or turn==3:
                errors.append('call_or_turn_limit');status='limit';break
            issues=[{'call':c,'error':validate_call(c,tools,request,observations)} for c in calls]
            event['validation']=issues
            if any(i['error'] for i in issues):
                errors.extend(i['error'] for i in issues if i['error'])
                history.append({'role':'tool','content':json.dumps({'error':'batch_validation_failed','issues':issues},ensure_ascii=False,separators=(',',':'))})
                continue
            if len(executed)+len(calls)>8:
                errors.append('execution_limit');status='limit';break
            outputs=[]
            for call in calls:
                key=json.dumps(call,sort_keys=True,ensure_ascii=False)
                if key in cache:
                    result=cache[key];cached=True
                else:
                    result=executor(call);cache[key]=result;cached=False
                    executed.append({'turn':turn,'call':call})
                    if not (isinstance(result,dict) and result.get('error')):observations.append(result)
                outputs.append(result)
                event['observations'].append({'call':call,'result':result,'cached':cached})
            payload=outputs[0] if len(outputs)==1 else outputs
            history.append({'role':'tool','content':json.dumps(payload,ensure_ascii=False,separators=(',',':'))})
        self.backend.synchronize()
        return {'arm':arm,'status':status,'final':final,'emitted_calls':emitted,'executed_calls':executed,
                'trace':trace,'errors':errors,'generated_tokens':tokens,'rank_ms':rank_ms,
                'total_ms':(time.perf_counter()-started)*1000}


def render(record):
    lines=[f"User ({record['language']}): {record['request']}",f"Variant: {record['arm']}"]
    for event in record['trace']:
        lines.append(f"\nTurn {event['turn']+1}; tools: "+', '.join(event['tool_order']))
        if event['ranking']:lines.append('Nev next choice: '+event['ranking']['choice'])
        lines.append('Nesso3: '+event['assistant'])
        for item in event['validation']:
            if item['error']:lines.append('Rejected: '+json.dumps(item,ensure_ascii=False))
        for o in event['observations']:lines.append(('Cached' if o['cached'] else 'Tool result')+': '+json.dumps(o,ensure_ascii=False))
    lines.extend([f"\nStatus: {record['status']}",'Errors: '+', '.join(record['errors']),f"Elapsed: {record['total_ms']/1000:.2f} s"])
    return '\n'.join(lines)
