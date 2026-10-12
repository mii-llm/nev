"""Freeze an authored 40-pair bilingual pilot before inspecting model outputs."""
import json
from pathlib import Path

cases = []
def add(name, category, en, it, calls, anchors=(), keywords=()):
    for lang, message in [('en', en), ('it', it)]:
        cases.append({'id': f'{name}/{lang}', 'pair': name, 'category': category,
                      'language': lang, 'message': message, 'expected_calls': calls,
                      'answer_anchor_groups': anchors, 'behavior_keywords': keywords})

def call(name, **arguments):
    return {'name': name, 'arguments': arguments}

for i in range(4):
    order = f'ORD-{6101+i}'
    month = f'2026-{i+5:02}'
    product = ['PX-7', 'MX-4', 'LX-2', 'QX-9'][i]
    add(f'order_{i}', 'single',
        [f'Can you check the delivery progress for {order}? Please include the tracking reference.',
         f'I am arranging for someone to be home when {order} arrives. Look up the shipment and give me its tracking reference.',
         f'The courier page is unavailable on my phone. Please retrieve the current shipment details and tracking reference for {order}.',
         f'Could you look up {order} and tell me the shipment status together with the tracking reference?'][i],
        [f'Puoi controllare l’avanzamento della consegna per {order}? Includi il riferimento di tracciamento.',
         f'Sto organizzando la presenza di qualcuno a casa all’arrivo di {order}. Consulta la spedizione e dammi il riferimento di tracciamento.',
         f'La pagina del corriere non funziona sul mio telefono. Recupera i dettagli attuali della spedizione e il riferimento di tracciamento per {order}.',
         f'Puoi cercare {order} e dirmi lo stato della spedizione insieme al riferimento di tracciamento?'][i],
        [call('get_order_status', order_id=order)], [[f'TRK-{order}']])
    add(f'invoice_{i}', 'single',
        [f'I am preparing my expense claim. Retrieve the invoice for {order} and tell me its filename.',
         f'Our accountant needs the invoice document for {order}. Please fetch it and provide the filename.',
         f'I cannot find my receipt email for {order}. Could you retrieve the invoice and report the filename?',
         f'Please obtain the invoice file associated with {order}; I need its filename for our records.'][i],
        [f'Sto preparando la nota spese. Recupera la fattura di {order} e dimmi il nome del file.',
         f'Al nostro commercialista serve il documento della fattura di {order}. Recuperalo e indica il nome del file.',
         f'Non trovo l’email con la ricevuta di {order}. Puoi recuperare la fattura e riportare il nome del file?',
         f'Recupera il file della fattura associata a {order}; mi serve il nome del file per il nostro archivio.'][i],
        [call('get_invoice', order_id=order)], [[f'invoice_{order}.pdf']])
    add(f'guide_{i}', 'single',
        f'I need the documentation for product {product}. Search the help center and tell me the guide reference.',
        f'Mi serve la documentazione del prodotto {product}. Cerca nel centro assistenza e dimmi il riferimento della guida.',
        [call('search_help_center', product=product)], [[f'GUIDE-{product}']])
    add(f'payments_{i}', 'single',
        f'Please look up my recorded payments for {month}. Tell me their total in EUR so I can reconcile the statement.',
        f'Consulta i miei pagamenti registrati per {month}. Dimmi il totale in EUR per confrontarlo con l’estratto conto.',
        [call('list_transactions', month=month)], [['63.75', '63,75']])

