import json
from pathlib import Path
root=Path(__file__).resolve().parent
questions={
'en':{
 'route':{'type':'choice','instructions':'Choose the team for the primary requested action, ignoring background complaints. Confirmed unauthorized account activity takes precedence and must go to security. Otherwise: returning a product goes to returns; correcting a duplicate charge to billing; restoring login to account; locating a parcel to shipping. Verified facts override customer speculation.','criteria':{'shipping':'Parcel tracking and delivery','billing':'Payment corrections','account':'Login recovery','returns':'Product returns','security':'Confirmed unauthorized account activity'}},
 'refund':{'type':'noul','instructions':'Apply this synthetic shop policy exactly. Approve reimbursement if a duplicate posted charge is confirmed and has not already been refunded, OR if this is a product-return request and the product is unopened and delivered at most 30 days ago. Otherwise reject. A delivery delay alone does not qualify.','criteria':{'false':'Do not approve reimbursement','true':'Approve reimbursement'}},
 'urgency':{'type':'score','instructions':'Choose level 2 for confirmed unauthorized account activity OR a delivery deadline within 24 hours (inclusive). Otherwise choose level 1 for a delivery deadline within 72 hours (inclusive). Otherwise choose level 0. Angry wording alone does not increase urgency.','criteria':['Routine','Priority','Urgent']},
 'escalate':{'type':'noul','instructions':'Escalate to a human supervisor if confirmed unauthorized account activity is present OR there have been at least 3 previous unsuccessful support contacts. Otherwise do not escalate.','criteria':{'false':'No supervisor escalation','true':'Escalate to a human supervisor'}}},
'it':{
 'route':{'type':'choice','instructions':'Scegli il reparto per l’azione principale richiesta, ignorando le lamentele di contorno. Un’attività non autorizzata confermata sull’account ha precedenza e va alla sicurezza. Altrimenti: la restituzione di un prodotto va ai resi; la correzione di un doppio addebito alla fatturazione; il ripristino dell’accesso all’assistenza account; la ricerca di un pacco alle spedizioni. I fatti verificati prevalgono sui sospetti del cliente.','criteria':{'shipping':'Tracciamento pacchi e consegne','billing':'Correzione dei pagamenti','account':'Recupero dell’accesso','returns':'Restituzione dei prodotti','security':'Attività non autorizzata confermata sull’account'}},
 'refund':{'type':'noul','instructions':'Applica esattamente questa politica commerciale sintetica. Approva il rimborso se è confermato un doppio addebito contabilizzato non ancora rimborsato, OPPURE se si richiede la restituzione di un prodotto non aperto, consegnato al massimo 30 giorni fa. Altrimenti rifiuta. Un ritardo nella consegna da solo non è sufficiente.','criteria':{'false':'Non approvare il rimborso','true':'Approva il rimborso'}},
 'urgency':{'type':'score','instructions':'Scegli il livello 2 se è confermata un’attività non autorizzata sull’account OPPURE la scadenza per la consegna è entro 24 ore incluse. Altrimenti scegli il livello 1 se la scadenza è entro 72 ore incluse. Altrimenti scegli il livello 0. Il tono arrabbiato da solo non aumenta l’urgenza.','criteria':['Ordinaria','Prioritaria','Urgente']},
 'escalate':{'type':'noul','instructions':'Passa il caso a un supervisore umano se è confermata un’attività non autorizzata sull’account OPPURE ci sono stati almeno 3 precedenti contatti con l’assistenza senza soluzione. Altrimenti non passare al supervisore.','criteria':{'false':'Non passare al supervisore','true':'Passa a un supervisore umano'}}}}
