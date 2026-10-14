import json
from pathlib import Path
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parent
models={
 'nesso3':('giux78/nesso3-0.4B-agentic','56f42f1c7eb82fbd48b0c4ee46aae7b8bed203b8',['*.json','*.safetensors','*.jinja','tokenizer.model']),
 'nev':('giux78/nev','c5c84121263b423f8846811a24790ab96e66cee3',['v3/**'])}
paths={}
for name,(repo,revision,patterns) in models.items():
 path=snapshot_download(repo,revision=revision,allow_patterns=patterns,local_dir=ROOT/'models'/name,max_workers=2)
 paths[name]={'repository':repo,'revision':revision,'path':str(Path(path)/'v3') if name=='nev' else path}
 print('Downloaded',name,flush=True)
(ROOT/'models.json').write_text(json.dumps(paths,indent=2)+'\n')
