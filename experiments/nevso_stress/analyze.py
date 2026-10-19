"""Summarize frozen runs without treating repeated tool orders as independent cases."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics

ARMS=['nesso_only','nev_ranked','nev_selected']
ROOT=Path(__file__).resolve().parent


def cluster_difference(rows, metric, arm):
    pairs=defaultdict(dict)
    for r in rows:
        if r['score'].get(metric) is not None:
            pairs[(r['pair_id'],r['language'],r['order'])][r['arm']]=r['score'][metric]
    clustered=defaultdict(list)
    for (pair,lang,order),scores in pairs.items():
        if arm in scores and 'nesso_only' in scores:
            clustered[pair].append(int(scores[arm])-int(scores['nesso_only']))
    means=[statistics.mean(v) for v in clustered.values()]
    if not means:return None
    rng=random.Random(20261019)
    samples=sorted(statistics.mean(rng.choices(means,k=len(means))) for _ in range(2000))
    comparisons=[d for values in clustered.values() for d in values]
    return {'mean_delta_pp':100*statistics.mean(means),
            'cluster_bootstrap_95_pp':[100*samples[50],100*samples[1949]],
            'independent_bilingual_pairs':len(means),'trial_wins':sum(d==1 for d in comparisons),
            'trial_losses':sum(d==-1 for d in comparisons),'trial_ties':sum(d==0 for d in comparisons)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    meta=json.loads((a.run/'metadata.json').read_text())
    rows=[json.loads(s) for s in (a.run/'rows.jsonl').read_text().splitlines()]
    suite=json.loads((ROOT/'suite.json').read_text())
    cases={c['id']:c for c in suite['cases']}
    groups=defaultdict(list)
    for r in rows:
        c=cases[r['id']]
        group=r['category']
        if group=='unsupported_or_direct':group=c['expected_behavior']
        if group=='error_or_format':group='tool_error' if c['expected_behavior']=='tool_error' else 'date_format'
        groups[group].append(r)
    out={'status':meta['status'],'trials':len(rows),'expected_trials':meta['expected_trials'],'groups':{},'sensitivity_excluding_flagged':{}}
    lines=['# Nevso bilingual stress test — automatic results','',
           f"Run status: **{meta['status']}**. Recorded **{len(rows)}/{meta['expected_trials']} trials**.",
           '',f"Engine: `{meta['engine']}`; precision: `{meta['precision']}`.",
           '', '**These are automatic scores.** BFCL-derived rows measure schema-valid reference calls; workflow scores are completion proxies, not reviewed factual accuracy. Date-format rows use the strict proxy. Three tool orders repeat each request; trial counts are not independent sample sizes.',
           '', '| Category | Language | Requests | Nesso3 alone | Nev-ranked | Nev-selected |',
           '| --- | --- | ---: | ---: | ---: | ---: |']
    for group,rs in sorted(groups.items()):
        metric='call_correct' if group=='external_single' else ('strict_completion_proxy' if group=='date_format' else 'completion_proxy')
        details={'metric':metric,'languages':{},'paired_difference':{}}
        for lang in ['en','it']:
            cell=[];ld={}
            for arm in ARMS:
                chosen=[r for r in rs if r['language']==lang and r['arm']==arm]
                vals=[r['score'][metric] for r in chosen]
                bycase=defaultdict(list)
                for r in chosen:bycase[r['id']].append(r['score'][metric])
                perorder={str(o):{'correct':sum(r['score'][metric] for r in chosen if r['order']==o),
                                 'n':sum(r['order']==o for r in chosen)} for o in meta['orders']}
                ld[arm]={'correct':sum(vals),'n':len(vals),'requests':len(bycase),
                         'all_orders_correct':sum(len(v)==len(meta['orders']) and all(v) for v in bycase.values()),
                         'per_order':perorder,'median_ms':statistics.median(r['total_ms'] for r in chosen) if chosen else None,
                         'blocked_calls':sum(r['score'].get('blocked_calls',0) for r in chosen)}
                cell.append(f"{sum(vals)}/{len(vals)} ({100*sum(vals)/len(vals):.1f}%)" if vals else '—')
            details['languages'][lang]=ld
            n=len({r['id'] for r in rs if r['language']==lang})
            lines.append(f"| {group} | {lang.upper()} | {n} | "+' | '.join(cell)+' |')
        for arm in ARMS[1:]:details['paired_difference'][arm]=cluster_difference(rs,metric,arm)
        out['groups'][group]=details
    clean=[r for r in rows if r['source']=='bfcl_adapted' and not r.get('quality_flag')]
    for arm in ARMS:
        rs=[r for r in clean if r['arm']==arm]
        out['sensitivity_excluding_flagged'][arm]={'correct':sum(r['score']['call_correct'] for r in rs),'n':len(rs)}
    lines += ['', '## Paired differences versus Nesso3 alone','',
              'Percentage-point differences pool EN/IT and cluster resampling by bilingual pair, retaining all tool orders together. Intervals are descriptive and conditional on this selected sample.',
              '', '| Category | Strategy | Difference | 95% cluster bootstrap interval | Pairs |',
              '| --- | --- | ---: | --- | ---: |']
    for group,d in out['groups'].items():
        for arm,delta in d['paired_difference'].items():
            if delta:
                lo,hi=delta['cluster_bootstrap_95_pp']
                lines.append(f"| {group} | {arm} | {delta['mean_delta_pp']:+.1f} pp | [{lo:+.1f}, {hi:+.1f}] pp | {delta['independent_bilingual_pairs']} |")
    lines += ['', '## Interpretation boundaries','',
              '- The selected arm keeps only its initial tool; dependent cases measure that restriction. Ranking is also performed once, not after every observation.',
              '- BFCL-derived API descriptions stay English in both languages. Italian requests are assistant translations. The 30-pair subset is filtered, and training overlap is unknown.',
              '- Workflow checks use lexical assertions. Correct assertions can coexist with invented statements; valid paraphrases can fail. These scores must not be called hallucination-free or independently reviewed task success.',
              '- No live service runs. Error cases are permanent missing-record responses, and clarification cases stop at the first request for information.',
              '- See analysis.json for tool-order stability, rejected-call counts, median latency, and the sensitivity analysis excluding the contradictory BFCL date prompt.',
              '- Shared A100 timings exclude model loading and cannot be presented as Mac Q8 timings.',
              '', 'The frozen protocol and complete raw/readable traces accompany this report.']
    (a.run/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    (a.run/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines[:20]))

if __name__=='__main__':main()
