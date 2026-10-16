"""Download the pinned CPU release and verify every selected artifact's SHA-256."""
import argparse
import hashlib
import json
from pathlib import Path
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precision', choices=['f16', 'q8', 'both'], default='f16')
    parser.add_argument('--model', choices=['nev', 'nesso3', 'both'], default='both')
    parser.add_argument('--destination', type=Path, default=ROOT)
    args = parser.parse_args()
    release = json.loads((ROOT / 'release.json').read_text())
    for model_name, model in release['models'].items():
        if args.model != 'both' and args.model != model_name:
            continue
        manifest_path = hf_hub_download(model['repository'], 'ARTIFACTS.json', revision=model['revision'], token=False)
        manifest = json.loads(Path(manifest_path).read_text())
        selected = {name: spec for name, spec in manifest.items()
                    if not name.startswith('gguf/') or args.precision == 'both'
                    or name.endswith(f'-{args.precision}.gguf')}
        for name, spec in selected.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError(f'Invalid artifact path: {name}')
            target = args.destination / relative
            if target.exists():
                if target.stat().st_size != spec['bytes'] or sha256(target) != spec['sha256']:
                    raise ValueError(f'Existing file differs from release; move it aside first: {target}')
                print(f'Verified existing {name}', flush=True)
                continue
            downloaded = Path(hf_hub_download(model['repository'], name, revision=model['revision'], local_dir=args.destination, token=False))
            if downloaded.stat().st_size != spec['bytes'] or sha256(downloaded) != spec['sha256']:
                raise ValueError(f'Integrity check failed: {name}')
            print(f'Downloaded and verified {name}', flush=True)
        print(f"Ready: {model['repository']} @ {model['revision']} ({args.precision})")

if __name__ == '__main__':
    main()
