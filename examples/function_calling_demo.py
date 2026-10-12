"""Select a function with Nev and display an application-built call without executing it."""
import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download
import torch
from decision_model import DecisionModel
from hf_decide import REPO, REVISION
from run_reference_examples import proposed_call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['v2', 'v3'], default='v3')
    parser.add_argument('--language', choices=['en', 'it', 'both'], default='both')
    parser.add_argument('--example', choices=['order', 'document', 'guide', 'payments'], default='document')
    args = parser.parse_args()
    if not torch.cuda.is_available():
        parser.error('This A100 demonstration requires a CUDA-compatible GPU')
    free, total = torch.cuda.mem_get_info()
    cap = 4 * 1024**3
    if free < cap:
        parser.error('At least 4 GiB of free GPU memory is required')
    torch.cuda.set_per_process_memory_fraction(min(cap / total, 1.0))
    cases = json.loads(Path(__file__).with_name('reference_candidates.json').read_text())['cases']
    cases = [c for c in cases if c['pair'] == f'function_selection/{args.example}'
             and (args.language == 'both' or c['language'] == args.language)]
    folder = Path(snapshot_download(REPO, revision=REVISION,
                  allow_patterns=[f'{args.variant}/**'], local_files_only=True)) / args.variant
    model = DecisionModel.from_pretrained(folder, device='cuda')
    results = []
    for case in cases:
        with torch.inference_mode():
            response = model.evaluate(**case['request'])
        answer = response['answers']['decision']
        results.append({
            'language': case['language'], 'input': case['request']['state'],
            'model_selected_function': answer['choice'],
            'probabilities': answer['probabilities'],
            'expected_function': case['expected'],
            'correct': answer['choice'] == case['expected'],
            'application_built_call': proposed_call(answer['choice'], case['application_context']),
        })
    print(json.dumps({'repository': REPO, 'revision': REVISION, 'variant': args.variant,
                     'scope': 'Function-name selection only. Arguments come from the application; no tool is executed.',
                     'results': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
