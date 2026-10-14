"""CPU reference / F16 / Q8 conversion diagnostics; these are not a new accuracy benchmark."""
import argparse
import gc
import json
from pathlib import Path
import re
import time
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from decision_model import DecisionModel
from decision_model.render import rows_of
from cpu_backend import ROOT,Worker,NevGGUF
p=argparse.ArgumentParser();p.add_argument('stage',choices=['nesso','nev']);args=p.parse_args()
torch.set_num_threads(4)
kits=json.loads((ROOT/'abstract_agent/toolsets.json').read_text());cases=json.loads((ROOT/'abstract_agent/cases.json').read_text())['cases']
output=ROOT/f'results/verify-{args.stage}.json'
if output.exists():raise FileExistsError(output)
report={'stage':args.stage,'threads':4,'device':'cpu','rows':[]}

def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

def scores(answer):return [float(v) for v in answer['probabilities'].values()]

if args.stage=='nesso':
 tok=AutoTokenizer.from_pretrained(ROOT/'models/nesso3',local_files_only=True)
 chosen=[c for c in cases if not c['renamed'] and (c['kind']=='single' or (c['toolset']=='sensors' and c['kind']=='dependent'))]
 model=AutoModelForCausalLM.from_pretrained(ROOT/'models/nesso3',dtype=torch.float32,attn_implementation='eager',local_files_only=True).to('cpu').eval()
 for c in chosen:
  tools=kits[c['toolset']]['schemas'][c['language']]
  context='Sei un assistente operativo. Usa gli strumenti disponibili quando serve.' if c['language']=='it' else 'You are an operational assistant. Use the available tools when needed.'
  system=context+'\n<tools>\n'+json.dumps(tools,ensure_ascii=False,separators=(',',':'))+'\n</tools>'
  prompt=tok.apply_chat_template([{'role':'system','content':system},{'role':'user','content':c['request']}],tokenize=False,add_generation_prompt=True)
  ids=tok.encode(prompt,add_special_tokens=True);x=torch.tensor([ids]);start=time.perf_counter()
  with torch.inference_mode():y=model.generate(input_ids=x,attention_mask=torch.ones_like(x),max_new_tokens=96,do_sample=False,eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id)
  generated=y[0,len(ids):].tolist()
  report['rows'].append({'id':c['id'],'prompt':prompt,'prompt_ids':ids,'reference_ids':generated,'reference_text':tok.decode(generated,skip_special_tokens=True),'reference_ms':(time.perf_counter()-start)*1000})
  save();print('reference',c['id'],flush=True)
 del model;gc.collect()
 for precision in ['f16','q8']:
  worker=Worker(ROOT/f'gguf/nesso3-{precision}.gguf','generate',4)
  try:
   for row in report['rows']:
    tokenize=worker.request({'tokenize':row['prompt'],'add_special':True})
    got=worker.request({'ids':row['prompt_ids'],'max_new_tokens':96})
    row[precision]={'tokenizer_exact':tokenize['ids']==row['prompt_ids'],'generation_exact':got['ids']==row['reference_ids'],
       'ids':got['ids'],'text':tok.decode(got['ids'],skip_special_tokens=True),'elapsed_ms':got['elapsed_ms'],'prefill_ms':got['prefill_ms'],'truncated':got['truncated']}
    save();print(precision,row['id'],'tokenizer',row[precision]['tokenizer_exact'],'generation',row[precision]['generation_exact'],flush=True)
  finally:worker.close()
else:
 requests=[]
 for c in cases:
  if c['renamed'] or c['kind'] not in ('single','selection','dependent'):continue
  tools=kits[c['toolset']]['schemas'][c['language']]
  criteria={s['function']['name']:s['function']['description']+' '+json.dumps(s['function']['parameters'],ensure_ascii=False,separators=(',',':')) for s in tools}
  instruction='Seleziona il prossimo passo utile per completare la richiesta, considerando i risultati già ricevuti.' if c['language']=='it' else 'Select the next useful step to complete the request, considering results already received.'
  requests.append({'id':c['id'],'state':json.dumps({'request':c['request'],'completed_calls':[],'observations':[]},ensure_ascii=False,separators=(',',':')),'questions':{'next':{'type':'choice','instructions':instruction,'criteria':criteria}}})
 for lang in ['en','it']:
  requests.append({'id':'typed-'+lang,'state':'The package arrived broken and I want a refund.' if lang=='en' else 'Il pacco è arrivato rotto e voglio un rimborso.',
   'questions':{'route':{'type':'choice','instructions':'Select the request type.' if lang=='en' else 'Seleziona il tipo di richiesta.','criteria':{'refund':'Refund or damaged goods','account':'Account access','info':'Product information'}},
    'damage':{'type':'noul','instructions':'Does the user report damage?' if lang=='en' else "L'utente segnala danni?"},
    'sentiment':{'type':'score','instructions':'Assess sentiment.' if lang=='en' else 'Valuta il sentimento.','criteria':['negative','neutral','positive']}}})
 model=DecisionModel.from_pretrained(ROOT/'models/nev/v3',device='cpu',dtype=torch.float32,attn='eager')
 for request in requests:
  start=time.perf_counter();result=model.evaluate(request['state'],request['questions'],form='rows')
  report['rows'].append({'id':request['id'],'request':{k:request[k] for k in ['state','questions']},'reference':result,'reference_ms':(time.perf_counter()-start)*1000});save();print('reference',request['id'],flush=True)
 # Compare final-normalized readout vectors on a full multi-question request.
 request=requests[-1];enc,meta=NevGGUF.encode(type('Encoder',(),{'tok':model.tok,'cfg':json.loads((ROOT/'models/nev/v3/config.json').read_text())})(),request['state'],request['questions'])
 prefix,pp,branches=rows_of(enc)
 with torch.inference_mode():hs=model._rows_hidden([(prefix+r['ids'],pp+r['pos']) for r in branches])
 expected_hidden=[h[[len(prefix)+i for i in r['opts']]+[len(prefix)+r['decide']]].numpy() for h,r in zip(hs,branches)]
 del model;gc.collect()
 for precision in ['f16','q8']:
  model=NevGGUF(precision,4)
  try:
   for row in report['rows']:
    got=model.evaluate(**row['request']);deltas=[];agreements=[]
    for key,a in got['answers'].items():
     target=row['reference']['answers'][key];x=scores(a);y=scores(target);deltas.append(max(abs(xx-yy) for xx,yy in zip(x,y)));agreements.append(int(np.argmax(x))==int(np.argmax(y)))
    row[precision]={'result':got,'max_probability_error':max(deltas),'all_choices_match':all(agreements),'question_agreements':agreements};save();print(precision,row['id'],row[precision]['max_probability_error'],all(agreements),flush=True)
   hidden_errors=[]
   for r,expected in zip(branches,expected_hidden):
    out=model.worker.request({'ids':prefix+r['ids'],'positions':[len(prefix)+i for i in r['opts']]+[len(prefix)+r['decide']]})
    actual=np.asarray(out['hidden']);hidden_errors.append({'max_abs':float(abs(actual-expected).max()),'mean_abs':float(abs(actual-expected).mean())})
   report[precision+'_hidden_errors']=hidden_errors
   text='<|reserved_special_token_0|>Richiesta italiana: perché? English request.'
   report[precision+'_tokenizer_exact']=model.worker.request({'tokenize':text,'add_special':False})['ids']==model.tok.encode(text,add_special_tokens=False)
   save()
  finally:model.close()
report['status']='complete';save()
