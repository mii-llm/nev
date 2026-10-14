"""Create a symlinked conversion input for Nev; preserve the original artifact."""
from pathlib import Path
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
source=ROOT/'models/nev/v3';stage=ROOT/'models/nev-conversion';stage.mkdir(exist_ok=True)
for folder in ['backbone','tokenizer']:
 for f in (source/folder).iterdir():
  if f.is_file() and f.name!='config.json':
   dest=stage/f.name
   if not dest.exists():dest.symlink_to(f)
cfg=json.loads((source/'backbone/config.json').read_text())
(stage/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
for name,path in [('nesso3',ROOT/'models/nesso3'),('nev-v3',stage)]:
 dest=ROOT/f'gguf/{name}-f16.gguf'
 if dest.exists():
  print('Keeping existing GGUF',dest,flush=True);continue
 partial=dest.with_suffix('.partial.gguf')
 with (ROOT/f'results/convert-{name}.log').open('w') as log:
  subprocess.run([sys.executable,str(ROOT/'llama.cpp/convert_hf_to_gguf.py'),str(path),'--outfile',str(partial),'--outtype','f16'],stdout=log,stderr=subprocess.STDOUT,check=True)
 partial.replace(dest)
 print('Converted',name,flush=True)
