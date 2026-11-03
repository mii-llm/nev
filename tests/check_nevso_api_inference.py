"""Real GGUF regression against the saved two-case Linux launch comparison."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nevso import Agent, Tool


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference-dir", type=Path,
                   default=ROOT/'docs/nevso/evidence/linux-cpu-20261103')
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): p.error("Use a new output path")
    suite_path = ROOT/'experiments/cpu_gguf/greenhouse_suite.json'
    suite = json.loads(suite_path.read_text())
    kits = suite['toolsets']
    responses = [r for kit in kits.values() for r in kit['responses']]
    schemas = {lang: {s['function']['name']: s['function'] for kit in kits.values()
                     for s in kit['schemas'][lang]} for lang in ('en', 'it')}
    def handler(name):
        def execute(**arguments):
            call = {'name': name, 'arguments': arguments}
            return next((deepcopy(r['result']) for r in responses if r['call'] == call),
                        {'error': 'not_found'})
        return execute
    report = {'status': 'incomplete', 'engine': 'gguf', 'precision': 'q8', 'threads': 4,
              'scope': 'Six launch-case parity trials, not a new benchmark.',
              'source_sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
                                ('nevso/api.py', 'tests/check_nevso_api_inference.py')},
              'suite_sha256': hashlib.sha256(suite_path.read_bytes()).hexdigest(), 'rows': []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save(): a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    targets = {'read_soil_ph-it': 'ph-it.json', 'read_water_tank_level-en': 'tank-en.json'}
    for i, case in enumerate(suite['cases']):
        if case['id'] not in targets: continue
        lang = case['language']
        names = list(schemas[lang])
        random.Random(7100+i//2).shuffle(names)
        tools = [Tool(name, {l: schemas[l][name]['description'] for l in ('en', 'it')},
                      schemas[lang][name]['parameters'], handler(name)) for name in names]
        ref_path = a.reference_dir/targets[case['id']]
        previous = json.loads(ref_path.read_text())
        with Agent(tools) as agent:
            for strategy, arm in [('none', 'nesso_only'), ('rank', 'nev_ranked'), ('select', 'nev_selected')]:
                row = agent.run(case['request'], language=lang, strategy=strategy)
                ref = next(r for r in previous['rows'] if r['arm'] == arm)
                fields = ['status', 'final', 'executed_calls', 'errors']
                row.update(id=case['id'], parity={f: row[f] == ref[f] for f in fields},
                           reference_sha256=hashlib.sha256(ref_path.read_bytes()).hexdigest())
                report['rows'].append(row)
                save()
                print(case['id'], strategy, row['parity'], flush=True)
    report['status'] = ('passed' if len(report['rows']) == 6 and
                        all(all(r['parity'].values()) for r in report['rows']) else 'failed')
    save()
    if report['status'] != 'passed': raise SystemExit('API changed saved launch outputs; inspect report')


if __name__ == '__main__': main()
