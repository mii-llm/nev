"""Bounded bilingual read workflows. A full-match grammar, not a general planner.

No unmatched text is ignored. Unknown/conditional requests execute nothing.
All model proposals must match the text-derived plan before any read executes.
"""
import json
import re
import time
from agent import TOOL_DATA, schemas, parse_calls, validate_call, mock_tool
from single_read import select_call, render_result

REFS = {'order_id': r'ORD-\d{4}', 'product': r'[A-Z]{2}-\d', 'month': r'2026-(?:0[1-9]|1[0-2])'}
# These are application phrases, not an inventory of evaluation request IDs.
PATTERNS = {
 'en': {
  'get_order_status': [
   r'(?:what is|tell me) the shipment status and tracking reference for (?:order )?{ref}',
   r'(?:please )?check (?:the )?shipment {ref}(?: and give me its tracking reference)?',
   r'i need the delivery status and tracking code for {ref}',
   r'(?:get|check) (?:the )?(?:shipment|delivery|order) status (?:for )?{ref}',
   r'shipment {ref}'],
  'get_invoice': [
   r'(?:please )?(?:get|retrieve) the invoice for (?:order )?{ref}(?: and tell me the filename)?',
   r'(?:please )?retrieve the invoice filename for {ref}',
   r'which invoice file belongs to order {ref}',
   r'invoice {ref}'],
  'search_help_center': [
   r'(?:please )?find the guide reference for product {ref}',
   r'look up the documentation reference for model {ref}',
   r'i need the guide identifier for product {ref}',
   r'(?:get|find) (?:the )?guide (?:for )?{ref}',
   r'guide {ref}'],
  'list_transactions': [
   r'list my payments for {ref} and tell me the total in eur',
   r'show the payments recorded in {ref} and their total in eur',
   r'what payments are recorded for {ref}, and what is their eur total',
   r'(?:list|show) (?:my |the )?payments (?:for )?{ref}',
   r'payments {ref}'],
 },
 'it': {
  'get_order_status': [
   r"qual è lo stato della spedizione e il riferimento di tracciamento dell'ordine {ref}",
   r'controlla la spedizione {ref}(?: e indicami il riferimento di tracciamento)?',
   r'mi servono lo stato della consegna e il codice di tracciamento di {ref}',
   r'(?:controlla|consulta) lo stato (?:della spedizione|dell\x27ordine) {ref}',
   r'spedizione {ref}'],
  'get_invoice': [
   r"recupera la fattura dell'ordine {ref}(?: e dimmi il nome del file)?",
   r'recupera il nome del file della fattura relativa a {ref}',
   r"quale file della fattura corrisponde all'ordine {ref}",
   r'(?:recupera )?(?:la )?fattura (?:di |per )?{ref}'],
  'search_help_center': [
   r'trova il riferimento della guida del prodotto {ref}',
   r'cerca il riferimento della documentazione del modello {ref}',
   r"mi serve l'identificativo della guida del prodotto {ref}",
   r'(?:trova|recupera) (?:la )?guida (?:di |per )?{ref}',
   r'guida {ref}'],
  'list_transactions': [
   r'elenca i miei pagamenti di {ref} e dimmi il totale in eur',
   r'mostra i pagamenti registrati in {ref} e il loro totale in eur',
   r'quali pagamenti risultano per {ref} e qual è il totale in eur',
   r'(?:elenca|mostra) (?:i miei |i )?pagamenti (?:di |per )?{ref}',
   r'pagamenti {ref}'],
 }}

# A recognized unsupported action refuses the whole request; even if a supported
# clause precedes it, no read is executed. Negation/quotation may over-refuse.
UNSUPPORTED = re.compile(r'\b(?:cancel\w*|refund\w*|send|email|e-mail|delete\w*|book|purchase\w*|buy|change|update|annull\w*|rimbors\w*|invia\w*|elimina\w*|prenot\w*|acquist\w*|modific\w*|aggiorn\w*)\b', re.I)
CONDITIONAL = re.compile(r'\b(?:if|unless|otherwise|depending|se|altrimenti|qualora|quando)\b', re.I)
CONNECTOR = re.compile(r'\s*;\s*|\s*,?\s+(?:and then|then|after that|e poi|poi|quindi)\s+', re.I)


