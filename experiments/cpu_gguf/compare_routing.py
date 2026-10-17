"""Compare Nesso3 with all tools, Nev ordering, and a Nev-selected single tool on CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import time

ARMS = ['nesso_only', 'nev_ranked', 'nev_selected']


def score(case, row):
    calls = [item['call'] for item in row['executed_calls']]
    exact = calls == case['expected_calls']
    final = row['final'].casefold()
    anchors = bool(final) and all(any(a.casefold() in final for a in group)
                                for group in case['answer_anchor_groups'])
    return {'exact_execution': exact,
            'answer_anchor_proxy': exact and anchors and row['status'] == 'answered'}


def summarize(rows):
    return {arm: {lang: {
        'n': len(selected),
        'exact_execution': sum(r['score']['exact_execution'] for r in selected),
        'answer_anchor_proxy': sum(r['score']['answer_anchor_proxy'] for r in selected),
        'median_ms': statistics.median(r['total_ms'] for r in selected),
        'mean_prompt_tokens': statistics.mean(r['prompt_tokens'] for r in selected),
    } for lang in ['en', 'it']
       if (selected := [r for r in rows if r['arm'] == arm and r['language'] == lang])}
       for arm in ARMS}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--precision', choices=['q8', 'f16'], default='q8')
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('--suite', type=Path, help='JSON with cases and toolsets; defaults to the original notes/sensors/music suite')
    p.add_argument('--language', choices=['en', 'it', 'both'], default='both')
    p.add_argument('--case', help='Optional case ID, e.g. playlist_duration-it')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.txt').exists():
        p.error('Choose a new output filename; existing results are preserved')
    os.environ['USE_TORCH'] = '0'
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    from cpu_backend import Backend, ROOT
    from abstract_agent.runtime import GenericAgent, render
    from abstract_agent.fixtures import FixtureExecutor
    cases_path = a.suite.resolve() if a.suite else ROOT/'routing_cases.json'
    data = json.loads(cases_path.read_text())
    cases = [(i, c) for i, c in enumerate(data['cases']) if (a.language == 'both' or c['language'] == a.language)
             and (not a.case or c['id'] == a.case)]
    if not cases:
        p.error('No matching cases')
    kits = data['toolsets'] if a.suite else json.loads((ROOT/'abstract_agent/toolsets.json').read_text())
    domains = list(kits) if a.suite else ['notes', 'sensors', 'media']
    if not domains:
        p.error('Suite must contain at least one toolset')
    for lang in ['en', 'it']:
        names = [s['function']['name'] for domain in domains for s in kits[domain]['schemas'][lang]]
        if len(names) != len(set(names)) or not names:
            p.error('Suite needs unique tool names for each language')
    responses = [r for name in domains for r in kits[name]['responses']]
    report = {'status': 'incomplete', 'scope': data['scope'], 'precision': a.precision,
              'threads': a.threads, 'cpu_only': True,
              'method': 'Same tool registry, requests, generator, validation, mocks and turn limits. Nev ranks once before generation; selected arm exposes only its top tool for this supported single-tool task. Rotated arm order; fixed seeded registry order. No answer keys passed to either model. Both models resident in every arm. Timings include Nev but exclude loading and warmup. Answer anchors are a proxy requiring manual review.',
              'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                for name in ['compare_routing.py', 'cpu_backend.py',
                                             'abstract_agent/runtime.py', 'release.json']
                                + ([] if a.suite else ['routing_cases.json', 'abstract_agent/toolsets.json'])},
              'release': json.loads((ROOT/'release.json').read_text()),
              'runner_source': Path(__file__).read_text(),
              'suite': data if a.suite else None,
              'suite_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(), 'rows': []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        report['summary'] = summarize(report['rows'])
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    started = time.perf_counter()
    backend = Backend(a.precision, a.threads)
    report['load_seconds'] = time.perf_counter()-started
    try:
        backend.generate([{'role': 'system', 'content': 'Reply briefly.'},
                          {'role': 'user', 'content': 'Hello.'}])
        backend.rank('Hello.', 'en', kits[domains[0]]['schemas']['en'], [], [], False)
        for i, case in cases:
            schemas = [s for name in domains for s in kits[name]['schemas'][case['language']]]
            random.Random(7100+i//2).shuffle(schemas)
            for arm in ARMS[i%3:]+ARMS[:i%3]:
                start = time.perf_counter()
                ranking = None
                available = schemas
                if arm != 'nesso_only':
                    ranking = backend.rank(case['request'], case['language'], schemas, [], [], False)
                    available = sorted(schemas, key=lambda s: -ranking['probabilities'][s['function']['name']])
                    if arm == 'nev_selected':
                        available = [next(s for s in schemas if s['function']['name'] == ranking['choice'])]
                metric_start = len(backend.generation_metrics)
                row = GenericAgent(backend).run(case['request'], case['language'], available,
                                               FixtureExecutor(responses), 'nesso_only', 7100+i)
                row.update(id=case['id'], language=case['language'], request=case['request'], arm=arm,
                           total_ms=(time.perf_counter()-start)*1000, initial_ranking=ranking,
                           expected_calls=case['expected_calls'],
                           prompt_tokens=sum(m['prompt_tokens'] for m in backend.generation_metrics[metric_start:]))
                row['score'] = score(case, row)
                report['rows'].append(row)
                save()
                print(f"{case['id']} {arm}: {row['score']} {row['total_ms']/1000:.2f}s", flush=True)
        report['status'] = 'complete'
    finally:
        backend.close()
        save()
        a.output.with_suffix('.txt').write_text('\n\n' + ('\n\n'+'='*70+'\n\n').join(
            f"{r['id']} | score: {r['score']}\nNev initial choice: "
            + (r['initial_ranking']['choice'] if r['initial_ranking'] else 'not used')
            + '\nExpected call: '+json.dumps(r['expected_calls'], ensure_ascii=False)+'\n'+render(r)
            for r in report['rows']), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    print(f'Results: {a.output}\nReadable traces: {a.output.with_suffix(".txt")}')


if __name__ == '__main__':
    main()
