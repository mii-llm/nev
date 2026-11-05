"""Paired Q8/Q4 CPU pilot: frozen catalogs, all traces and process-tree memory."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import threading
import time


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Memory:
    def __init__(self):
        import psutil
        self.psutil = psutil
        self.parent = psutil.Process()
        self.stop = threading.Event()
        self.phase = 'load'
        self.peaks = {'all': {k: 0 for k in ('rss', 'pss', 'uss')},
                      'inference': {k: 0 for k in ('rss', 'pss', 'uss')}}
        self.samples = self.failures = self.inference_samples = 0
        self.thread = threading.Thread(target=self.loop, daemon=True)
    def loop(self):
        while not self.stop.is_set():
            try:
                processes = [self.parent] + self.parent.children(recursive=True)
                infos = [p.memory_full_info() for p in processes]
                sample = {k: sum(getattr(i, k) for i in infos) for k in ('rss', 'pss', 'uss')}
                self.samples += 1
                for k, value in sample.items():
                    self.peaks['all'][k] = max(self.peaks['all'][k], value)
                    if self.phase == 'inference':
                        self.peaks['inference'][k] = max(self.peaks['inference'][k], value)
                if self.phase == 'inference': self.inference_samples += 1
            except (self.psutil.Error, ProcessLookupError, AttributeError): self.failures += 1
            self.stop.wait(.05)
    def report(self):
        return {'peak_mib': {phase: {k: v/1024**2 for k, v in d.items()} for phase, d in self.peaks.items()},
                'samples': self.samples, 'inference_samples': self.inference_samples,
                'failed_samples': self.failures, 'sampling_interval_seconds': .05,
                'scope': 'Python plus worker children; OS excluded. PSS apportions shared pages; RSS can double count. Sampled peaks, not a device minimum or hard ceiling.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, required=True)
    p.add_argument('--artifacts', type=Path, required=True)
    p.add_argument('--precision', choices=['q4_0_pure'], required=True)
    p.add_argument('--suite', choices=['routing', 'greenhouse'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.txt').exists(): p.error('Use a new output path')
    if platform.system() != 'Linux': p.error('This memory comparison requires Linux PSS/USS')
    os.environ.update(USE_TORCH='0', HF_HUB_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    cpu = a.repo_root.resolve()/'experiments/cpu_gguf'
    source = cpu/('routing_cases.json' if a.suite == 'routing' else 'greenhouse_suite.json')
    data = json.loads(source.read_text())
    kits = json.loads((cpu/'abstract_agent/toolsets.json').read_text()) if a.suite == 'routing' else data['toolsets']
    domains = ['notes', 'sensors', 'media'] if a.suite == 'routing' else list(kits)
    responses = [r for domain in domains for r in kits[domain]['responses']]
    runtime = load(cpu/'abstract_agent/runtime.py', '_q4_controller')
    fixtures = load(cpu/'abstract_agent/fixtures.py', '_q4_fixtures')
    module = load(cpu/'cpu_backend.py', '_q4_backend')
    # Relocate only artifact lookup; renderer, model/head computation and worker are unchanged.
    module.ROOT = a.artifacts.resolve()
    arm = 'nev_selected' if a.suite == 'routing' else 'nev_ranked'
    files = ['cpu_backend.py', 'worker.cpp', 'abstract_agent/runtime.py', 'abstract_agent/fixtures.py', 'release.json']
    report = {'status': 'incomplete', 'suite': a.suite, 'precision': a.precision, 'arm': arm,
              'cpu_only': True, 'threads': 4, 'platform': platform.platform(), 'python': sys.version,
              'release': json.loads((cpu/'release.json').read_text()), 'suite_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256': {f: hashlib.sha256((cpu/f).read_bytes()).hexdigest() for f in files},
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'quantization': json.loads((a.artifacts/'quantization-q4_0_pure.json').read_text()), 'rows': []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save(): a.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    save()
    memory = Memory();memory.thread.start();backend = None
    try:
        start = time.perf_counter();backend = module.Backend(a.precision, 4)
        report['load_seconds'] = time.perf_counter()-start
        backend.generate([{'role': 'system', 'content': 'Reply briefly.'}, {'role': 'user', 'content': 'Hello.'}])
        backend.rank('Hello.', 'en', kits[domains[0]]['schemas']['en'], [], [], False)
        backend.generation_metrics.clear();memory.phase = 'inference'
        for i, case in enumerate(data['cases']):
            schemas = [s for d in domains for s in kits[d]['schemas'][case['language']]]
            random.Random(7100+i//2).shuffle(schemas)
            start = time.perf_counter()
            ranking = backend.rank(case['request'], case['language'], schemas, [], [], False)
            available = sorted(schemas, key=lambda s: -ranking['probabilities'][s['function']['name']])
            if arm == 'nev_selected': available = [s for s in schemas if s['function']['name'] == ranking['choice']]
            row = runtime.GenericAgent(backend).run(case['request'], case['language'], available,
                                                   fixtures.FixtureExecutor(responses), 'nesso_only', 7100+i)
            elapsed = (time.perf_counter()-start)*1000
            actual = [x['call'] for x in row['executed_calls']]
            exact = actual == case['expected_calls']
            anchors = bool(row['final']) and all(any(v.casefold() in row['final'].casefold() for v in group)
                                              for group in case['answer_anchor_groups'])
            row.update(id=case['id'], request=case['request'], language=case['language'], arm=arm,
                       initial_ranking=ranking, total_ms=elapsed, expected_calls=case['expected_calls'],
                       generation_metrics=backend.generation_metrics[:],
                       score={'exact_execution': exact, 'answer_anchor_proxy': exact and anchors and row['status']=='answered',
                              'nev_top_choice': ranking['choice'] == case['expected_calls'][0]['name']})
            report['rows'].append(row);backend.generation_metrics.clear();save()
            print(a.suite, a.precision, case['id'], row['score'], round(elapsed/1000,2), repr(row['final']), flush=True)
        report['status'] = 'complete'
    finally:
        memory.stop.set();memory.thread.join()
        report['memory'] = memory.report()
        if backend is not None: backend.close()
        report['summary'] = {lang: {'n': len(rs), 'exact_execution': sum(r['score']['exact_execution'] for r in rs),
                                   'answer_anchor_proxy': sum(r['score']['answer_anchor_proxy'] for r in rs),
                                   'nev_top_choice': sum(r['score']['nev_top_choice'] for r in rs),
                                   'median_ms': statistics.median(r['total_ms'] for r in rs)}
                             for lang in ('en','it') if (rs := [r for r in report['rows'] if r['language']==lang])}
        save()
        a.output.with_suffix('.txt').write_text('\n\n'.join('Nev initial choice: '+r['initial_ranking']['choice']+'\n'+runtime.render(r)
                                                            for r in report['rows']))


if __name__ == '__main__': main()
