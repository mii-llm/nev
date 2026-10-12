"""Summarize the frozen pilot without changing its scoring or filtering failures."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from agent import ARMS


def analyze(report, cases):
    by_id={c['id']:c for c in cases}
    rows=report['rows']
    if report['status']!='complete': raise ValueError('Only summarize the complete pilot')
    if len(rows)!=len(cases)*3: raise ValueError('Incomplete arm coverage')
    assert len({(r['id'],r['arm']) for r in rows})==len(rows)
    analysis={'status':'complete','n_requests':len(cases),'n_pairs':len({c['pair'] for c in cases}),
              'scoring_note':'Strict mechanical checks, not semantic correctness. See README for literal-anchor and keyword limitations.',
              'results':{},'paired_changes':{},'errors':{}}
    for arm in ARMS:
        analysis['results'][arm]={}
        for lang in ['en','it']:
            subset=[r for r in rows if r['arm']==arm and r['language']==lang]
            tool_rows=[r for r in subset if by_id[r['id']]['expected_calls']]
            non_tool=[r for r in subset if not by_id[r['id']]['expected_calls']]
            initial_name=sum(bool(r['emitted_calls']) and r['emitted_calls'][0]['name']==by_id[r['id']]['expected_calls'][0]['name'] for r in tool_rows)
            initial_exact=sum(bool(r['emitted_calls']) and r['emitted_calls'][0]==by_id[r['id']]['expected_calls'][0] for r in tool_rows)
            analysis['results'][arm][lang]={
                'n':len(subset),'tool_requests':len(tool_rows),'non_tool_requests':len(non_tool),
                'first_tool_name_correct':initial_name,'first_call_exact':initial_exact,
                'whole_call_sequence_exact':sum(r['score']['calls_exact'] for r in subset),
                'strict_mechanical_pass':sum(r['score']['strict_mechanical_pass'] for r in subset),
                'tool_request_strict_pass':sum(r['score']['strict_mechanical_pass'] for r in tool_rows),
                'non_tool_request_strict_pass':sum(r['score']['strict_mechanical_pass'] for r in non_tool),
                'all_required_tools_retained':sum(r['score']['required_tools_available'] for r in tool_rows),
                'median_ms':statistics.median(r['total_ms'] for r in subset),
                'mean_ms':statistics.mean(r['total_ms'] for r in subset),
                'mean_generated_tokens':statistics.mean(r['generated_tokens'] for r in subset),
                'truncated_requests':sum(r['truncated'] for r in subset)}
        analysis['errors'][arm]=dict(Counter(error for r in rows if r['arm']==arm for error in r['errors']))
    indexed={(r['id'],r['arm']):r for r in rows}
    for arm in ARMS[1:]:
        analysis['paired_changes'][arm]={}
        for lang in ['en','it']:
            ids=[c['id'] for c in cases if c['language']==lang]
            wins=[];losses=[]
            for cid in ids:
                a=indexed[cid,'nesso_only']['score']['strict_mechanical_pass']
                b=indexed[cid,arm]['score']['strict_mechanical_pass']
                if b and not a:wins.append(cid)
                if a and not b:losses.append(cid)
            analysis['paired_changes'][arm][lang]={'wins':wins,'losses':losses,'net':len(wins)-len(losses)}
    return analysis

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path)
    p.add_argument('--cases',type=Path,default=Path(__file__).with_name('cases.json'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh output file')
    report=json.loads(a.report.read_text())
    assert report['cases_sha256']==hashlib.sha256(a.cases.read_bytes()).hexdigest()
    result=analyze(report,json.loads(a.cases.read_text())['cases'])
    result['report_sha256']=hashlib.sha256(a.report.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
