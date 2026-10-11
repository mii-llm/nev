"""Download the pinned private Nev release and run typed decisions with its runtime."""
import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download

REPO = 'giux78/nev'
REVISION = 'c5c84121263b423f8846811a24790ab96e66cee3'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', choices=['v2', 'v3'], default='v3')
    p.add_argument('--language', choices=['en', 'it', 'both'], default='it')
    inputs = p.add_mutually_exclusive_group()
    inputs.add_argument('--state', help='Your text, using the example shipping/billing/account options')
    inputs.add_argument('--request', type=Path, help='JSON object with state and questions, including your own options')
    p.add_argument('--download-only', action='store_true')
    p.add_argument('--offline', action='store_true')
    p.add_argument('--device', default=None)
    a = p.parse_args()
    # The existing LUMI login is in the default token location, while HF_HOME
    # deliberately points to scratch. Never print or copy the token.
    token = None
    if not a.offline:
        import os
        token = os.environ.get('HF_TOKEN')
        default_token = Path.home() / '.cache/huggingface/token'
        if not token and default_token.exists():
            token = default_token.read_text().strip()
    folder = Path(snapshot_download(REPO, revision=REVISION,
        allow_patterns=[f'{a.variant}/**'], local_files_only=a.offline, token=token)) / a.variant
    if a.download_only:
        print(json.dumps({'repository': REPO, 'revision': REVISION, 'variant': a.variant, 'folder': str(folder)}))
        return
    from decision_model import DecisionModel
    model = DecisionModel.from_pretrained(folder, device=a.device)
    results = {}
    if a.request:
        request = json.loads(a.request.read_text())
        if set(request) != {'state', 'questions'}:
            p.error('--request must contain exactly state and questions')
        results['custom'] = model.evaluate(**request)
    else:
        for language in (['en', 'it'] if a.language == 'both' else [a.language]):
            it = language == 'it'
            results[language] = model.evaluate(
                state=a.state if a.state is not None else ('Il pacco non è arrivato. Vorrei sapere dove si trova.' if it else 'My parcel has not arrived. I want to know where it is.'),
                questions={'route': {'type': 'choice',
                    'instructions': 'Scegli il reparto che deve gestire la richiesta.' if it else 'Choose the department that should handle this request.',
                    'criteria': {'shipping': 'Spedizioni e consegne' if it else 'Shipping and delivery',
                                 'billing': 'Pagamenti e fatture' if it else 'Payments and invoices',
                                 'account': 'Accesso e profilo' if it else 'Login and profile'}}})
    print(json.dumps({'repository': REPO, 'revision': REVISION, 'variant': a.variant,
                      'results': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
