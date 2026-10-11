"""Regenerate the authored bilingual splits without a model, GPU or network.

Training output contains synthetic records only; original-data replay is separate.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

p=argparse.ArgumentParser()
p.add_argument('--variant',choices=['v2','v3'],required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
if a.out.exists():raise FileExistsError('Choose a new output directory; existing data will not be replaced')
sys.path.insert(0,str(root/'recipe-source'/a.variant))
generator=importlib.import_module('practical_data_v2' if a.variant=='v2' else 'focused_data_v3')
from practical_data import validate_pairs
splits=generator.generate()
counts=validate_pairs(splits)
pins=json.loads((root/'recipes/synthetic-split-hashes.json').read_text())[a.variant]
encoded={name:''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows).encode('utf-8') for name,rows in splits.items()}
for name,expected in pins.items():assert hashlib.sha256(encoded[name]).hexdigest()==expected, 'Historical split mismatch: '+name
a.out.mkdir(parents=True)
for name,data in encoded.items():(a.out/(name+'.jsonl')).write_bytes(data)
manifest={'variant':a.variant,'scope':'Authored synthetic examples only; no original-data replay or guards',
          'counts':counts,'historical_heldout_hashes_verified':True,
          'replay_records_required':4096 if a.variant=='v2' else 6144,
          'files':{name+'.jsonl':{'records':len(splits[name]),'sha256':hashlib.sha256(data).hexdigest()} for name,data in encoded.items()}}
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'variant':a.variant,'counts':counts,'historical_heldout_hashes_verified':True}))