base=dict(days_since_delivery=None,unopened=False,duplicate_charge=False,already_refunded=False,unauthorized_activity=False,deadline_hours=None,previous_failed_contacts=1)
pairs=[
 ('return_window','days_since_delivery',[29,31],{},'returns',
  'Delivery was late and the invoice looks confusing, but what I want now is to return the unopened product. Please approve my return.',
  'La consegna era in ritardo e la fattura è poco chiara, ma ora voglio restituire il prodotto non aperto. Vorrei l’approvazione del reso.',
  [{'route':'returns','refund':'true','urgency':'0','escalate':'false'},{'route':'returns','refund':'false','urgency':'0','escalate':'false'}]),
 ('security_override','unauthorized_activity',[False,True],{},'account',
  'I cannot log in. The order is also late and I suspect a strange payment, but my main request is to restore account access. Please check the verified security findings.',
  'Non riesco ad accedere. Anche l’ordine è in ritardo e sospetto un pagamento strano, ma la mia richiesta principale è recuperare l’accesso. Controllate gli esiti della verifica di sicurezza.',
  [{'route':'account','refund':'false','urgency':'0','escalate':'false'},{'route':'security','refund':'false','urgency':'2','escalate':'true'}]),
 ('duplicate_reimbursement','already_refunded',[False,True],{'duplicate_charge':True},'billing',
  'I mentioned returning the product yesterday, but I am keeping it. Today I only want the duplicate payment corrected. Check whether you have already reimbursed it before issuing more money.',
  'Ieri avevo parlato di restituire il prodotto, ma lo tengo. Oggi voglio soltanto correggere il doppio pagamento. Verificate se è già stato rimborsato prima di restituire altro denaro.',
  [{'route':'billing','refund':'true','urgency':'0','escalate':'false'},{'route':'billing','refund':'false','urgency':'0','escalate':'false'}]),
 ('delivery_deadline','deadline_hours',[25,23],{},'shipping',
  'This is outrageous! Ignore the old billing complaint; it has been resolved. I need you to locate my parcel before the verified delivery deadline. I am not requesting a return.',
  'È assurdo! Ignorate il vecchio reclamo sulla fattura: è stato risolto. Voglio sapere dove si trova il pacco prima della scadenza verificata per la consegna. Non sto chiedendo un reso.',
  [{'route':'shipping','refund':'false','urgency':'1','escalate':'false'},{'route':'shipping','refund':'false','urgency':'2','escalate':'false'}]),
 ('repeat_contact','previous_failed_contacts',[2,3],{'deadline_hours':48},'shipping',
  'The password reset worked, thank you. The remaining issue is the missing parcel. Please locate it; previous support contacts about this delivery have not resolved the problem.',
  'Il ripristino della password ha funzionato, grazie. Rimane il problema del pacco mancante. Vorrei rintracciarlo: i precedenti contatti con l’assistenza sulla consegna non hanno risolto il problema.',
  [{'route':'shipping','refund':'false','urgency':'1','escalate':'false'},{'route':'shipping','refund':'false','urgency':'1','escalate':'true'}])]
labels={'en':['Days since delivery','Product unopened','Confirmed duplicate posted charge','Duplicate charge already refunded','Confirmed unauthorized account activity','Hours until delivery deadline (none means no deadline)','Previous unsuccessful support contacts'], 'it':['Giorni dalla consegna','Prodotto non aperto','Doppio addebito contabilizzato confermato','Doppio addebito già rimborsato','Attività non autorizzata confermata sull’account','Ore alla scadenza per la consegna (nessuna indica assenza di scadenza)','Precedenti contatti con l’assistenza senza soluzione']}
cases=[]
for pair,field,values,changes,action,en,it,golds in pairs:
 facts0={**base,**changes}
 if pair=='return_window':facts0['unopened']=True
 for side,(value,gold) in enumerate(zip(values,golds)):
  facts={**facts0,field:value}
  # Independent executable checks against the explicit answer key above.
  computed={'route':'security' if facts['unauthorized_activity'] else action,
   'refund':str((facts['duplicate_charge'] and not facts['already_refunded']) or (action=='returns' and facts['unopened'] and facts['days_since_delivery']<=30)).lower(),
   'urgency':str(2 if facts['unauthorized_activity'] or (facts['deadline_hours'] is not None and facts['deadline_hours']<=24) else 1 if facts['deadline_hours'] is not None and facts['deadline_hours']<=72 else 0),
   'escalate':str(facts['unauthorized_activity'] or facts['previous_failed_contacts']>=3).lower()}
  assert computed==gold,(pair,side)
  for lang,text in [('en',en),('it',it)]:
   def display(v):
    if isinstance(v,bool):return ('sì' if v else 'no') if lang=='it' else ('yes' if v else 'no')
    if v is None:return 'nessuna' if lang=='it' else 'none'
    return v
   state={('messaggio_cliente' if lang=='it' else 'customer_message'):text,('fatti_verificati' if lang=='it' else 'verified_facts'):{k:display(v) for k,v in zip(labels[lang],facts.values())}}
   cases.append({'id':f'{pair}/{side}/{lang}','pair':pair,'side':side,'language':lang,'changed_fact':field,'request':{'state':state,'questions':questions[lang]},'expected':gold})
(root/'scenarios.json').write_text(json.dumps({'description':'Authored bilingual diagnostic examples; 5 one-fact contrast pairs, 4 simultaneous decisions. Fixed before observing either model. Not a benchmark or a representative accuracy estimate.','cases':cases},ensure_ascii=False,indent=2)+'\n')
# A standalone complex request works with the existing single-request CLI too.
(root/'request-complex-it.json').write_text(json.dumps(cases[7]['request'],ensure_ascii=False,indent=2)+'\n')
print(len(cases),'requests;',len(cases)*4,'decisions per model')
