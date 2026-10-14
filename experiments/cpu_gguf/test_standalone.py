"""Real CPU inference checks for one model, without loading the other model."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', choices=['nev', 'nesso3'], required=True)
    p.add_argument('--precision', choices=['f16', 'q8'], default='f16')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.output and args.output.exists():
        p.error('Choose a fresh output path')
    if args.model == 'nev':
        os.environ['USE_TORCH'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        from cpu_backend import NevGGUF
        model = NevGGUF(args.precision)
        rows = []
        try:
            for lang, state, instructions, criteria in [
                ('en', 'My parcel arrived broken. I want a refund.', 'Select the appropriate department.',
                 {'refund': 'Damaged goods and refunds', 'account': 'Account access', 'info': 'Product information'}),
                ('it', 'Il pacco è arrivato rotto e voglio un rimborso.', 'Seleziona il tipo di richiesta.',
                 {'refund': 'Rimborso o merce danneggiata', 'account': "Accesso all'account", 'info': 'Informazioni sui prodotti'}),
            ]:
                result = model.evaluate(state, {'route': {'type': 'choice', 'instructions': instructions, 'criteria': criteria}})
                assert result['answers']['route']['choice'] == 'refund', result
                rows.append({'language': lang, 'state': state, 'result': result})
        finally:
            model.close()
        other = ROOT/'models/nesso3'
    else:
        with tempfile.TemporaryDirectory(prefix='nesso3-alone-') as tmp:
            out = Path(tmp)/'generation.json'
            subprocess.run([sys.executable, str(ROOT/'generate.py'), '--precision', args.precision,
                            '--language', 'both', '--output', str(out)], check=True)
            report = json.loads(out.read_text())
        assert not report['nev_loaded'] and not report['tools_executed']
        rows = report['rows']
        assert {r['language'] for r in rows} == {'en', 'it'}
        for row in rows:
            match = re.fullmatch(r'\s*<tool_call>\s*(.*?)\s*</tool_call>\s*', row['text'], flags=re.DOTALL)
            assert match and not row['truncated'], row
            assert json.loads(match.group(1)) == {'name': 'read_sensor', 'arguments': {'sensor_id': 'S-6K3'}}, row
        other = ROOT/'models/nev'
    result = {'status': 'passed', 'model': args.model, 'precision': args.precision, 'cpu_only': True,
              'other_model_artifacts_present': other.exists(),
              'scope': 'Selected bilingual standalone smoke checks, not broad quality evaluation.', 'rows': rows}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(f'PASS: standalone {args.model}, {args.precision}, English and Italian')


if __name__ == '__main__':
    main()
