"""Add final recipe/source documentation while keeping all evaluated core files fixed."""
import argparse
import json
from pathlib import Path
import shutil
from assemble_release_candidates import sha


def main(preparation):
    draft=preparation/'draft';out=preparation/'candidates'
    smoke=json.loads((preparation/'smoke-report.json').read_text())
    assert smoke['status']=='complete'
    history=preparation/'candidate-manifests-before-doc-refresh'
    history.mkdir(exist_ok=False)
    release=json.loads((out/'release-candidates.json').read_text())
    shutil.copy2(out/'release-candidates.json',history/'release-candidates.json')
    shared=['LICENSE','NOTICE','INFERENCE.md','BUILD.md','EXPERIMENTS.md','COMPARISON.md','EXPORT_COMPARISON.md','results.json','export-comparison.json','environment.json','parent-provenance.json','experiment-index.json']
    for variant in ('v2','v3'):
        dest=out/variant
        core=json.loads((dest/'provenance.json').read_text())['unchanged_core_sha256']
        for name,h in core.items():assert sha(dest/name)==h,(variant,name)
        shutil.copy2(dest/'FILE_MANIFEST.json',history/(variant+'-FILE_MANIFEST.json'))
        for name in shared:shutil.copy2(draft/name,dest/name)
        for name in ('recipes','recipe-source','tools'):shutil.copytree(draft/name,dest/name)
        shutil.copy2(preparation/'smoke-report.json',dest/'smoke-report.json')
        manifest={str(p.relative_to(dest)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='FILE_MANIFEST.json'}
        (dest/'FILE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        release['models'][variant]={'files':len(manifest),'bytes':sum(x['bytes'] for x in manifest.values()),'file_manifest_sha256':sha(dest/'FILE_MANIFEST.json'),'unchanged_core_files':len(core)}
    release['documentation_revision']=2
    release['smoke_test']='passed: isolated package install and EN/IT examples for each model, using tested LUMI dependencies'
    (out/'release-candidates.json').write_text(json.dumps(release,indent=2)+'\n')
    print(json.dumps(release),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preparation',type=Path,required=True);a=ap.parse_args();main(a.preparation)
