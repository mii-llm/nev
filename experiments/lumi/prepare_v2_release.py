"""Export the fixed v2 candidate and evaluate its actual merged weights; no upload."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()


def main(root,out):
    run=root/'runs/bilingual-all-v1'; pilot=run/'practical-pilot-v2'
    source=run/'training-source'
    sys.path.insert(0,str(source));sys.path.insert(0,str(root/'references/decision-index'))
    os.environ['PYTHONPATH']=str(source)+os.pathsep+os.environ.get('PYTHONPATH','')
    from compare_latest import load,save,external_meta,existing_practical,practical_rows,summarize,decode_answer
    from run_focused_v3 import infer
    prior=run/'practical-v2-benchmark-comparison-v1'
    assert sha(prior/'manifest.json')=='ee1569b4fe8a36b9a1b8087df18cbffac31b68013a6bc05f106f764aef3e7dff'
    pins=json.loads((prior/'manifest.json').read_text())
    assert sha(pilot/'manifest.json')==pins['pilot_manifest_sha256']
    pm=json.loads((pilot/'manifest.json').read_text())
    for n,h in pm['frozen_runtime_sha256'].items(): assert sha(source/n)==h,n
    checkpoint=pilot/'training/adapted-256'
    for n,h in pins['checkpoint_sha256'].items(): assert sha(checkpoint/n)==h,n
    assert sha(pilot/'results/selection.json')==pins['selection_sha256']
    assert json.loads((pilot/'results/selection.json').read_text())['selected_before_test']=='adapted-256'
    records=load(pilot/'data/test.jsonl')
    assert sha(pilot/'data/test.jsonl')==pins['inputs']['practical_v2']
    assert sha(pilot/'results/report.json')=='4511085a2c35a1fe43c01dd6077cda383209b76af49ada293c4c815a78947f3c'
    calibration=json.loads((pilot/'results/report.json').read_text())['models']['adapted-256']['calibration']
    out.mkdir(parents=True,exist_ok=True)
    manifest={'candidate':'v2_original74k_plus256','checkpoint_sha256':pins['checkpoint_sha256'],
              'frozen_runtime_sha256':pm['frozen_runtime_sha256'],'inputs':pins['inputs'],
              'calibration':calibration,'source_sha256':{p.name:sha(p) for p in (out/'source').iterdir() if p.is_file()},
              'public_upload':False}
    if (out/'manifest.json').exists(): assert json.loads((out/'manifest.json').read_text())==manifest
    else:save(out/'manifest.json',manifest)
    import torch
    from decision_model.export import export
    from decision_model.model import DecisionModel
    from decision_subset_engine import NessoEngine
    from decision_index.engines import Unsupported,validate
    target=out/'model'
    if not (target/'conversion.json').exists():
        checks=[r['request'] for r in records[:8]]
        export(checkpoint,target,calibration=calibration,conversion={'scope':'V2 release preparation; no upload',
               'release_preparation_manifest_sha256':sha(out/'manifest.json')},dtype=torch.float32,device='cuda',check_requests=checks)
    engine=NessoEngine.__new__(NessoEngine)
    engine.model=DecisionModel.from_pretrained(target,device='cuda',dtype=torch.float32).eval()
    predictions={}
    for panel,paths in {'okapi':[run/'decision-index-okapi-v1/rows.jsonl'],
                         'decision_index':[run/f'decision-index-{lang}-selection-v1/selection.jsonl' for lang in ('english','italian')]}.items():
        rows=[]
        for i,p in enumerate(paths):
            key=panel if panel=='okapi' else 'decision_index_'+('english','italian')[i]
            assert sha(p)==pins['inputs'][key]
            rows+=load(p)
        result=[]
        with (out/(panel+'-predictions.jsonl')).open('w') as f:
            for i,r in enumerate(rows):
                meta=external_meta(r);qid,=r['questions']
                try:
                    response,_=engine(r['state'],r['questions']);validate(r['questions'],response)
                    choice,prob,tie=decode_answer(r['questions'][qid],response['answers'][qid])
                    row={**meta,'status':'ok','choice':choice,'correct':choice==meta['expected'],'probabilities':prob,
                         'nll':-math.log(max(prob[meta['expected']],1e-30))}
                except Unsupported as exc:
                    row={**meta,'status':'unsupported','correct':False,'reason':str(exc)}
                result.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
                if (i+1)%200==0:print(panel,i+1,'/',len(rows),flush=True)
        predictions[panel]=result
    logits,performance=infer(engine.model,records)
    save(out/'practical_v2-logits.json',{'rows':logits,'performance':performance})
    predictions['practical_v2']=existing_practical(logits,practical_rows(records))
    (out/'practical_v2-predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predictions['practical_v2']))
    report={'status':'complete','model':'v2_merged_export','manifest_sha256':sha(out/'manifest.json'),
            'panels':{p:summarize(rs) for p,rs in predictions.items()},'numerics':'FP32 parameters / BF16 autocast; external rows T=1; practical packed logits',
            'limitations':['Previously inspected diagnostic subsets','No confidence threshold qualified','No public upload']}
    save(out/'report.json',report)
    save(target/'evaluation.json',report)
    save(out/'artifact-sha256.json',{str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()})
    print('COMPLETE',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();main(a.root,a.out)
