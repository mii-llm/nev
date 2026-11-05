"""Summarize paired precision trials without treating answer proxies as truth."""
import argparse
import json
from pathlib import Path
import statistics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('results', type=Path)
    a = p.parse_args()
    runs = {(suite, precision): json.loads((a.results/f'{suite}-{precision}.json').read_text())
            for suite in ('routing', 'greenhouse') for precision in ('q8', 'q4_k_m', 'q4_0', 'q4_0_pure')}
    for run in runs.values():
        assert run['status'] == 'complete' and len(run['rows']) == 24
        assert run['memory']['inference_samples'] > 0
    summary = {'scope': '48 reused authored requests, 24 EN + 24 IT, each at Q8, Q4_K_M, Q4_0 and pure Q4_0; 192 trials.',
               'runs': {}, 'paired': {}}
    lines = ['# Nevso Q4 versus Q8 — automatic results', '', summary['scope'], '',
             'Selection for routing; ranking for greenhouse, fixed before evaluation. CPU only, four threads.',
             'Answer-anchor checks are automatic proxies; review final answers separately. Shared-host timings are illustrative.', '',
             '| Suite | Precision | Language | Correct calls | Answer proxy | Nev top choice |',
             '| --- | --- | --- | ---: | ---: | ---: |']
    for (suite, precision), run in runs.items():
        summary['runs'][suite+'-'+precision] = {'by_language': run['summary'], 'memory': run['memory'],
                                               'median_ms': statistics.median(r['total_ms'] for r in run['rows'])}
        for lang, s in run['summary'].items():
            lines.append(f"| {suite} | {precision} | {lang} | {s['exact_execution']}/{s['n']} | "
                         f"{s['answer_anchor_proxy']}/{s['n']} | {s['nev_top_choice']}/{s['n']} |")
    lines += ['', '| Suite | Precision | Warm median | Peak summed RSS | Peak PSS | Peak USS |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    for key, s in summary['runs'].items():
        suite, precision = key.split('-', 1);m = s['memory']['peak_mib']['all']
        lines.append(f"| {suite} | {precision} | {s['median_ms']/1000:.2f} s | {m['rss']:.0f} MiB | {m['pss']:.0f} MiB | {m['uss']:.0f} MiB |")
    lines += ['', 'Memory peaks include loading/warmup and the Python/worker process tree, not the OS. '
              'PSS apportions shared pages; USS excludes them; RSS can double count. '
              'These are sampled observations, not device RAM minima or hard caps.', '', '## Paired changes', '']
    review = ['# All answers for precision review', '']
    for suite in ('routing', 'greenhouse'):
        q8 = runs[(suite, 'q8')]
        for precision in ('q4_k_m', 'q4_0', 'q4_0_pure'):
            candidate = runs[(suite, precision)]
            assert q8['suite_sha256'] == candidate['suite_sha256'] and q8['source_sha256'] == candidate['source_sha256']
            assert [r['id'] for r in q8['rows']] == [r['id'] for r in candidate['rows']]
            diffs = [];agree = 0
            for old, new in zip(q8['rows'], candidate['rows']):
                agree += old['initial_ranking']['choice'] == new['initial_ranking']['choice']
                diff = {'id': old['id'], 'language': old['language'],
                        'q8': {k: old[k] for k in ('score','final','status')},
                        precision: {k: new[k] for k in ('score','final','status')}}
                if old['score'] != new['score']: diffs.append(diff)
            summary['paired'][suite+'-'+precision] = {'nev_choice_agreement': agree, 'n': 24, 'score_changes': diffs}
            lines.append(f'- {suite} / {precision}: Nev top-choice agreement {agree}/24; {len(diffs)} cases change at least one automatic metric.')
        for i, old in enumerate(q8['rows']):
            review += [f"## {suite} / {old['id']}", '', old['request'], '',
                       'Expected calls: '+json.dumps(old['expected_calls'], ensure_ascii=False)]
            for precision in ('q8', 'q4_k_m', 'q4_0', 'q4_0_pure'):
                row = runs[(suite,precision)]['rows'][i]
                observations = [o for event in row['trace'] for o in event['observations']]
                review += ['', f"{precision}: {row['status']}; {row['score']}",
                           'Nev: '+row['initial_ranking']['choice'],
                           'Executed: '+json.dumps(row['executed_calls'], ensure_ascii=False),
                           'Observations: '+json.dumps(observations, ensure_ascii=False), 'Answer: '+row['final']]
    (a.results/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    (a.results/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    (a.results/'REVIEW_INPUT.md').write_text('\n'.join(line.rstrip() for line in review)+'\n')


if __name__ == '__main__': main()