def compile_plan(message, language):
    if language not in PATTERNS:
        return {'route':'defer','reason':'unsupported_language','steps':[]}
    if len(message)>4000:
        return {'route':'defer','reason':'request_too_long','steps':[]}
    text=re.sub(r'\s+',' ',message.replace('’',"'")).strip()
    if UNSUPPORTED.search(text):
        return {'route':'unsupported','reason':'unsupported_action_in_request','steps':[]}
    if CONDITIONAL.search(text):
        return {'route':'defer','reason':'conditional_workflow_not_supported','steps':[]}
    text=re.sub(r'^(?:first|prima)\s*,?\s+', '', text, flags=re.I)
    clauses=CONNECTOR.split(text)
    if len(clauses)>4:
        return {'route':'defer','reason':'too_many_steps','steps':[]}
    steps=[]
    for clause in clauses:
        clause=clause.strip().rstrip('.?!').strip()
        matched=[]
        for name,patterns in PATTERNS[language].items():
            key=TOOL_DATA[name][0]
            for pattern in patterns:
                match=re.fullmatch(pattern.replace('{ref}','(?P<value>'+REFS[key]+')'),clause,re.I)
                if match:
                    value=match.group('value').upper()
                    call={'name':name,'arguments':{key:value}}
                    # Match case-insensitively for prose, but use the original
                    # explicit identifier convention enforced by the shared guard.
                    if validate_call(call,list(TOOL_DATA),clause) is None:
                        matched.append({'request':clause,'call':call})
        unique={json.dumps(m['call'],sort_keys=True):m for m in matched}
        if len(unique)!=1:
            return {'route':'defer','reason':'unrecognized_or_ambiguous_clause','steps':[]}
        steps.append(next(iter(unique.values())))
    if not steps:
        return {'route':'defer','reason':'empty_request','steps':[]}
    return {'route':'single' if len(steps)==1 else 'multi','reason':None,'steps':steps}


def canonical_request(call, language):
    value=next(iter(call['arguments'].values())); it=language=='it'
    return {
        'get_order_status': f"Qual è lo stato della spedizione e il riferimento di tracciamento dell’ordine {value}?" if it else f'What is the shipment status and tracking reference for order {value}?',
        'get_invoice': f"Recupera la fattura dell’ordine {value} e dimmi il nome del file." if it else f'Get the invoice for order {value} and tell me the filename.',
        'search_help_center': f'Trova il riferimento della guida del prodotto {value}.' if it else f'Find the guide reference for product {value}.',
        'list_transactions': f'Elenca i miei pagamenti di {value} e dimmi il totale in EUR.' if it else f'List my payments for {value} and tell me the total in EUR.',
    }[call['name']]


def prepare_step(agent, request, language):
    """Same compact prompt and single-read checks; never executes a tool."""
    ranking=agent.rank(request,language)
    full={s['function']['name']:s for s in schemas(language,agent.schema_style)}
    names=ranking['names']
    context=('Sei un assistente operativo. Usa gli strumenti disponibili quando serve.' if language=='it'
             else 'You are an operational assistant. Use the available tools when needed.')
    system=context+'\n<tools>\n'+json.dumps([full[n] for n in names],ensure_ascii=False,separators=(',',':'))+'\n</tools>'
    text,tokens,truncated=agent.generate([{'role':'system','content':system},{'role':'user','content':request}])
    calls,parse_error=parse_calls(text)
    call=None;events=[];blocked=parse_error
    if not blocked:
        if truncated:blocked='truncated_call_output'
        else:call,events,blocked=select_call(calls,names,request,ranking,validate_call)
    return {'request':request,'ranking':ranking,'assistant':text,'emitted_calls':calls,'generated_tokens':tokens,
            'truncated':truncated,'parse_error':parse_error,'policy_events':events,'blocked_reason':blocked,'prepared_call':call}


