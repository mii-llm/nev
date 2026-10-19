"""Qwen3 native tools/chat adapter for the existing frozen decision-agent controller."""
import copy
import hashlib
import json
import re
import time

MODEL=('Qwen/Qwen3-0.6B','c1899de289a04d12100db370d81485cdf75e47ca')
MAX_NEW_TOKENS=192


def native_messages(messages):
    """Unpack the controller's schema envelope; never read evaluation references."""
    messages=copy.deepcopy(messages)
    if not messages or messages[0]['role']!='system':raise ValueError('Expected system message')
    content=messages[0]['content']
    match=re.fullmatch(r'(.*?)\n<tools>\n(.*?)\n</tools>',content,re.S)
    if not match:return messages,None
    schemas=json.loads(match.group(2))
    if not isinstance(schemas,list):raise ValueError('Expected tool schema list')
    messages[0]['content']=match.group(1)
    # The controller stores valid calls as text. Qwen's native template expects
    # structured assistant tool_calls for prior turns. Invalid/mixed output stays
    # text so this adapter cannot repair a model error behind the scorer's back.
    for message in messages[1:]:
        if message['role']!='assistant':continue
        text=message['content']
        matches=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',text,re.S)
        rest=re.sub(r'<tool_call>\s*.*?\s*</tool_call>','',text,flags=re.S).strip()
        if not matches or rest:continue
        try:calls=[json.loads(m) for m in matches]
        except json.JSONDecodeError:continue
        if any(not isinstance(c,dict) or set(c)!={'name','arguments'} or not isinstance(c['name'],str) or not isinstance(c['arguments'],dict) for c in calls):continue
        message['content']=''
        message['tool_calls']=[{'type':'function','function':c} for c in calls]
    return messages,schemas


class Backend:
    def __init__(self):
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        from huggingface_hub import snapshot_download
        self.torch=torch;self.generation_metrics=[]
        free,total=torch.cuda.mem_get_info();cap=4*1024**3
        if free<cap:raise RuntimeError('Need 4 GiB free GPU memory')
        torch.cuda.set_per_process_memory_fraction(cap/total)
        path=snapshot_download(MODEL[0],revision=MODEL[1],allow_patterns=['*.json','*.safetensors','*.jinja','*.txt','*.model'],local_files_only=True,token=False)
        self.tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
        self.generator=AutoModelForCausalLM.from_pretrained(path,dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True).to('cuda').eval()
        self.template_sha256=hashlib.sha256(self.tokenizer.chat_template.encode()).hexdigest()
        self.parameter_count=self.generator.num_parameters()
        self.model_allocated_mib=torch.cuda.memory_allocated()/1024**2
    def synchronize(self):self.torch.cuda.synchronize()
    def generate(self,messages):
        self.synchronize();start=time.perf_counter()
        converted,schemas=native_messages(messages)
        kwargs={'tokenize':False,'add_generation_prompt':True,'enable_thinking':False}
        if schemas is not None:kwargs['tools']=schemas
        prompt=self.tokenizer.apply_chat_template(converted,**kwargs)
        # The native template already includes all special tokens.
        inputs=self.tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda')
        with self.torch.inference_mode():
            output=self.generator.generate(**inputs,max_new_tokens=MAX_NEW_TOKENS,do_sample=False,
                repetition_penalty=1.0,no_repeat_ngram_size=0,
                eos_token_id=self.tokenizer.eos_token_id,pad_token_id=self.tokenizer.pad_token_id)
        ids=output[0,inputs['input_ids'].shape[1]:].tolist()
        ended=bool(ids) and ids[-1]==self.tokenizer.eos_token_id
        raw=self.tokenizer.decode(ids,skip_special_tokens=False)
        text=self.tokenizer.decode(ids[:-1] if ended else ids,skip_special_tokens=False).strip()
        self.synchronize()
        self.generation_metrics.append({'prompt_tokens':int(inputs['input_ids'].shape[1]),'generated_tokens':len(ids),
             'elapsed_ms':(time.perf_counter()-start)*1000,'raw_completion':raw,
             'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'truncated':len(ids)>=MAX_NEW_TOKENS and not ended})
        return text,len(ids),len(ids)>=MAX_NEW_TOKENS and not ended
    def rank(self,*args,**kwargs):raise RuntimeError('Qwen-only baseline must not call Nev')
    def close(self):del self.generator;self.torch.cuda.empty_cache()
