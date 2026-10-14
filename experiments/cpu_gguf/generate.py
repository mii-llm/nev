"""Nesso3 alone: CPU text/tool-call generation; no Nev model and no tool execution."""
import argparse
import json
import os
from pathlib import Path
import re
import time

os.environ['USE_TORCH'] = '0'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from transformers import AutoTokenizer
from cpu_backend import ROOT, Worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--precision', choices=['f16', 'q8'], default='f16')
    parser.add_argument('--language', choices=['en', 'it', 'both'], default='both')
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--message', help='Plain user message without tools.')
    inputs.add_argument('--messages', type=Path, help='A JSON array of native chat messages, including any tool schema/results.')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Choose a fresh output path')
    tokenizer = AutoTokenizer.from_pretrained(ROOT/'models/nesso3', local_files_only=True)
    worker = Worker(ROOT/f'gguf/nesso3-{args.precision}.gguf', 'generate', args.threads)
    rows = []
    try:
        languages = ['en', 'it'] if args.language == 'both' else [args.language]
        if args.messages:
            languages = ['custom']
        for lang in languages:
            if args.messages:
                messages = json.loads(args.messages.read_text())
            elif args.message:
                messages = [{'role': 'system', 'content': 'Rispondi brevemente in italiano.' if lang == 'it' else 'Reply briefly in English.'},
                            {'role': 'user', 'content': args.message}]
            else:
                # Same frozen bilingual schemas used by the original conversion checks.
                kit = json.loads((ROOT/'abstract_agent/toolsets.json').read_text())['sensors']
                instruction = 'Sei un assistente operativo. Usa gli strumenti disponibili quando servono.' if lang == 'it' else 'You are an operational assistant. Use the available tools when needed.'
                messages = [{'role': 'system', 'content': instruction+'\n<tools>\n'+json.dumps(kit['schemas'][lang], ensure_ascii=False, separators=(',', ':'))+'\n</tools>'},
                            {'role': 'user', 'content': 'Leggi la temperatura del sensore S-6K3.' if lang == 'it' else 'Read temperature sensor S-6K3.'}]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            ids = tokenizer.encode(prompt, add_special_tokens=True)
            if not ids or ids[0] != tokenizer.bos_token_id or (len(ids) > 1 and ids[1] == tokenizer.bos_token_id):
                raise ValueError('Expected exactly one leading BOS')
            start = time.perf_counter()
            result = worker.request({'ids': ids, 'max_new_tokens': 192})
            text = re.split(r'<\|eot_id\|>|<\|end_of_text\|>', tokenizer.decode(result['ids'], skip_special_tokens=False))[0].strip()
            row = {'language': lang, 'messages': messages, 'text': text, 'truncated': result['truncated'],
                   'elapsed_ms': (time.perf_counter()-start)*1000, 'prompt_tokens': len(ids), 'generated_tokens': len(result['ids'])}
            rows.append(row)
            print(f"[{lang}] {messages[-1]['content']}\n{text}\n", flush=True)
    finally:
        worker.close()
    report = {'model': 'nesso3', 'precision': args.precision, 'cpu_only': True, 'threads': args.threads,
              'nev_loaded': False, 'tools_executed': False, 'rows': rows}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