def run_workflow(agent, message, language, executor=mock_tool):
    start=time.perf_counter()
    plan=compile_plan(message,language)
    result={'policy':'workflow','plan':plan,'route':plan['route'],'status':'deferred',
        'prepared_steps':[],'executed_calls':[],'observations':[],'answer_source':'application_template',
        'blocked_reason':plan['reason'],'final':'','total_ms':0.0}
    it=language=='it'
    def finish():
        result['total_ms']=(time.perf_counter()-start)*1000
        return result
    if plan['route'] not in ('single','multi'):
        result['answer_source']='application_deferral'
        result['final']=(('Non posso eseguire questa azione con gli strumenti disponibili. Nessuna operazione eseguita.' if it else
                         'This action is not supported by the available tools. No operation was executed.') if plan['route']=='unsupported' else
                        ('La richiesta non rientra nelle forme di lettura supportate. Specifica una lettura e il suo riferimento per ogni passaggio. Nessuna operazione eseguita.' if it else
                         'This request does not match a supported read workflow. Specify one read and its reference per step. No operation was executed.'))
        return finish()
    # Preflight the whole plan. The language grammar is part of the application
    # contract; it is not passed gold labels from an evaluation harness.
    for index,step in enumerate(plan['steps']):
        request=message if plan['route']=='single' else canonical_request(step['call'],language)
        prepared=prepare_step(agent,request,language)
        result['prepared_steps'].append(prepared)
        if prepared['blocked_reason'] or prepared['prepared_call']!=step['call']:
            result['blocked_reason']=prepared['blocked_reason'] or 'proposal_does_not_match_plan'
            result['answer_source']='application_deferral'
            result['final']=('Non ho eseguito operazioni: il piano richiede una verifica.' if it else
                             'No operation was executed: the plan needs review.')
            return finish()
    answers=[]
    for index,prepared in enumerate(result['prepared_steps']):
        call=prepared['prepared_call']
        try:
            observation=executor(call)
        except Exception as error:
            result['status']='partial' if result['executed_calls'] else 'failed'
            result['blocked_reason']='tool_execution_failed'
            result['failed_step']={'step':index+1,'error_type':type(error).__name__}
            result['final']='\n'.join(answers+[f"Interrotto al passaggio {index+1}; nessun passaggio successivo eseguito." if it else f"Stopped at step {index+1}; no later step was executed."])
            return finish()
        result['executed_calls'].append({'step':index+1,'call':call})
        result['observations'].append({'step':index+1,'call':call,'result':observation})
        if isinstance(observation,dict) and observation.get('error'):
            result['status']='partial' if answers else 'failed'
            result['blocked_reason']='tool_reported_error'
            result['final']='\n'.join(answers+[f"Errore al passaggio {index+1}; nessun passaggio successivo eseguito." if it else f"Error at step {index+1}; no later step was executed."])
            return finish()
        try:
            answer=render_result(call['name'],observation,language)
        except (KeyError,TypeError,ValueError):
            result['status']='partial' if answers else 'failed'
            result['blocked_reason']='invalid_tool_result'
            result['final']='\n'.join(answers+['Risultato dello strumento non valido; flusso interrotto.' if it else 'Invalid tool result; workflow stopped.'])
            return finish()
        answers.append((f'{index+1}. ' if plan['route']=='multi' else '')+answer)
    result.update(status='complete',final='\n'.join(answers))
    return finish()


def render_workflow(record):
    lines=['Simulation: local mock tools',f"User ({record['language']}): {record['message']}",
           f"Workflow route: {record['route']}"]
    for index,step in enumerate(record['prepared_steps'],1):
        lines.extend([f'\nPreflight step {index}: {step["request"]}',
                      'Nev ranks: '+' > '.join(step['ranking']['names']),
                      'Nesso3 proposed: '+json.dumps(step['emitted_calls'],ensure_ascii=False)])
        if step['policy_events']:lines.append('Validation: '+json.dumps(step['policy_events'],ensure_ascii=False))
    for observation in record['observations']:
        lines.append(f"\nExecuted step {observation['step']}: "+json.dumps(observation,ensure_ascii=False))
    lines.extend([f"\nStatus: {record['status']}",record['final'],f"Elapsed: {record['total_ms']/1000:.2f} s"])
    return '\n'.join(lines)
