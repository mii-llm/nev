"""Measure synchronized native inference; reports startup separately and records GPU sharing."""
import argparse
from contextlib import nullcontext
import gc
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import threading
import time

from huggingface_hub import snapshot_download
from hf_decide import REPO, REVISION
import torch
from decision_model import DecisionModel


def gpu_snapshot():
    try:
        data = subprocess.check_output([
            'nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu,clocks.sm',
            '--format=csv,noheader,nounits'], text=True, timeout=5).strip()
        processes = subprocess.check_output([
            'nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
            text=True, timeout=5).strip().splitlines()
        return {'time': time.time(), 'gpu_csv': data,
                'other_compute_processes': sum(x.strip().isdigit() and int(x.strip()) != os.getpid() for x in processes)}
    except (OSError, subprocess.SubprocessError) as e:
        return {'time': time.time(), 'telemetry_error': type(e).__name__}


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def choices(result):
    out = {}
    for key, answer in result['answers'].items():
        out[key] = (answer['choice'] if answer['type'] == 'choice' else
                    str(answer['decision']).lower() if answer['type'] == 'noul' else str(answer['level']))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variants', nargs='+', choices=['v2', 'v3'], default=['v3'])
    p.add_argument('--precisions', nargs='+', choices=['fp32', 'bf16'], default=['fp32', 'bf16'])
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--memory-cap-gib', type=float, default=6)
    a = p.parse_args()
    if a.repeats < 1 or a.memory_cap_gib <= 0:
        p.error('repeats and memory cap must be positive')
    if a.output.exists():
        p.error('Choose a fresh output filename')
    if not torch.cuda.is_available():
        p.error('This timing script requires a CUDA-compatible GPU')
    if 'bf16' in a.precisions and not torch.cuda.is_bf16_supported():
        p.error('This GPU does not support BF16')
    free, total = torch.cuda.mem_get_info()
    cap = int(a.memory_cap_gib * 1024**3)
    if free < cap:
        p.error('Less free GPU memory than the requested cap; retry when more is available')
    torch.cuda.set_per_process_memory_fraction(min(cap / total, 1.0))
    path = Path(__file__).with_name('scenarios.json')
    cases = json.loads(path.read_text())['cases']
    report = {'repository': REPO, 'revision': REVISION,
        'scope': 'Sequential batch=1 cached API, validation/tokenization and GPU synchronization included; no HTTP or download time',
        'cases_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'torch': torch.__version__, 'cuda': torch.version.cuda,
        'gpu': torch.cuda.get_device_name(0), 'repeats': a.repeats,
        'parameter_dtype': 'float32', 'memory_cap_gib': a.memory_cap_gib,
        'allow_tf32': torch.backends.cuda.matmul.allow_tf32,
        'float32_matmul_precision': torch.get_float32_matmul_precision(),
        'cpu_threads': torch.get_num_threads(), 'models': {}}
    telemetry = [gpu_snapshot()]
    stop = threading.Event()

    def monitor():
        while not stop.wait(1):
            telemetry.append(gpu_snapshot())

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        for variant in a.variants:
            folder = Path(snapshot_download(REPO, revision=REVISION,
                allow_patterns=[f'{variant}/**'], local_files_only=True)) / variant
            torch.cuda.synchronize()
            started = time.perf_counter()
            model = DecisionModel.from_pretrained(folder, device='cuda')
            torch.cuda.synchronize()
            model_report = {'load_seconds': time.perf_counter() - started, 'measurements': {}}
            report['models'][variant] = model_report
            reference = {}
            for precision in a.precisions:
                def call(request):
                    # Autocast leaves FP32 weights and rotary buffers unchanged.
                    ctx = torch.autocast('cuda', dtype=torch.bfloat16) if precision == 'bf16' else nullcontext()
                    torch.cuda.synchronize()
                    begin = time.perf_counter()
                    with torch.inference_mode(), ctx:
                        result = model.evaluate(**request)
                    torch.cuda.synchronize()
                    return result, (time.perf_counter() - begin) * 1000

                _, first_ms = call(cases[0]['request'])
                for case in cases[:2]:
                    call(case['request'])
                measured = {'first_request_ms': first_ms, 'workloads': {}}
                for workload in ['one_question', 'four_questions']:
                    torch.cuda.reset_peak_memory_stats()
                    rows = []
                    for repeat in range(a.repeats):
                        for case in cases:
                            request = case['request']
                            if workload == 'one_question':
                                request = {**request, 'questions': {'route': request['questions']['route']}}
                            response, milliseconds = call(request)
                            prediction = choices(response)
                            identity = (workload, case['id'], repeat)
                            changed = None
                            if precision == 'fp32':
                                reference[identity] = prediction
                            elif identity in reference:
                                changed = sum(prediction[q] != reference[identity][q] for q in prediction)
                            rows.append({'case': case['id'], 'language': case['language'], 'repeat': repeat,
                                'elapsed_ms': milliseconds, 'usage': response['usage'], 'predicted': prediction,
                                'correct': sum(prediction[q] == case['expected'][q] for q in prediction),
                                'changed_vs_fp32': changed})
                    milliseconds = [r['elapsed_ms'] for r in rows]
                    count = sum(r['usage']['questions'] for r in rows)
                    summary = {'requests': len(rows), 'decisions': count,
                        'p50_ms': statistics.median(milliseconds), 'p95_ms': percentile(milliseconds, .95),
                        'mean_ms': statistics.mean(milliseconds), 'requests_per_second': 1000 / statistics.mean(milliseconds),
                        'decisions_per_second': count * 1000 / sum(milliseconds),
                        'correct_decisions': sum(r['correct'] for r in rows),
                        'changed_decisions_vs_fp32': sum(r['changed_vs_fp32'] for r in rows) if all(r['changed_vs_fp32'] is not None for r in rows) else None,
                        'peak_allocated_mib': torch.cuda.max_memory_allocated() / 1024**2,
                        'peak_reserved_mib': torch.cuda.max_memory_reserved() / 1024**2}
                    measured['workloads'][workload] = {'summary': summary, 'samples': rows}
                    print(variant, precision, workload, json.dumps(summary), flush=True)
                model_report['measurements'][precision] = measured
                report['gpu_telemetry'] = list(telemetry)
                a.output.write_text(json.dumps(report, indent=2) + '\n')
            del model
            gc.collect()
            torch.cuda.empty_cache()
    finally:
        stop.set()
        thread.join(timeout=12)
        telemetry.append(gpu_snapshot())
        report['gpu_telemetry'] = telemetry
        report['status'] = 'complete' if len(report['models']) == len(a.variants) and all(len(x['measurements']) == len(a.precisions) for x in report['models'].values()) else 'incomplete'
        a.output.write_text(json.dumps(report, indent=2) + '\n')
    print('RESULTS', a.output, flush=True)


if __name__ == '__main__':
    main()
