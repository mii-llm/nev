"""CPU-only GGUF inference; Nev keeps its released FP32 head and exact renderer."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
from safetensors.numpy import load_file
from transformers import AutoTokenizer
from decision_model.render import encode_request,rows_of,delimiter_ids
from decision_model.schema import DecisionRequest,to_answers

ROOT=Path(__file__).resolve().parent

class Worker:
    def __init__(self,path,mode,threads=4):
        self.process=subprocess.Popen([str(ROOT/'build/nev-cpu-worker'),str(path),mode,str(threads)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('CPU worker failed to load; inspect stderr')
        self.info=json.loads(line)
        if not self.info.get('cpu_only'):raise RuntimeError('Expected CPU worker')
    def request(self,data):
        self.process.stdin.write(json.dumps(data,ensure_ascii=False)+'\n');self.process.stdin.flush()
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('CPU worker exited')
        result=json.loads(line)
        if 'error' in result:raise RuntimeError(result['error'])
        return result
    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=10)
    def __del__(self):
        if hasattr(self,'process'):self.close()

class NevGGUF:
    def __init__(self,precision='f16',threads=4):
        self.path=ROOT/'models/nev/v3'
        self.cfg=json.loads((self.path/'config.json').read_text())
        self.tok=AutoTokenizer.from_pretrained(self.path/'tokenizer',local_files_only=True)
        if delimiter_ids(self.tok)!=self.cfg['tokenizer']['delimiters']:raise ValueError('Nev delimiter mismatch')
        self.head=load_file(self.path/self.cfg['head']['path'])
        self.worker=Worker(ROOT/f'gguf/nev-v3-{precision}.gguf','embeddings',threads)
    def encode(self,state,questions):
        return encode_request(self.tok,DecisionRequest.model_validate({'state':state,'questions':questions}),max_state=self.cfg['limits']['max_state_tokens'],max_row=self.cfg['limits']['max_row_tokens'])
    def evaluate(self,state,questions):
        start=time.perf_counter();enc,meta=self.encode(state,questions);prefix,_,rows=rows_of(enc);probabilities=[];raw_logits=[]
        for row in rows:
            ids=prefix+row['ids'];positions=[len(prefix)+i for i in row['opts']]+[len(prefix)+row['decide']]
            out=self.worker.request({'ids':ids,'positions':positions});h=np.asarray(out['hidden'],dtype=np.float32)
            q=h[-1]@self.head['q.weight'].T+self.head['q.bias']
            k=h[:-1]@self.head['k.weight'].T+self.head['k.bias']
            logits=(k@q)*np.float32(self.cfg['head']['dim']**-.5)
            z=logits/np.float32(self.cfg['temperature']);p=np.exp(z-z.max());p/=p.sum()
            probabilities.append(p.tolist());raw_logits.append(logits.tolist())
        return {'answers':to_answers(probabilities,meta),'latency_ms':(time.perf_counter()-start)*1000,'form':'gguf_rows','raw_logits':raw_logits,
                'usage':{'state_tokens':enc['n_state'],'branch_tokens':len(enc['ids'])-enc['n_state'],'questions':len(rows)}}
    def close(self):self.worker.close()

class Backend:
    def __init__(self,precision='f16',threads=4,engine='gguf'):
        self.engine=engine;self.tok=AutoTokenizer.from_pretrained(ROOT/'models/nesso3',local_files_only=True)
        if engine=='gguf':
            self.generator=Worker(ROOT/f'gguf/nesso3-{precision}.gguf','generate',threads)
            self.nev=NevGGUF(precision,threads)
        else:
            import torch
            from transformers import AutoModelForCausalLM
            from decision_model import DecisionModel
            torch.set_num_threads(threads);self.torch=torch
            self.generator=AutoModelForCausalLM.from_pretrained(ROOT/'models/nesso3',dtype=torch.float32,attn_implementation='eager',local_files_only=True).to('cpu').eval()
            self.nev=DecisionModel.from_pretrained(ROOT/'models/nev/v3',device='cpu',dtype=torch.float32,attn='eager')
        self.generation_metrics=[]
    def synchronize(self):pass
    def generate(self,messages):
        prompt=self.tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        ids=self.tok.encode(prompt,add_special_tokens=True)
        if ids[0]!=self.tok.bos_token_id or ids[1]==self.tok.bos_token_id:raise ValueError('BOS contract')
        if self.engine=='gguf':
            out=self.generator.request({'ids':ids,'max_new_tokens':192});tokens=out['ids'];truncated=out['truncated']
            self.generation_metrics.append({'prompt_tokens':len(ids),'generated_tokens':len(tokens),'prefill_ms':out['prefill_ms'],'elapsed_ms':out['elapsed_ms']})
        else:
            inputs=self.torch.tensor([ids]);start=time.perf_counter()
            with self.torch.inference_mode():
                output=self.generator.generate(input_ids=inputs,attention_mask=self.torch.ones_like(inputs),max_new_tokens=192,do_sample=False,
                    repetition_penalty=1.0,no_repeat_ngram_size=0,eos_token_id=self.tok.eos_token_id,pad_token_id=self.tok.pad_token_id)
            tokens=output[0,len(ids):].tolist();truncated=len(tokens)==192 and tokens[-1]!=self.tok.eos_token_id
            self.generation_metrics.append({'prompt_tokens':len(ids),'generated_tokens':len(tokens),'elapsed_ms':(time.perf_counter()-start)*1000})
        text=re.split(r'<\|eot_id\|>|<\|end_of_text\|>',self.tok.decode(tokens,skip_special_tokens=False))[0].strip()
        return text,len(tokens),truncated
    def rank(self,request,language,tools,executed,observations,gate):
        criteria={s['function']['name']:s['function']['description']+' '+json.dumps(s['function']['parameters'],ensure_ascii=False,separators=(',',':')) for s in tools}
        if gate:
            criteria.update({'__answer__':'Rispondi usando le informazioni già disponibili, senza strumenti.' if language=='it' else 'Answer using information already available, without tools.',
                '__clarify__':'Chiedi un dato necessario mancante prima di chiamare strumenti.' if language=='it' else 'Ask for a missing required value before calling tools.',
                '__unsupported__':'La richiesta richiede una funzione non disponibile; spiega il limite senza eseguire altre azioni.' if language=='it' else 'The request needs an unavailable capability; explain the limitation without other actions.'})
        state=json.dumps({'request':request,'completed_calls':[e['call'] for e in executed],'observations':observations},ensure_ascii=False,separators=(',',':'))
        instruction='Seleziona il prossimo passo utile per completare la richiesta, considerando i risultati già ricevuti.' if language=='it' else 'Select the next useful step to complete the request, considering results already received.'
        start=time.perf_counter();result=self.nev.evaluate(state=state,questions={'next':{'type':'choice','instructions':instruction,'criteria':criteria}})
        answer=result['answers']['next']
        return {'choice':answer['choice'],'probabilities':answer['probabilities'],'elapsed_ms':(time.perf_counter()-start)*1000}
    def close(self):
        if self.engine=='gguf':self.generator.close();self.nev.close()
