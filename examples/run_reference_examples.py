"""Run bilingual reference candidates and show a dry-run tool dispatch."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import platform
import time

from huggingface_hub import snapshot_download
from hf_decide import REPO, REVISION
from decision_model import DecisionModel
import torch


def proposed_call(name, context):
    """Arguments are application-supplied, never generated or extracted by Nev."""
    fields = {
        'get_order_status': ('order_id',),
        'get_invoice': ('order_id',),
        'search_help_center': ('help_query',),
        'list_transactions': ('customer_id', 'start_date', 'end_date'),
        'no_tool': (),
    }
    if name not in fields:
        raise ValueError('Unknown function')
    if name == 'no_tool':
        return None
    arguments = {key: context[key] for key in fields[name]}
    if not all(isinstance(value, str) and value.strip() for value in arguments.values()):
        raise ValueError('Missing application argument')
    return {'name': name, 'arguments': arguments, 'executed': False,
            'argument_source': 'synthetic application context; not model output'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', nargs='+', choices=['v2', 'v3'], default=['v3'])
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('reference_candidates.json'))
    parser.add_argument('--domain', choices=['routing', 'function_selection', 'news_topic', 'banking_intent'])
    parser.add_argument('--language', choices=['en', 'it', 'both'], default='both')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output path; existing results are preserved')
    if not args.output.parent.is_dir():
        parser.error('Create the output directory first')
    if not torch.cuda.is_available():
        parser.error('This reference runner requires a CUDA-compatible GPU')
    free, total = torch.cuda.mem_get_info()
    cap = 4 * 1024**3
    if free < cap:
        parser.error('At least 4 GiB of free GPU memory is required')
    torch.cuda.set_per_process_memory_fraction(min(cap / total, 1.0))
    data = json.loads(args.cases.read_text())
    cases = [c for c in data['cases'] if (not args.domain or c['domain'] == args.domain)
             and (args.language == 'both' or c['language'] == args.language)]
    if not cases:
        parser.error('No matching cases')
    report = {'repository': REPO, 'revision': REVISION, 'scope': data['scope'],
              'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'python': platform.python_version(), 'torch': torch.__version__,
              'gpu': torch.cuda.get_device_name(), 'precision': 'FP32 native cached inference',
              'timing_scope': 'Synchronized wall time after one warmup; shared GPU, illustrative only',
              'selection_rule': data['selection_rule'], 'models': {}, 'status': 'incomplete'}
    try:
        for variant in args.variants:
            folder = Path(snapshot_download(REPO, revision=REVISION,
                          allow_patterns=[f'{variant}/**'], local_files_only=True)) / variant
            model = DecisionModel.from_pretrained(folder, device='cuda')
            with torch.inference_mode():
                model.evaluate(**cases[0]['request'])
            rows = []
            for case in cases:
                torch.cuda.synchronize()
                started = time.perf_counter()
                with torch.inference_mode():
                    response = model.evaluate(**case['request'])
                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - started) * 1000
                answer = response['answers']['decision']
                predicted = answer['choice']
                row = {key: case[key] for key in ('id', 'pair', 'domain', 'language', 'expected')}
                row.update(predicted=predicted, correct=predicted == case['expected'],
                           elapsed_ms=elapsed, response=response)
                if case['domain'] == 'function_selection':
                    row['proposed_call'] = proposed_call(predicted, case['application_context'])
                rows.append(row)
                print(f"{variant} {case['id']}: {predicted} "
                      f"p={answer['top_probability']:.3f} expected={case['expected']} "
                      f"{'OK' if row['correct'] else 'FAIL'}", flush=True)
            summary = {}
            for domain in sorted({c['domain'] for c in cases}):
                subset = [r for r in rows if r['domain'] == domain]
                summary[domain] = {
                    lang: {'correct': sum(r['correct'] for r in subset if r['language'] == lang),
                           'n': sum(r['language'] == lang for r in subset)}
                    for lang in ('en', 'it')}
                summary[domain]['successful_bilingual_pairs'] = [
                    pair for pair in sorted({r['pair'] for r in subset})
                    if {r['language'] for r in subset if r['pair'] == pair} == {'en', 'it'}
                    and all(r['correct'] for r in subset if r['pair'] == pair)]
            report['models'][variant] = {'cases': rows, 'summary': summary}
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print('SUMMARY', variant, json.dumps(summary), flush=True)
            del model
            gc.collect()
            torch.cuda.empty_cache()
        report['status'] = 'complete'
    finally:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
