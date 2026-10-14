"""Integration check: real CPU inference, bilingual mock tool execution and grounding."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--precision', choices=['f16', 'q8'], default='f16')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.output and args.output.exists():
        p.error('Choose a fresh output path')
    with tempfile.TemporaryDirectory(prefix='nev-cpu-smoke-') as folder:
        trace = Path(folder) / 'trace.json'
        subprocess.run([sys.executable, str(ROOT/'demo.py'), '--precision', args.precision,
                        '--language', 'both', '--output', str(trace)], check=True)
        report = json.loads(trace.read_text())
    expected = {'name': 'read_sensor', 'arguments': {'sensor_id': 'S-6K3'}}
    assert report['cpu_only'] and len(report['rows']) == 2
    for row in report['rows']:
        assert row['status'] == 'answered', row
        assert not row['errors'], row
        assert [entry['call'] for entry in row['executed_calls']] == [expected], row
        assert row['trace'][0]['ranking']['choice'] == 'read_sensor', row
        answer = row['final'].replace(' ', '').replace(',', '.')
        assert '18.2' in answer and ('°C' in answer or 'Celsius' in answer), row
    os.environ['USE_TORCH'] = '0'
    os.environ['HF_HUB_OFFLINE'] = '1'
    from cpu_backend import NevGGUF
    nev = NevGGUF(args.precision)
    try:
        decisions = nev.evaluate(
            'Vorrei un rimborso per un articolo difettoso.',
            {'route': {'type': 'choice', 'instructions': 'Scegli il reparto competente.',
                       'criteria': {'refund': 'Resi e rimborsi', 'account': 'Accesso account',
                                    'info': 'Informazioni generali'}}})
        assert decisions['answers']['route']['choice'] == 'refund', decisions
    finally:
        nev.close()
    result = {'status': 'passed', 'precision': args.precision, 'cpu_only': True,
              'scope': 'Selected bilingual sensor smoke and Italian refund decision; not broad accuracy.',
              'agent': report, 'nev': decisions}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(f'PASS: {args.precision}, EN + IT tool call/answer and standalone Nev refund routing')

if __name__ == '__main__':
    main()
