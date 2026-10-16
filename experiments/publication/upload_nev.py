"""Publish both evaluated Nev variants to the public mii-llm HF repository."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
from huggingface_hub import HfApi

root=Path('/scratch/project_465002563/decision-models/kev-nesso2')
work=root/'releases/publication-nev'
folder=work/'huggingface'
lock=(work/'upload.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
receipt_path=work/'huggingface-receipt.json'
if receipt_path.exists():
    previous=json.loads(receipt_path.read_text())
    if previous.get('repository')=='mii-llm/nev' and previous.get('private') is False:
        print(receipt_path.read_text(), flush=True)
        raise SystemExit(0)
print('Uploader started; verifying candidate hashes', flush=True)

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
api=HfApi(token=os.environ.get('HF_TOKEN'))
api.create_repo(repo_id='mii-llm/nev',repo_type='model',private=False,exist_ok=True)
assert not api.model_info('mii-llm/nev').private, 'Expected the existing public release'
print('PUBLIC REPOSITORY VERIFIED; uploading both variants',flush=True)
commit=api.upload_folder(repo_id='mii-llm/nev',repo_type='model',folder_path=str(folder),
    commit_message='Release Nev bilingual decision variants, model cards and measured provenance',
    ignore_patterns=['**/__pycache__/**','**/.cache/**','**/*.pyc'])
info=api.model_info('mii-llm/nev',files_metadata=True)
assert not info.private
remote={s.rfilename:s for s in info.siblings}
for variant in ('v2','v3'):
    for name in ('backbone/model.safetensors','decision_head.safetensors','config.json','README.md'):
        path=variant+'/'+name;assert path in remote,path
        local=folder/path
        assert remote[path].size==local.stat().st_size,path
        lfs=remote[path].lfs
        if lfs:assert lfs.sha256==sha(local),path
receipt={'status':'complete','repository':'mii-llm/nev','private':info.private,'commit':info.sha,
         'commit_url':commit.commit_url,'variants':['v2','v3'],
         'verification':'remote file sizes and LFS SHA-256 checked for both model weights; evaluated core files unchanged',
         'card_sha256':sha(folder/'README.md')}
(work/'huggingface-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
