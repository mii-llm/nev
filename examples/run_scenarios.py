"""Show successes AND failures on authored EN/IT one-fact contrast pairs."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import time

from huggingface_hub import snapshot_download
from hf_decide import REPO, REVISION
from decision_model import DecisionModel
import torch


def prediction(answer):
    if answer['type'] == 'choice':
        return answer['choice']
    if answer['type'] == 'noul':
        return str(answer['decision']).lower()
    return str(answer['level'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variants', nargs='+', choices=['v2', 'v3'], default=['v2', 'v3'])
    p.add_argument('--cases', type=Path, default=Path(__file__).with_name('scenarios.json'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--device', default='cuda')
    a = p.parse_args()
    if a.output.exists():
        p.error('Choose a new output filename; existing results are preserved')
    cases = json.loads(a.cases.read_text())['cases']
    report = {'repository': REPO, 'revision': REVISION,
              'cases_sha256': hashlib.sha256(a.cases.read_bytes()).hexdigest(),
              'scope': '20 authored diagnostic requests, 80 decisions/model; not a representative benchmark',
              'models': {}}
    for variant in a.variants:
        folder = Path(snapshot_download(REPO, revision=REVISION,
            allow_patterns=[f'{variant}/**'], local_files_only=True)) / variant
        model = DecisionModel.from_pretrained(folder, device=a.device)
        warm_start = time.perf_counter()
        model.evaluate(**cases[0]['request'])
        warm_seconds = time.perf_counter() - warm_start
        outputs = []
        for case in cases:
            response = model.evaluate(**case['request'])
            pred = {q: prediction(answer) for q, answer in response['answers'].items()}
            correct = {q: pred[q] == gold for q, gold in case['expected'].items()}
            outputs.append({**{k: case[k] for k in ('id', 'pair', 'side', 'language', 'expected')},
                            'predicted': pred, 'correct': correct, 'response': response})
            detail = []
            for q, gold in case['expected'].items():
                probability = response['answers'][q]['probabilities'][pred[q]]
                status = 'OK' if correct[q] else f'WRONG expected={gold}'
                detail.append(f'{q}={pred[q]} p={probability:.3f} {status}')
            print(f"{variant} {case['id']}: " + ' | '.join(detail), flush=True)
        summary = {}
        for lang in ('en', 'it'):
            rows = [r for r in outputs if r['language'] == lang]
            tasks = {q: {'correct': sum(r['correct'][q] for r in rows), 'n': len(rows)}
                     for q in rows[0]['expected']}
            changes_correct = changes_n = pairs_correct = 0
            for pair in sorted({r['pair'] for r in rows}):
                before, after = sorted([r for r in rows if r['pair'] == pair], key=lambda r: r['side'])
                pairs_correct += all(before['correct'].values()) and all(after['correct'].values())
                for q in before['expected']:
                    if before['expected'][q] != after['expected'][q]:
                        changes_n += 1
                        changes_correct += before['correct'][q] and after['correct'][q]
            summary[lang] = {'by_task': tasks,
                'all_four_correct': {'correct': sum(all(r['correct'].values()) for r in rows), 'n': len(rows)},
                'changed_decisions_both_sides_correct': {'correct': changes_correct, 'n': changes_n},
                'whole_pairs_correct': {'correct': pairs_correct, 'n': len(rows)//2}}
        report['models'][variant] = {'warmup_seconds': warm_seconds, 'summary': summary, 'cases': outputs}
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print('SUMMARY '+variant+' '+json.dumps(summary), flush=True)
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    print('RESULTS '+str(a.output), flush=True)


if __name__ == '__main__':
    main()
