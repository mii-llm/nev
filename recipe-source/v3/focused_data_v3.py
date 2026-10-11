"""Synthetic EN/IT intent and routing transfer cases; no benchmark questions used."""
import random
from practical_data import sha, facts, oracle, LABELS, generate as old_v1
from practical_data_v2 import generate as old_v2, render as old_render

SIZES = {'train':512, 'dev':128, 'calibration_fit':128, 'calibration_policy':128, 'test':256}
BANKS = {'train':(0,1,2,3), 'dev':(4,), 'calibration_fit':(5,), 'calibration_policy':(6,), 'test':(7,8)}
# Description, two training utterances, development/calibration utterance, test utterance.
# Each item has an independently authored EN and IT realization.
INTENTS = [
 [('reset_password','reset a forgotten password','reimpostare una password dimenticata'),('I forgot my password.','Ho dimenticato la password.'),('Please help me reset my login password.','Aiutatemi a reimpostare la password di accesso.'),('How can I replace the password I no longer remember?','Come posso sostituire la password che non ricordo più?'),('My login secret has slipped my mind; I need a new one.','Non ricordo più la credenziale segreta di accesso; me ne serve una nuova.')],
 [('change_address','change a delivery address','cambiare un indirizzo di consegna'),('Send my order to a different address.','Inviate il mio ordine a un indirizzo diverso.'),('I need to update the delivery address.','Devo aggiornare l’indirizzo di consegna.'),('Where do I edit the destination for my parcel?','Dove modifico la destinazione del pacco?'),('The package must go to my new home instead of the old one.','Il pacco deve arrivare nella nuova casa anziché in quella vecchia.')],
 [('track_delivery','track the location of a delivery','localizzare una consegna'),('Where is my parcel?','Dove si trova il mio pacco?'),('Show me the tracking status of my order.','Mostratemi lo stato della spedizione del mio ordine.'),('Can you tell me how far my shipment has travelled?','Potete dirmi a che punto è la mia spedizione?'),('I want to locate the package while it is in transit.','Voglio sapere dove si trova il pacco durante il trasporto.')],
 [('cancel_order','cancel an order before delivery','annullare un ordine prima della consegna'),('Cancel my order before it ships.','Annullate l’ordine prima che venga spedito.'),('I no longer want this order; please cancel it.','Non voglio più questo ordine; annullatelo.'),('Can you stop this purchase from being dispatched?','Potete impedire che questo acquisto venga spedito?'),('Please withdraw the purchase that is still awaiting dispatch.','Ritirate l’acquisto che è ancora in attesa di spedizione.')],
 [('request_refund','request a new refund','richiedere un nuovo rimborso'),('I want a refund for this purchase.','Voglio un rimborso per questo acquisto.'),('Please open a refund request.','Aprite una richiesta di rimborso.'),('How do I start getting my money back?','Come posso avviare la restituzione del denaro?'),('I would like to initiate reimbursement for the item.','Vorrei avviare il rimborso dell’articolo.')],
 [('refund_status','check an existing refund status','verificare lo stato di un rimborso già richiesto'),('Has my requested refund been processed?','Il rimborso che ho richiesto è stato elaborato?'),('Check the progress of my existing refund.','Controllate l’avanzamento del rimborso già richiesto.'),('When will the reimbursement I already requested arrive?','Quando arriverà il rimborso che ho già richiesto?'),('I am waiting for an approved repayment; tell me where it stands.','Aspetto una restituzione già approvata; ditemi a che punto è.')],
 [('download_invoice','obtain a copy of an invoice','ottenere una copia di una fattura'),('Send me a copy of the invoice.','Inviatemi una copia della fattura.'),('Where can I download my invoice?','Dove posso scaricare la fattura?'),('I need the billing document for my records.','Mi serve il documento di fatturazione per l’archivio.'),('Please provide the itemized invoice for my purchase.','Fornite la fattura dettagliata del mio acquisto.')],
 [('dispute_charge','dispute an unrecognized charge','contestare un addebito non riconosciuto'),('I do not recognize this charge.','Non riconosco questo addebito.'),('I want to dispute a payment I did not authorize.','Voglio contestare un pagamento che non ho autorizzato.'),('Someone billed me for a purchase I never made.','Mi è stato addebitato un acquisto che non ho mai fatto.'),('There is an unauthorized debit on my statement; challenge it.','C’è un addebito non autorizzato nell’estratto conto; contestatelo.')],
 [('freeze_card','temporarily freeze a payment card','bloccare temporaneamente una carta di pagamento'),('Temporarily freeze my payment card.','Bloccate temporaneamente la carta di pagamento.'),('Pause all spending on my card for now.','Sospendete per ora tutte le spese con la mia carta.'),('I want a reversible block on my card.','Voglio un blocco reversibile della carta.'),('Disable card transactions until I decide to reactivate them.','Disabilitate le operazioni con la carta finché non deciderò di riattivarle.')],
 [('replace_card','order a replacement payment card','ordinare una carta di pagamento sostitutiva'),('I need a replacement card.','Mi serve una carta sostitutiva.'),('Order a new physical card to replace this one.','Ordinate una nuova carta fisica per sostituire questa.'),('How can I get another card instead of my damaged one?','Come posso ottenere un’altra carta al posto di quella danneggiata?'),('The plastic is broken; please issue a substitute card.','La tessera è rotta; emettete una carta sostitutiva.')],
 [('change_plan','switch a subscription plan','cambiare piano di abbonamento'),('I want to switch subscription plans.','Voglio cambiare piano di abbonamento.'),('Move my subscription to another tier.','Passate il mio abbonamento a un altro livello.'),('Can I upgrade or downgrade my current package?','Posso passare a un pacchetto superiore o inferiore?'),('Keep my subscription active but put it on a different tariff.','Mantenete attivo l’abbonamento ma applicate una tariffa diversa.')],
 [('cancel_subscription','end a recurring subscription','terminare un abbonamento ricorrente'),('Cancel my recurring subscription.','Annullate il mio abbonamento ricorrente.'),('Stop renewing this subscription.','Interrompete il rinnovo di questo abbonamento.'),('I want to end my membership and its recurring payments.','Voglio terminare l’iscrizione e i relativi pagamenti ricorrenti.'),('Do not extend my membership when the current period expires.','Non prolungate la mia iscrizione alla scadenza del periodo attuale.')],
 [('book_appointment','make a new appointment','fissare un nuovo appuntamento'),('I would like to book an appointment.','Vorrei prenotare un appuntamento.'),('Schedule a new visit for me.','Fissate una nuova visita per me.'),('Find me an available slot for a meeting.','Trovatemi un orario disponibile per un incontro.'),('Please reserve a time for my first consultation.','Riservate un orario per la mia prima consulenza.')],
 [('reschedule_appointment','move an existing appointment','spostare un appuntamento esistente'),('Move my existing appointment to another day.','Spostate il mio appuntamento a un altro giorno.'),('I need to reschedule the visit I already booked.','Devo riprogrammare la visita già prenotata.'),('Can we change the time of my confirmed meeting?','Possiamo cambiare l’orario dell’incontro confermato?'),('Keep my reservation but shift it to a later slot.','Mantenete la prenotazione ma spostatela a un orario successivo.')],
 [('report_outage','report a service outage','segnalare un’interruzione del servizio'),('The service is down; report an outage.','Il servizio non funziona; segnalate un’interruzione.'),('My connection has stopped working completely.','La connessione ha smesso completamente di funzionare.'),('There is no service at all; I need to report the interruption.','Non c’è alcun servizio; devo segnalare l’interruzione.'),('Everything went offline and I want the failure investigated.','È tutto fuori servizio e voglio che venga verificato il guasto.')],
 [('human_agent','request to speak with a human agent','richiedere di parlare con un operatore umano'),('Let me speak to a human agent.','Fatemi parlare con un operatore umano.'),('Please transfer me to a real person.','Trasferitemi a una persona reale.'),('I would prefer an operator instead of automated assistance.','Preferirei un operatore anziché l’assistenza automatica.'),('Put me through to a member of your support staff.','Mettetemi in contatto con un membro del personale di assistenza.')],
]
ROUTING = [
 ('Apply priority {order}. Consider only active issues; billing additionally requires {minimum} EUR or more. If none qualifies, use general.', 'Applica la priorità {order}. Considera solo problemi attivi; per fatturazione servono anche almeno {minimum} EUR. Se nessuno è ammissibile, usa generale.'),
 ('Filter out absent problems and billing below {minimum} EUR. Select the first remaining team in {order}, or general when no team remains.', 'Elimina problemi assenti e fatturazione sotto {minimum} EUR. Scegli il primo reparto rimasto in {order}, oppure generale se non ne rimane nessuno.'),
 ('An issue must be present to be routed. Billing also needs amount >= {minimum} EUR. Among eligible issues use {order} from left to right; default to general.', 'Un problema deve essere presente per essere instradato. Fatturazione richiede anche importo >= {minimum} EUR. Tra i problemi ammissibili usa {order} da sinistra a destra; altrimenti generale.'),
 ('Use general only if nothing is eligible. Present issues qualify except billing amounts under {minimum} EUR. Break ties with priority {order}.', 'Usa generale solo se nulla è ammissibile. I problemi presenti sono ammissibili salvo fatturazione sotto {minimum} EUR. Risolvi le parità con priorità {order}.'),
 ('Allocate the case by the ordered queue {order}. Ignore inactive categories and billing with less than {minimum} EUR. The earliest survivor wins; otherwise general.', 'Assegna il caso secondo la coda ordinata {order}. Ignora categorie inattive e fatturazione con meno di {minimum} EUR. Vince la prima rimasta; altrimenti generale.'),
 ('Read {order} as descending precedence. Choose the highest present issue that qualifies, where billing requires at least {minimum} EUR. Choose general if there is none.', 'Leggi {order} come precedenza decrescente. Scegli il problema presente più alto e ammissibile; fatturazione richiede almeno {minimum} EUR. Se non ce ne sono scegli generale.'),
 ('Determine the first applicable destination in {order}. All missing issues are excluded; also exclude billing below {minimum} EUR. Fall back to general.', 'Determina la prima destinazione applicabile in {order}. Escludi tutti i problemi assenti e fatturazione sotto {minimum} EUR. In assenza di alternative usa generale.'),
 ('Which queue takes ownership? Test {order} in sequence. Stop at a reported issue, but skip billing unless its amount reaches {minimum} EUR. With no match, choose general.', 'Quale coda prende in carico il caso? Controlla {order} in sequenza. Fermati a un problema segnalato, ma salta fatturazione se l’importo non raggiunge {minimum} EUR. Senza corrispondenze scegli generale.'),
 ('Give the case to the earliest valid team listed in {order}. Valid means the issue exists, plus amount no lower than {minimum} EUR for billing. If all fail, assign general.', 'Assegna il caso al primo reparto valido elencato in {order}. Valido significa problema esistente e, per fatturazione, importo non inferiore a {minimum} EUR. Se tutti falliscono assegna generale.'),
]
INTENT_RULES = [
 ('Classify the intent of the last customer message. Earlier messages are context only.', 'Classifica l’intento dell’ultimo messaggio del cliente. I messaggi precedenti sono solo contesto.'),
 ('Which intent describes what the customer asks for most recently?', 'Quale intento descrive ciò che il cliente chiede più recentemente?'),
 ('Select the category of the final request, ignoring earlier requests for this decision.', 'Scegli la categoria della richiesta finale, ignorando quelle precedenti per questa decisione.'),
 ('Identify the latest customer need using the available intent descriptions.', 'Identifica l’ultima esigenza del cliente usando le descrizioni degli intenti disponibili.'),
 ('The conversation may change topic. Label only the customer’s final turn.', 'La conversazione può cambiare argomento. Etichetta soltanto l’ultimo intervento del cliente.'),
 ('Determine which listed intent fits the most recent utterance.', 'Determina quale intento elencato corrisponde all’enunciato più recente.'),
 ('Choose the intent of the request at the end of the conversation.', 'Scegli l’intento della richiesta alla fine della conversazione.'),
 ('What does the customer want now? Use the final message to choose a category.', 'Che cosa vuole ora il cliente? Usa il messaggio finale per scegliere una categoria.'),
 ('Assign an intent to the closing customer message; previous turns do not determine this label.', 'Assegna un intento al messaggio conclusivo del cliente; gli interventi precedenti non determinano questa etichetta.'),
]


