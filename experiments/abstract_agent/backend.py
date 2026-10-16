"""Pinned native model serving. Tool descriptions and schemas are runtime inputs."""
import json
from pathlib import Path
import re
import time

GENERATOR=('mii-llm/nesso3-0.4B-agentic','56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8')
NEV=('mii-llm/nev','c5c84121263b423f8846811a24790ab96e66cee3')

class Backend:
    def __init__(self):
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        from huggingface_hub import snapshot_download
        from decision_model import DecisionModel
        self.torch=torch
        free,total=torch.cuda.mem_get_info();cap=4*1024**3
        if free<cap:raise RuntimeError('Need 4 GiB free GPU memory')
        torch.cuda.set_per_process_memory_fraction(cap/total)
        path=snapshot_download(GENERATOR[0],revision=GENERATOR[1],allow_patterns=['*.json','*.safetensors','*.jinja','tokenizer.model'],local_files_only=True)
        self.tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
        self.generator=AutoModelForCausalLM.from_pretrained(path,dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True).to('cuda').eval()
        self.memory={'after_generator_mib':torch.cuda.memory_allocated()/1024**2}
        npath=Path(snapshot_download(NEV[0],revision=NEV[1],allow_patterns=['v3/**'],local_files_only=True))/'v3'
        self.nev=DecisionModel.from_pretrained(npath,device='cuda')
        self.memory['after_both_models_mib']=torch.cuda.memory_allocated()/1024**2
    def synchronize(self):self.torch.cuda.synchronize()
    def generate(self,messages):
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        inputs=self.tokenizer(prompt,return_tensors='pt',add_special_tokens=True).to('cuda');ids=inputs['input_ids'][0]
        if ids[0].item()!=self.tokenizer.bos_token_id or ids[1].item()==self.tokenizer.bos_token_id:raise RuntimeError('BOS contract mismatch')
        with self.torch.inference_mode():
            out=self.generator.generate(**inputs,max_new_tokens=192,do_sample=False,repetition_penalty=1.0,no_repeat_ngram_size=0,
                eos_token_id=self.tokenizer.eos_token_id,pad_token_id=self.tokenizer.pad_token_id)
        generated=out[0,ids.shape[0]:]
        text=self.tokenizer.decode(generated,skip_special_tokens=False)
        return re.split(r'<\|eot_id\|>|<\|end_of_text\|>',text)[0].strip(),len(generated),len(generated)==192
    def rank(self,request,language,tools,executed,observations,gate):
        criteria={s['function']['name']:s['function']['description']+' '+json.dumps(s['function']['parameters'],ensure_ascii=False,separators=(',',':')) for s in tools}
        if gate:
            criteria.update({'__answer__':'Rispondi usando le informazioni già disponibili, senza strumenti.' if language=='it' else 'Answer using information already available, without tools.',
                '__clarify__':'Chiedi un dato necessario mancante prima di chiamare strumenti.' if language=='it' else 'Ask for a missing required value before calling tools.',
                '__unsupported__':'La richiesta richiede una funzione non disponibile; spiega il limite senza eseguire altre azioni.' if language=='it' else 'The request needs an unavailable capability; explain the limitation without other actions.'})
        state=json.dumps({'request':request,'completed_calls':[e['call'] for e in executed],'observations':observations},ensure_ascii=False,separators=(',',':'))
        instructions=('Seleziona il prossimo passo utile per completare la richiesta, considerando i risultati già ricevuti.' if language=='it' else
                      'Select the next useful step to complete the request, considering results already received.')
        self.synchronize();start=time.perf_counter()
        with self.torch.inference_mode():result=self.nev.evaluate(state=state,questions={'next':{'type':'choice','instructions':instructions,'criteria':criteria}})
        self.synchronize();a=result['answers']['next']
        return {'choice':a['choice'],'probabilities':a['probabilities'],'elapsed_ms':(time.perf_counter()-start)*1000}
