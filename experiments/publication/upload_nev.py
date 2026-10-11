"""Publish both evaluated Nev variants to the explicitly requested private HF repo."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from huggingface_hub import HfApi

root=Path('/scratch/project_465002563/decision-models/kev-nesso2')
work=root/'releases/publication-nev'
folder=work/'huggingface'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

for variant in ('v2','v3'):
    source=root/'releases/preparation-v1/candidates'/variant
    manifest=json.loads((source/'FILE_MANIFEST.json').read_text())
    for name,spec in manifest.items():assert sha(source/name)==spec['sha256'],name
    dest=folder/variant
    if not dest.exists():shutil.copytree(source,dest)
    shutil.copy2(work/'cards'/variant/'README.md',dest/'README.md')
    # The published card changes; evaluated model tensors/configuration stay exact.
    core=json.loads((source/'provenance.json').read_text())['unchanged_core_sha256']
    for name,h in core.items():assert sha(dest/name)==h,name
    files={str(p.relative_to(dest)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json' and '.cache' not in p.parts}
    (dest/'FILE_MANIFEST.json').write_text(json.dumps(files,indent=2)+'\n')
for name in ('README.md','LICENSE','NOTICE'):
    shutil.copy2(work/'cards'/name,folder/name)
api=HfApi(token=os.environ['HF_TOKEN'])
assert api.whoami()['name']=='giux78'
api.create_repo(repo_id='giux78/nev',repo_type='model',private=True,exist_ok=True)
if not api.model_info('giux78/nev').private:
    api.update_repo_settings(repo_id='giux78/nev',repo_type='model',private=True)
assert api.model_info('giux78/nev').private
print('PRIVATE REPOSITORY VERIFIED; uploading both variants',flush=True)
commit=api.upload_folder(repo_id='giux78/nev',repo_type='model',folder_path=str(folder),
    commit_message='Release Nev bilingual decision variants, model cards and measured provenance',
    ignore_patterns=['**/__pycache__/**','**/.cache/**','**/*.pyc'])
info=api.model_info('giux78/nev',files_metadata=True)
assert info.private
remote={s.rfilename:s for s in info.siblings}
for variant in ('v2','v3'):
    for name in ('backbone/model.safetensors','decision_head.safetensors','config.json','README.md'):
        path=variant+'/'+name;assert path in remote,path
        local=folder/path
        assert remote[path].size==local.stat().st_size,path
        lfs=remote[path].lfs
        if lfs:assert lfs.sha256==sha(local),path
receipt={'status':'complete','repository':'giux78/nev','private':info.private,'commit':info.sha,
         'commit_url':commit.commit_url,'variants':['v2','v3'],
         'verification':'remote file sizes and LFS SHA-256 checked for both model weights; evaluated core files unchanged',
         'card_sha256':sha(folder/'README.md')}
(work/'huggingface-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