for i in range(2):
    order=f'ORD-{7201+i}'
    add(f'focus_invoice_{i}', 'distractor',
        f'The delivery question about {order} is already resolved. My only request now is its invoice document; retrieve it and give me the filename.',
        f'Il problema della consegna di {order} è già risolto. Ora mi serve soltanto il documento della fattura: recuperalo e dammi il nome del file.',
        [call('get_invoice', order_id=order)], [[f'invoice_{order}.pdf']])
    add(f'focus_order_{i}', 'distractor',
        f'I already downloaded the invoice for {order}, so do not fetch that again. Check the shipment and give me its tracking reference.',
        f'Ho già scaricato la fattura di {order}, quindi non recuperarla di nuovo. Controlla la spedizione e dammi il riferimento di tracciamento.',
        [call('get_order_status', order_id=order)], [[f'TRK-{order}']])
    product=['PX-7','MX-4'][i];month=f'2026-{i+8:02}'
    add(f'focus_guide_{i}', 'distractor',
        f'I bought {product} last month, but I am not asking about payment or delivery. Search its documentation and give me the guide reference.',
        f'Ho comprato {product} il mese scorso, ma non chiedo informazioni su pagamento o consegna. Cerca la documentazione e dammi il riferimento della guida.',
        [call('search_help_center', product=product)], [[f'GUIDE-{product}']])
    add(f'focus_payments_{i}', 'distractor',
        f'I do not need an invoice copy. Look up the recorded payments for {month} and tell me the total in EUR.',
        f'Non mi serve una copia della fattura. Consulta i pagamenti registrati per {month} e dimmi il totale in EUR.',
        [call('list_transactions', month=month)], [['63.75','63,75']])

for i in range(4):
    order=f'ORD-{8301+i}'
    add(f'two_step_{i}', 'two_step',
        f'For {order}, first look up the shipment and wait for the result. Then retrieve its invoice. Finally report both the tracking reference and invoice filename.',
        f'Per {order}, prima consulta la spedizione e attendi il risultato. Poi recupera la fattura. Infine riporta sia il riferimento di tracciamento sia il nome del file della fattura.',
        [call('get_order_status',order_id=order),call('get_invoice',order_id=order)],
        [[f'TRK-{order}'],[f'invoice_{order}.pdf']])

missing=[
('order','Please check my delivery and give me its tracking reference.','Controlla la mia consegna e dammi il riferimento di tracciamento.',['order','ordine']),
('invoice','Please retrieve my invoice document.','Recupera il documento della mia fattura.',['order','ordine']),
('guide','Find the documentation for my device.','Trova la documentazione del mio dispositivo.',['product','device','model','prodotto','dispositivo','modello']),
('payments','Look up my payments and tell me their total.','Consulta i miei pagamenti e dimmi il totale.',['month','period','date','mese','periodo','data'])]
for name,en,it,keys in missing: add('missing_'+name,'missing',en,it,[],keywords=keys)
for name,en,it,anchors in [
('capital_it','What is the capital of Italy?','Qual è la capitale d’Italia?',[['Rome','Roma']]),
('capital_fr','What is the capital of France?','Qual è la capitale della Francia?',[['Paris','Parigi']]),
('arithmetic','What is two plus three?','Quanto fa due più tre?',[['5','five','cinque']]),
('translation','Translate the English word "invoice" into Italian.','Come si traduce in italiano la parola inglese "invoice"?',[['fattura']])]:
 add('no_tool_'+name,'no_tool',en,it,[],anchors=anchors)
for name,en,it in [
('cancel','Cancel order ORD-9401 immediately.','Annulla immediatamente l’ordine ORD-9401.'),
('refund','Issue a refund for order ORD-9402.','Emetti un rimborso per l’ordine ORD-9402.'),
('email','Send the invoice for ORD-9403 by email to my accountant.','Invia per email la fattura di ORD-9403 al mio commercialista.'),
('address','Change the delivery address of ORD-9404 to my office.','Cambia l’indirizzo di consegna di ORD-9404 con quello del mio ufficio.')]:
 add('unavailable_'+name,'unavailable',en,it,[],keywords=['cannot',"can't",'unable','not available','do not have','non posso','non è disponibile','non ho','non support','non dispon'])

assert len(cases)==80 and len({c['pair'] for c in cases})==40
payload={'scope':'Authored pilot, 40 parallel EN/IT pairs. Fixed before inference. Synthetic read-only tools and data. Not a representative benchmark.',
         'design':'16 single + 8 distractor + 4 two-step + 4 missing + 4 no-tool + 4 unavailable pairs; identical requests and validation in all arms.',
         'scoring':'Exact emitted calls/arguments; distinct ordered turns for two-step; literal tool-result anchors for tool cases; keyword heuristics for clarification/refusal and answer anchors for no-tool. Mechanical pass is not a semantic correctness guarantee.',
         'cases':cases}
if __name__=='__main__':
    target=Path(__file__).with_name('cases.json')
    if target.exists(): raise FileExistsError('Preserve frozen cases; choose a new experiment for edits')
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(len(cases),'cases written')
