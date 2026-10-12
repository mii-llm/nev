"""A bounded two-model agent with synthetic, read-only local tools only."""
import json
import re
from pathlib import Path
import time

GENERATOR_REPO = 'giux78/nesso2-0.4B-agentic-v2'
GENERATOR_REVISION = 'dc74c2f5ec3330d3e22d697078646b547669da1a'
NEV_REPO = 'giux78/nev'
NEV_REVISION = 'c5c84121263b423f8846811a24790ab96e66cee3'
ARMS = ['nesso_only', 'nev_ranked', 'nev_top2']

TOOL_DATA = {
    'get_order_status': ('order_id', r'ORD-\d{4}',
        'Look up shipment status and tracking reference for an order.',
        'Consulta lo stato della spedizione e il riferimento di tracciamento di un ordine.'),
    'get_invoice': ('order_id', r'ORD-\d{4}',
        'Retrieve the invoice document and filename for an order.',
        'Recupera il documento della fattura e il nome del file di un ordine.'),
    'search_help_center': ('product', r'[A-Z]{2}-\d',
        'Find the documentation and guide reference for a product model.',
        'Trova la documentazione e il riferimento della guida di un modello di prodotto.'),
    'list_transactions': ('month', r'2026-(?:0[1-9]|1[0-2])',
        'List recorded payments and their total for a month in YYYY-MM format.',
        'Elenca i pagamenti registrati e il totale di un mese nel formato AAAA-MM.'),
}


def schemas(language, style='validated'):
    if style not in ('validated', 'compact'):
        raise ValueError('Unknown schema style')
    result = [{'type': 'function', 'function': {
        'name': name, 'description': row[3 if language == 'it' else 2],
        'parameters': {'type': 'object', 'properties': {
            row[0]: {'type': 'string', 'pattern': row[1]}},
            'required': [row[0]], 'additionalProperties': False}}}
        for name, row in TOOL_DATA.items()]
    if style == 'compact':
        for tool in result:
            parameters = tool['function']['parameters']
            parameters.pop('additionalProperties')
            for spec in parameters['properties'].values():
                spec.pop('pattern')
    return result


def parse_calls(text):
    """Reject malformed or mixed call markup rather than silently executing it."""
    if '<tool_call' not in text and '</tool_call>' not in text:
        return [], None
    matches = list(re.finditer(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.S))
    remainder = re.sub(r'<tool_call>\s*.*?\s*</tool_call>', '', text, flags=re.S).strip()
    if not matches or remainder:
        return [], 'malformed_or_mixed_tool_markup'
    try:
        calls = [json.loads(m.group(1)) for m in matches]
    except json.JSONDecodeError:
        return [], 'invalid_json'
    if any(not isinstance(c, dict) or set(c) != {'name', 'arguments'} for c in calls):
        return [], 'invalid_call_shape'
    return calls, None


def validate_call(call, allowed_names, user_text):
    name = call.get('name')
    if not isinstance(name, str) or name not in allowed_names or name not in TOOL_DATA:
        return 'function_not_available'
    key, pattern, _, _ = TOOL_DATA[name]
    args = call.get('arguments')
    if not isinstance(args, dict) or set(args) != {key}:
        return 'wrong_arguments'
    value = args[key]
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        return 'invalid_argument_value'
    # This pilot supports only explicitly supplied identifiers/months.
    # It does not pretend to resolve arbitrary natural-language references.
    grounded_values = re.findall(r'(?<![A-Za-z0-9-])(?:' + pattern + r')(?![A-Za-z0-9-])', user_text)
    if value not in grounded_values:
        return 'argument_not_grounded_in_request'
    return None


def mock_tool(call):
    """No network access, files, real accounts, or external side effects."""
    name, args = call['name'], call['arguments']
    if name == 'get_order_status':
        return {'order_id': args['order_id'], 'status': 'in_transit',
                'tracking_reference': 'TRK-' + args['order_id']}
    if name == 'get_invoice':
        return {'order_id': args['order_id'], 'filename': 'invoice_' + args['order_id'] + '.pdf'}
    if name == 'search_help_center':
        return {'product': args['product'], 'guide_reference': 'GUIDE-' + args['product']}
    if name == 'list_transactions':
        return {'month': args['month'], 'currency': 'EUR', 'payments': [24.50, 39.25], 'total': 63.75}
    raise ValueError('Unknown mock tool')


