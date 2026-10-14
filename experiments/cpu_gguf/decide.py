import argparse
import json
import os
from pathlib import Path
os.environ['USE_TORCH']='0';os.environ['HF_HUB_OFFLINE']='1'
from cpu_backend import NevGGUF
p=argparse.ArgumentParser(description='Nev v3: GGUF decoder + original FP32 scoring head on CPU.')
p.add_argument('--request',type=Path);p.add_argument('--precision',choices=['f16','q8'],default='f16');args=p.parse_args()
request=json.loads(args.request.read_text()) if args.request else {'state':'Il pacco è arrivato rotto e voglio un rimborso.','questions':{'route':{'type':'choice','instructions':'Seleziona il tipo di richiesta.','criteria':{'refund':'Rimborso o merce danneggiata','account':"Accesso all'account",'info':'Informazioni sui prodotti'}}}}
model=NevGGUF(args.precision)
try:print(json.dumps(model.evaluate(**request),ensure_ascii=False,indent=2))
finally:model.close()
