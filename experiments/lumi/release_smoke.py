"""Check the locally installed release runtime and the published bilingual example."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main(root):
    out=root/'releases/preparation-v1'
    with tempfile.TemporaryDirectory(dir=out,prefix='smoke-') as tmp:
        tmp=Path(tmp);build=tmp/'runtime';install=tmp/'installed'
        shutil.copytree(out/'draft/runtime',build)
        subprocess.run([sys.executable,'-m','pip','install','--no-deps','--no-build-isolation','--no-index','--target',str(install),str(build)],check=True)
        env={**os.environ,'PYTHONPATH':str(install)+os.pathsep+os.environ.get('PYTHONPATH',''),
             'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HOME':str(tmp/'empty-cache')}
        imported=subprocess.check_output([sys.executable,'-c','import decision_model; print(decision_model.__file__)'],env=env,text=True).strip()
        assert imported.startswith(str(install)), imported
        outputs={}
        for variant in ('v2','v3'):
            for language in ('en','it'):
                data=subprocess.check_output([sys.executable,str(out/'candidates'/variant/'examples/decide.py'),
                    '--model',str(out/'candidates'/variant),'--language',language,'--device','cuda'],env=env,text=True)
                result=json.loads(data)
                assert result['answers']['route']['choice'] in ('shipping','billing','account')
                outputs[variant+'/'+language]=result
        report={'status':'complete','scope':'Isolated pip installation and four actual example invocations on LUMI with existing tested dependencies; not a fresh machine or other GPU platform',
                'offline':True,'examples':outputs}
        (out/'smoke-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('SMOKE COMPLETE',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();main(a.root)
