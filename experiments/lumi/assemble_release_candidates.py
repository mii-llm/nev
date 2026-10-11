"""Assemble two local research-release candidates without touching source artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main(root,draft,out):
    sources={'v2':root/'releases/preparation-v1/v2-export/model',
             'v3':root/'runs/bilingual-all-v1/focused-pilot-v3/private-export'}
    pins=json.loads((draft/'weight-sources.json').read_text())
    if out.exists():raise FileExistsError('Refusing to overwrite a staged release candidate')
    # Verify both sources before creating a destination.
    for variant,source in sources.items():
        for name,h in pins[variant].items():assert sha(source/name)==h,(variant,name)
    out.mkdir(parents=True)
    release={'status':'staged_draft','public_upload':False,'models':{}}
    shared=['LICENSE','NOTICE','INFERENCE.md','BUILD.md','EXPERIMENTS.md','EXPORT_COMPARISON.md','export-comparison.json','environment.json','parent-provenance.json']
    for variant,source in sources.items():
        dest=out/variant;dest.mkdir()
        for name in ['backbone','tokenizer']:
            shutil.copytree(source/name,dest/name)
        for name in ['config.json','decision_head.safetensors','calibration.json']:
            shutil.copy2(source/name,dest/name)
        # Keep the exact evaluated weights/config, and record changed documentation.
        core={n:h for n,h in pins[variant].items() if n.startswith(('backbone/','tokenizer/')) or n in ('config.json','decision_head.safetensors','calibration.json')}
        for n,h in core.items():assert sha(dest/n)==h,(variant,n)
        for name in ['conversion.json','evaluation.json']:
            obj=(source/name).read_text().replace(str(root),'${PROJECT_ROOT}')
            (dest/name).write_text(obj)
        shutil.copy2(draft/'models'/variant/'README.md',dest/'README.md')
        for name in shared:shutil.copy2(draft/name,dest/name)
        shutil.copytree(draft/'runtime',dest/'runtime')
        shutil.copytree(draft/'examples',dest/'examples')
        provenance={'variant':variant,'source_artifact_sha256':pins[variant],
                    'unchanged_core_sha256':core,'documentation':'Model card, notices and shared research documentation added; site path in conversion/evaluation metadata parameterized; evaluated weights/config unchanged',
                    'publication_status':'draft; repository name not finalized; no upload'}
        (dest/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        manifest={str(p.relative_to(dest)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file()}
        (dest/'FILE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        release['models'][variant]={'files':len(manifest),'bytes':sum(v['bytes'] for v in manifest.values()),'file_manifest_sha256':sha(dest/'FILE_MANIFEST.json'),'unchanged_core_files':len(core)}
    (out/'release-candidates.json').write_text(json.dumps(release,indent=2)+'\n')
    print(json.dumps(release),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--draft',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();main(a.root,a.draft,a.out)