def record(family, split, signature, lang, state, question, gold, variant, f):
    pair='focused-v3/'+family+'/'+signature
    if question['type']=='choice':
        keys=list(question['criteria']);random.Random(signature).shuffle(keys)
        question['criteria']={k:question['criteria'][k] for k in keys}
    return {'record_id':pair+'/'+lang,'group_id':pair,'language':lang,'source_family':'focused_'+family,
            'split':split,'schema_family':'focused_v3.'+family,'request':{'state':state,'questions':{'decision':question}},
            'supervision':{'decision':{'gold':gold,'task':family}},
            'provenance':{'parallel_record':pair,'facts':f,'generator':'focused-v3','template_id':variant,'template_bank':split}}


def generate():
    seen={sha([r['supervision']['decision']['task'],r['provenance']['facts']]) for gen in (old_v1,old_v2) for rows in gen().values() for r in rows}
    out={s:[] for s in SIZES}
    rng=random.Random('focused-v3-routing-20261011')
    for split,n in SIZES.items():
        for i in range(n):
            gold=LABELS['routing'][i%4]; variant=BANKS[split][(i//4)%len(BANKS[split])]
            for _ in range(100000):
                f=facts('routing',rng);sig=sha(['routing',f])
                if sig not in seen and oracle('routing',f)==gold:break
            else:raise ValueError('No unique routing facts')
            seen.add(sig)
            for lang in ('en','it'):
                it=int(lang=='it');state,q=old_render('routing',f,lang,variant)
                order=' > '.join(q['criteria'][k] for k in f['priority'])
                q['instructions']=ROUTING[variant][it].format(order=order,minimum=f['minimum'])
                out[split].append(record('routing',split,sig,lang,state,q,gold,variant,f))
    # Train sees phrases 1/2, dev and calibration phrase 3, final test phrase 4.
    # Neither target nor distracting context can expose the held-out test phrase in training.
    used=set()
    rng=random.Random('focused-v3-intent-20261011')
    for split,n in SIZES.items():
        for i in range(n):
            target=i%len(INTENTS);variant=BANKS[split][(i//len(INTENTS))%len(BANKS[split])]
            for _ in range(100000):
                prior=rng.choice([j for j in range(len(INTENTS)) if j!=target])
                current_phrase=rng.choice((1,2)) if split=='train' else 4 if split=='test' else 3
                prior_phrase=rng.choice((1,2))
                f={'target':target,'previous':prior,'current_phrase':current_phrase,'previous_phrase':prior_phrase}
                sig=sha(['intent',f])
                if sig not in used:break
            else:raise ValueError('No unique intent configuration')
            used.add(sig)
            for lang in ('en','it'):
                it=int(lang=='it')
                state=[{'role':'user','content':INTENTS[prior][prior_phrase][it]}, {'role':'user','content':INTENTS[target][current_phrase][it]}]
                criteria={x[0][0]:x[0][1+it] for x in INTENTS}
                q={'type':'choice','instructions':INTENT_RULES[variant][it],'criteria':criteria}
                out[split].append(record('intent',split,sig,lang,state,q,INTENTS[target][0][0],variant,f))
    return out
