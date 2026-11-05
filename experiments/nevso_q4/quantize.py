"""Create non-overwriting Q4_K_M files from verified public F16 sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8*1024**2), b''): digest.update(block)
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts', type=Path, required=True)
    p.add_argument('--quantizer', type=Path, required=True)
    a = p.parse_args()
    record = a.artifacts/'quantization.json'
    if record.exists(): p.error('Use a new experiment directory')
    outputs = [a.artifacts/'gguf'/f'{name}-q4_k_m.gguf' for name in ('nev-v3', 'nesso3')]
    if any(o.exists() or o.with_suffix('.partial.gguf').exists() for o in outputs):
        p.error('Quantized output or partial file already exists')
    result = {'status': 'incomplete', 'format': 'Q4_K_M',
              'quantizer_sha256': sha(a.quantizer), 'models': {}}
    record.write_text(json.dumps(result, indent=2)+'\n')
    for name, output in zip(('nev-v3', 'nesso3'), outputs):
        source = a.artifacts/'gguf'/f'{name}-f16.gguf'
        temporary = output.with_suffix('.partial.gguf')
        command = [str(a.quantizer), str(source), str(temporary), 'Q4_K_M', '4']
        with (a.artifacts/f'quantize-{name}.log').open('x') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        temporary.rename(output)
        result['models'][name] = {'source_bytes': source.stat().st_size,
                                 'source_sha256': sha(source), 'output_bytes': output.stat().st_size,
                                 'output_sha256': sha(output), 'command': command}
        record.write_text(json.dumps(result, indent=2)+'\n')
        print(name, result['models'][name], flush=True)
    result['status'] = 'complete'
    record.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__': main()
