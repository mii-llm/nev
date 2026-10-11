"""Frozen final Laya comparison and private export checks after v3 selection."""
import argparse
import gc
import json
import os
from pathlib import Path
import sys


def main(out):
    manifest=json.loads((out/'manifest.json').read_text())
    run_root=Path(manifest['root']);root=run_root.parent.parent
    source=run_root/'training-source'
    sys.path.insert(0,str(source));sys.path.insert(0,str(root/'references/decision-index'))
    # Fresh-process export verification must import the same frozen implementation.
    os.environ['PYTHONPATH']=str(source)+os.pathsep+os.environ.get('PYTHONPATH','')
    import torch
    from decision_model.data import digest, load_split
    from decision_subset_engine import LayaEngine
    from compare_latest import external_meta, practical_rows, existing_practical, common_panel, check_laya_encoding, decode_answer, save
    from run_focused_v3 import infer, summarize
    for name,h in manifest['source_sha256'].items():assert digest(out/'source'/name)==h
    report=json.loads((out/'results/report.json').read_text())
    assert report['status']=='complete'
    selection=json.loads((out/'results/selection.json').read_text())
    assert selection==report['selection'] and selection['identity']['manifest_sha256']==digest(out/'manifest.json')
    records=load_split(out/'data','test');panel=practical_rows(records)
    models={}
    for _,name,path in selection['candidates']:
        rows=json.loads((out/'results'/(name+'-test-logits.json')).read_text())['rows']
        models[name]=existing_practical(rows,panel)
    target=out/'results/laya-test.jsonl'
    existing=[json.loads(s) for s in target.read_text().splitlines()] if target.exists() else []
    done={r['id']:r for r in existing}
    assert len(done)==len(existing)
    engine=LayaEngine(str(root))
    save(out/'results/laya-provenance.json',engine.provenance)
    with target.open('a') as stream:
        for i,row in enumerate(panel):
            meta=external_meta(row)
            if row['id'] in done:
                assert all(done[row['id']][k]==v for k,v in meta.items());continue
            qid,=row['questions'];q=row['questions'][qid]
            if not check_laya_encoding(engine.agent.tok,row['state'],q):
                value={**meta,'status':'unsupported','correct':False}
            else:
                response=engine.agent.predict(row['state'],row['questions'],max_len=8192,head_max_len=8184)
                assert not response['usage'].get('truncated',False) and engine.agent.cpu_fallback_count==0
                assert set(response['answers'])=={qid} and response['answers'][qid]['type']==q['type']
                answer,prob,tie=decode_answer(q,response['answers'][qid])
                value={**meta,'status':'ok','correct':answer==meta['expected'],'choice':answer,'probabilities':prob,'rounded_probability_tie':tie}
            stream.write(json.dumps(value,ensure_ascii=False)+'\n');stream.flush();done[row['id']]=value
            if (i+1)%200==0:print('LAYA',i+1,'/',len(panel),flush=True)
    assert set(done)=={r['id'] for r in panel}
    models['laya']=[done[r['id']] for r in panel]
    comparison={'status':'complete','selection':selection,'manifest_sha256':digest(out/'manifest.json'),
                'panel':common_panel(models),'limitations':manifest['limitations']}
    save(out/'results/comparison.json',comparison)
    del engine;gc.collect();torch.cuda.empty_cache()
    selected=selection['selected_before_test']
    checkpoint=next(path for _,name,path in selection['candidates'] if name==selected)
    calibration=report['models'][selected]['calibration']
    from decision_model.export import export
    from decision_model.model import DecisionModel
    export_dir=out/'private-export'
    if not (export_dir/'conversion.json').exists():
        checks=[r['request'] for r in records[:8]]+[r['request'] for r in load_split(out/'data','guard')[:8]]
        export(checkpoint,export_dir,calibration=calibration,
               conversion={'scope':'Private experimental candidate; not public release approval',
                           'experiment_manifest_sha256':digest(out/'manifest.json'),
                           'recipe_sha256':manifest['recipe_sha256']},
               dtype=torch.float32,device='cuda',check_requests=checks)
    model=DecisionModel.from_pretrained(export_dir,device='cuda')
    exported,_=infer(model,records)
    baseline=json.loads((out/'results'/(selected+'-test-logits.json')).read_text())['rows']
    assert [(r['record_id'],r['qid'],r['keys'],r['label']) for r in exported]==[(r['record_id'],r['qid'],r['keys'],r['label']) for r in baseline]
    argmax=lambda r:max(range(len(r['logits'])),key=r['logits'].__getitem__)
    flips=sum(argmax(a)!=argmax(b) for a,b in zip(exported,baseline))
    export_evaluation={'status':'complete','selected':selected,'argmax_changes_vs_adapter_bf16':flips,
                       'metrics':summarize(exported),'dtype':'float32 parameters / bfloat16 autocast',
                       'release_ready':False,'note':'Confidence policy and distribution-shift limitations still require review; no upload performed.'}
    save(out/'results/export-test-logits.json',{'rows':exported})
    save(out/'results/export-evaluation.json',export_evaluation)
    save(export_dir/'evaluation.json',export_evaluation)
    with (export_dir/'README.md').open('a') as f:
        f.write('\n## Experimental status\n\nPrivate candidate, not a completed public release. Training and tests are 50% EN/50% IT. New tests are synthetic 16-intent and routing cases, not full CLINC or real traffic. Read the preserved experiment manifest and results. A temperature does not guarantee correctness. No automated confidence threshold should be used without validating the recorded calibration policy and distribution shift.\n')
    completion={'status':'complete','selected':selected,'comparison_sha256':digest(out/'results/comparison.json'),
                'export_evaluation_sha256':digest(out/'results/export-evaluation.json'),
                'private_export':str(export_dir),'public_upload':False}
    save(out/'results/completion.json',completion)
    print('FINISHED',json.dumps(completion),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