class HybridAgent:
    def __init__(self, memory_cap_gib=8, schema_style='validated'):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from huggingface_hub import snapshot_download
        from decision_model import DecisionModel
        self.torch = torch
        self.schema_style = schema_style
        if not torch.cuda.is_available():
            raise RuntimeError('The A100 pilot requires CUDA')
        free, total = torch.cuda.mem_get_info()
        cap = int(memory_cap_gib * 1024**3)
        if free < cap:
            raise RuntimeError(f'Need {memory_cap_gib} GiB free GPU memory')
        torch.cuda.set_per_process_memory_fraction(min(cap / total, 1.0))
        generator_path = snapshot_download(GENERATOR_REPO, revision=GENERATOR_REVISION,
            allow_patterns=['*.json', '*.safetensors', '*.jinja', 'tokenizer.model'], local_files_only=True)
        nev_path = Path(snapshot_download(NEV_REPO, revision=NEV_REVISION,
                            allow_patterns=['v3/**'], local_files_only=True)) / 'v3'
        self.tokenizer = AutoTokenizer.from_pretrained(generator_path, local_files_only=True)
        if not self.tokenizer.chat_template:
            raise RuntimeError('Missing native saved chat template; do not substitute a new format')
        self.generator = AutoModelForCausalLM.from_pretrained(generator_path,
            dtype=torch.bfloat16, attn_implementation='sdpa', local_files_only=True).to('cuda').eval()
        self.nev = DecisionModel.from_pretrained(nev_path, device='cuda')

    def rank(self, message, language):
        criteria = {name: row[3 if language == 'it' else 2] for name, row in TOOL_DATA.items()}
        self.torch.cuda.synchronize()
        start = time.perf_counter()
        with self.torch.inference_mode():
            result = self.nev.evaluate(state=message, questions={'tool': {
                'type': 'choice', 'instructions': ('Seleziona la funzione più pertinente alla richiesta.'
                    if language == 'it' else 'Select the function most relevant to the request.'),
                'criteria': criteria}})
        self.torch.cuda.synchronize()
        probabilities = result['answers']['tool']['probabilities']
        return {'names': sorted(criteria, key=lambda k: -probabilities[k]),
                'probabilities': probabilities, 'elapsed_ms': (time.perf_counter()-start)*1000}

    def generate(self, messages):
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors='pt', add_special_tokens=True).to('cuda')
        ids = inputs['input_ids'][0]
        if ids[0].item() != self.tokenizer.bos_token_id or (len(ids)>1 and ids[1].item()==self.tokenizer.bos_token_id):
            raise RuntimeError('Expected exactly one initial BOS token with native contract')
        with self.torch.inference_mode():
            output = self.generator.generate(**inputs, max_new_tokens=192, do_sample=False,
                repetition_penalty=1.0, no_repeat_ngram_size=0,
                eos_token_id=self.tokenizer.eos_token_id, pad_token_id=self.tokenizer.pad_token_id)
        generated = output[0, ids.shape[0]:]
        text = self.tokenizer.decode(generated, skip_special_tokens=False)
        text = re.split(r'<\|eot_id\|>|<\|end_of_text\|>', text)[0].strip()
        return text, len(generated), len(generated)==192

    def run(self, message, language, arm, ranking=None):
        if arm not in ARMS:
            raise ValueError('Unknown arm')
        if arm != 'nesso_only' and ranking is None:
            ranking = self.rank(message, language)
        full = {s['function']['name']: s for s in schemas(language, self.schema_style)}
        names = list(full) if arm == 'nesso_only' else ranking['names'][:2] if arm == 'nev_top2' else ranking['names']
        tools = [full[name] for name in names]
        context = ('Sei un assistente operativo. Usa gli strumenti disponibili quando serve.' if language=='it'
                   else 'You are an operational assistant. Use the available tools when needed.')
        system = context + '\n<tools>\n' + json.dumps(tools, ensure_ascii=False, separators=(',', ':')) + '\n</tools>'
        messages = [{'role':'system','content':system},{'role':'user','content':message}]
        trace, emitted, executed, errors = [], [], [], []
        final = ''; total_tokens=0; truncated=False
        self.torch.cuda.synchronize(); start=time.perf_counter()
        for turn in range(4):
            text, tokens, hit_limit = self.generate(messages)
            total_tokens += tokens; truncated |= hit_limit
            calls, parse_error = parse_calls(text)
            event={'turn':turn,'assistant':text,'generated_tokens':tokens,'calls':calls,'parse_error':parse_error,'observations':[]}
            trace.append(event)
            messages.append({'role':'assistant','content':text})
            if parse_error:
                errors.append(parse_error);break
            if not calls:
                final=text;break
            emitted.extend(calls)
            if turn==3:
                errors.append('tool_round_limit');break
            for call in calls:
                error=validate_call(call,names,message)
                if not error and any(e['call']==call for e in executed):
                    error='duplicate_call'
                if error:
                    errors.append(error)
                    observation={'error':error}
                else:
                    observation=mock_tool(call)
                    executed.append({'turn':turn,'call':call})
                event['observations'].append({'call':call,'result':observation})
            payload=event['observations'][0]['result'] if len(calls)==1 else event['observations']
            messages.append({'role':'tool','content':json.dumps(payload,ensure_ascii=False,separators=(',',':'))})
        self.torch.cuda.synchronize()
        generator_ms=(time.perf_counter()-start)*1000
        route_ms=0 if arm=='nesso_only' else ranking['elapsed_ms']
        return {'arm':arm,'available_tools':names,'ranking':None if arm=='nesso_only' else ranking,
                'emitted_calls':emitted,'executed_calls':executed,'errors':errors,'final':final,'trace':trace,
                'generated_tokens':total_tokens,'truncated':truncated,
                'generator_and_controller_ms':generator_ms,'route_ms':route_ms,'total_ms':generator_ms+route_ms}
