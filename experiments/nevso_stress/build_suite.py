"""Build the frozen 100-pair test; no model calls or output-dependent selection."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANSLATIONS = [
"Trova brani di Cody Johnson del 2019 dall'album 'Gotta Be Me'.",
"Puoi darmi le previsioni meteo per Chicago, IL per l'8 marzo 2023?",
"Puoi aiutarmi a trovare eventi musicali a Livermore, CA il 6 marzo 2023?",
"Vorrei ascoltare una canzone popolare di Phan Dinh Tung dall'album Hat Nhan in cucina.",
"Ci sono film di animazione in formato imax a Union City?",
"Trova un evento musicale a New York il 25 marzo 2023. Oggi è il 15 marzo.",
"Trova monumenti storici a Paris adatti ai bambini e con ingresso gratuito.",
"Mi serve aiuto per trovare un terapista familiare a Mountain View.",
"Voglio il badge delle violazioni per il progetto bandana. La versione è 5.",
"Puoi trovare eventi musicali a Seattle, WA l'11 marzo? L'anno è il 2023.",
"Devo vedere tutti i mandati associati al nostro partner, indipendentemente dal loro stato.",
"Devo ripristinare le impostazioni predefinite degli avvisi dell'app mobile con ID di configurazione 'sl8'. La configurazione è stata creata il 2023-04-01T10:00:00Z.",
"Recupera tutti i SIP attivi di tutti i clienti di un partner.",
"Trova le previsioni meteo per Antioch, CA per mercoledì prossimo, precisamente il 2023-10-1.",
"Puoi cercare film in programmazione a Fremont, CA al cinema Century at Pacific Commons and XD? Mi interessano i generi Sci-fi e Action.",
"Puoi dirmi il prezzo attuale di un articolo 'winter jacket' a Berkeley, CA?",
"Rinomina il sito web 'Frank' in 'Bob'. L'ID del sito è 1234.",
"Puoi trovare film di genere Anime diretti da Satoshi Kon con Akiko Kawase nel cast?",
"Puoi darmi i dettagli del tirocinio di Adriel presso la sebelas maret university?",
"Trova hotel disponibili a Phoenix, AZ.",
"Puoi cercarmi un hotel a Delhi, India?",
"Ho voglia di musica dall'album This Is Acting e mi piace molto Sia. Puoi trovare brani di quell'album e di quell'artista? Vorrei anche ascoltare canzoni di genere Pop.",
"Voglio andare a Sydney, Australia e mi serve un alloggio per tre persone con servizio lavanderia.",
"Quale versione?",
"Trova un parrucchiere a Walnut Creek, CA disponibile il 5 marzo 2023 alle 2 del pomeriggio.",
"Trova treni in partenza da Phoenix, AZ per Los Angeles il 25 aprile 2023.",
"Chi è ji sung park?",
"Devo inviare privatamente 50 dollari al mio amico Jamie usando la mia carta di debito.",
"Puoi trovare un elenco di parchi a New York con ingresso gratuito e adatti ai bambini?",
"Segmenta tutti gli oggetti nell'immagine './yoha.jpg'.",
]


def tool(name, en, it, arg):
    def schema(desc):
        return {'type':'function','function':{'name':name,'description':desc,
            'parameters':{'type':'object','properties':{arg:{'type':'string'}},'required':[arg],'additionalProperties':False}}}
    return {'en':schema(en),'it':schema(it)}


def call(name, arg, value):
    return {'name':name,'arguments':{arg:value}}


# Local fictional facts, not real accounts or services. Six tools per domain.
DOMAINS = {
'library': [
 ('find_book','Find a book identifier by its title.','Trova il codice di un libro dal titolo.','title'),
 ('get_book_availability','Read available copies and branch for a book.','Leggi copie disponibili e sede per un libro.','book_id'),
 ('get_book_author','Read the author of a book.','Leggi l’autore di un libro.','book_id'),
 ('get_loan_due_date','Read the due date of a library loan.','Leggi la data di scadenza di un prestito bibliotecario.','loan_id'),
 ('get_branch_hours','Read the opening hours of a library branch.','Leggi gli orari di apertura di una sede bibliotecaria.','branch_id'),
 ('get_book_page_count','Read the number of pages in a book.','Leggi il numero di pagine di un libro.','book_id')],
'parcel': [
 ('find_shipment','Find a shipment identifier from an order reference.','Trova il codice spedizione dal riferimento ordine.','reference'),
 ('get_shipment_status','Read the current delivery status of a shipment.','Leggi lo stato attuale di consegna di una spedizione.','shipment_id'),
 ('get_shipment_location','Read the current depot location of a shipment.','Leggi il deposito in cui si trova una spedizione.','shipment_id'),
 ('get_delivery_date','Read the scheduled delivery date of a shipment.','Leggi la data prevista di consegna di una spedizione.','shipment_id'),
 ('get_parcel_weight','Read the parcel weight in kilograms.','Leggi il peso del pacco in chilogrammi.','shipment_id'),
 ('get_pickup_hours','Read the opening hours of a pickup point.','Leggi gli orari di apertura di un punto di ritiro.','point_id')],
'museum': [
 ('find_exhibit','Find an exhibit identifier by its title.','Trova il codice di un’opera dal suo titolo.','title'),
 ('get_exhibit_location','Read the room containing an exhibit.','Leggi la sala in cui si trova un’opera.','exhibit_id'),
 ('get_exhibit_artist','Read the artist who created an exhibit.','Leggi l’artista che ha creato un’opera.','exhibit_id'),
 ('get_exhibit_end_date','Read the final display date of an exhibit.','Leggi la data finale di esposizione di un’opera.','exhibit_id'),
 ('get_ticket_price','Read the ticket price in euros for a ticket category.','Leggi il prezzo in euro del biglietto per una categoria.','ticket_type'),
 ('get_museum_hours','Read the museum opening hours.','Leggi gli orari di apertura del museo.','museum_id')],
'bicycle': [
 ('find_station','Find a bicycle station identifier by its name.','Trova il codice di una stazione biciclette dal nome.','name'),
 ('get_available_bikes','Read the number of bicycles available at a station.','Leggi il numero di biciclette disponibili in una stazione.','station_id'),
 ('get_empty_docks','Read the number of empty return docks at a station.','Leggi il numero di posti liberi per restituire biciclette in una stazione.','station_id'),
 ('get_station_service_date','Read the date of the next station maintenance.','Leggi la data della prossima manutenzione della stazione.','station_id'),
 ('get_bike_battery','Read the battery charge percentage of a bicycle.','Leggi la percentuale di carica della batteria di una bicicletta.','bike_id'),
 ('get_station_address','Read the street address of a bicycle station.','Leggi l’indirizzo stradale di una stazione biciclette.','station_id')],
'lab': [
 ('find_sample','Find a laboratory sample identifier by its label.','Trova il codice di un campione di laboratorio dalla sua etichetta.','label'),
 ('get_sample_temperature','Read sample temperature in degrees Celsius.','Leggi la temperatura del campione in gradi Celsius.','sample_id'),
 ('get_sample_ph','Read the pH of a laboratory sample.','Leggi il pH di un campione di laboratorio.','sample_id'),
 ('get_analysis_due_date','Read the scheduled analysis completion date.','Leggi la data prevista di completamento dell’analisi.','sample_id'),
 ('get_sample_volume','Read sample volume in millilitres.','Leggi il volume del campione in millilitri.','sample_id'),
 ('get_instrument_status','Read the operational status of a laboratory instrument.','Leggi lo stato operativo di uno strumento di laboratorio.','instrument_id')]
}

# Four distinct contrast requests per domain: (tool index, value, EN, IT, result, answer alternatives).
CONTRAST = {
'library': [
 (1,'BK-471',"For BK-471, I need available copies and the branch, not its author.","Per BK-471 mi servono le copie disponibili e la sede, non l’autore.",{'copies':3,'branch':'Levante'},[['3','three','tre'],['Levante']]),
 (2,'BK-582',"Who wrote BK-582? I already know it is available.","Chi ha scritto BK-582? So già che è disponibile.",{'author':'Ada Neri'},[['Ada Neri']]),
 (5,'BK-693',"How long is BK-693 in pages? Do not look up the loan deadline.","Quante pagine ha BK-693? Non cercare la scadenza del prestito.",{'pages':248},[['248']]),
 (4,'BR-704',"I want to visit branch BR-704. When does it open and close?","Voglio andare alla sede BR-704. A che ora apre e chiude?",{'opens':'09:15','closes':'17:45'},[['09:15','9:15'],['17:45']])],
'parcel': [
 (2,'SH-481',"Where is SH-481 physically now? I do not need the delivery date.","Dove si trova fisicamente SH-481 adesso? Non mi serve la data di consegna.",{'depot':'Deposito Iris'},[['Iris']]),
 (1,'SH-592',"Has SH-592 arrived? Tell me its delivery status, not its weight.","SH-592 è arrivata? Dimmi lo stato della consegna, non il peso.",{'status':'delivered','status_it':'consegnato'},[['delivered','consegnat']]),
 (4,'SH-603',"What does SH-603 weigh in kilograms? I know where it is.","Quanto pesa SH-603 in chilogrammi? So già dove si trova.",{'weight_kg':2.7},[['2.7','2,7'],['kg','kilogram','chilogram']]),
 (5,'PT-714',"When can I collect a parcel at PT-714? Give the opening hours.","Quando posso ritirare un pacco a PT-714? Dammi gli orari di apertura.",{'opens':'08:30','closes':'19:00'},[['08:30','8:30'],['19:00']])],
'museum': [
 (1,'EX-491',"Which room contains EX-491? I do not need the artist’s name.","In quale sala si trova EX-491? Non mi serve il nome dell’artista.",{'room':'Sala Ambra'},[['Ambra']]),
 (2,'EX-502',"Who created EX-502? Please do not give directions to its room.","Chi ha creato EX-502? Non darmi indicazioni per la sala.",{'artist':'Lia Vanni'},[['Lia Vanni']]),
 (4,'adult',"How much is an 'adult' ticket in euros? Not the opening hours.","Quanto costa in euro un biglietto 'adult'? Non gli orari di apertura.",{'price_eur':14},[['14'],['eur','€']]),
 (5,'MU-724',"I am planning a visit to MU-724. Give its opening and closing times.","Sto organizzando una visita a MU-724. Dammi l’orario di apertura e chiusura.",{'opens':'10:00','closes':'18:30'},[['10:00'],['18:30']])],
'bicycle': [
 (2,'ST-511',"I need to return a bicycle at ST-511. How many empty docks are there?","Devo restituire una bicicletta a ST-511. Quanti posti liberi ci sono?",{'empty_docks':7},[['7','seven','sette']]),
 (1,'ST-622',"I want to borrow a bicycle at ST-622. How many bikes can I take?","Voglio prendere una bicicletta a ST-622. Quante biciclette sono disponibili?",{'available_bikes':4},[['4','four','quattro']]),
 (4,'BI-733',"What percentage of charge remains on BI-733? Not the number of bikes.","Quale percentuale di carica rimane su BI-733? Non il numero di biciclette.",{'battery_percent':62},[['62'],['%','percent','per cento']]),
 (5,'ST-844',"I know ST-844 has bikes. What is its street address?","So che ST-844 ha biciclette. Qual è il suo indirizzo?",{'address':'Via Olmo 27'},[['Via Olmo 27']])],
'lab': [
 (2,'SA-521',"Read the acidity of SA-521 as pH, not its temperature.","Leggi l’acidità di SA-521 come pH, non la temperatura.",{'ph':6.8},[['6.8','6,8'],['ph']]),
 (1,'SA-632',"How hot is SA-632 in Celsius? The volume is irrelevant.","Qual è la temperatura di SA-632 in Celsius? Il volume non è rilevante.",{'temperature_c':21.4},[['21.4','21,4'],['celsius','°c']]),
 (4,'SA-743',"How many millilitres are in SA-743? Do not report its pH.","Quanti millilitri contiene SA-743? Non riportare il pH.",{'volume_ml':85},[['85'],['ml','millilit']]),
 (5,'IN-854',"Is instrument IN-854 operational? I am not asking about a sample.","Lo strumento IN-854 è operativo? Non sto chiedendo informazioni su un campione.",{'status':'offline','status_it':'non operativo'},[['offline','non operativo']])]
}
MISSING = {
'library':[(1,'How many copies of the book are available?','Quante copie del libro sono disponibili?',['book','libro','codice','id']), (3,'When must I return my library loan?','Quando devo restituire il mio prestito bibliotecario?',['loan','prestito','codice','id']), (4,'What time does the library branch close?','A che ora chiude la sede della biblioteca?',['branch','sede','codice','id'])],
'parcel':[(1,'Has my shipment been delivered?','La mia spedizione è stata consegnata?',['shipment','spedizione','codice','id']), (4,'What is the weight of my parcel?','Qual è il peso del mio pacco?',['parcel','pacco','spedizione','codice','id']), (5,'When does my pickup point open?','A che ora apre il mio punto di ritiro?',['point','punto','codice','id'])],
'museum':[(1,'Which room contains the exhibit?','In quale sala si trova l’opera?',['exhibit','opera','codice','id']), (4,'How much is a museum ticket?','Quanto costa un biglietto del museo?',['type','category','tipo','categoria']), (5,'When does the museum close?','A che ora chiude il museo?',['museum','museo','codice','id'])],
'bicycle':[(1,'How many bicycles are available at the station?','Quante biciclette sono disponibili alla stazione?',['station','stazione','codice','id']), (4,'How much charge does the bicycle have?','Quanta carica ha la bicicletta?',['bike','bicycle','bicicletta','codice','id']), (2,'Are there empty docks where I can return this bike?','Ci sono posti liberi dove posso restituire questa bicicletta?',['station','stazione','codice','id'])],
'lab':[(2,'What is the pH of my sample?','Qual è il pH del mio campione?',['sample','campione','codice','id']), (1,'Read the temperature of the sample.','Leggi la temperatura del campione.',['sample','campione','codice','id']), (5,'Is the instrument online?','Lo strumento è online?',['instrument','strumento','codice','id'])]
}
UNSUPPORTED = {
'library':[("Reserve book BK-915 for me.","Prenota per me il libro BK-915."),("Delete loan LN-926 from my account.","Elimina il prestito LN-926 dal mio account.")],
'parcel':[("Redirect shipment SH-915 to Via Pino 12.","Reindirizza la spedizione SH-915 a Via Pino 12."),("Cancel shipment SH-926.","Annulla la spedizione SH-926.")],
'museum':[("Buy 2 adult museum tickets.","Compra 2 biglietti adulti per il museo."),("Move exhibit EX-926 to Sala Blu.","Sposta l’opera EX-926 nella Sala Blu.")],
'bicycle':[("Unlock bicycle BI-915.","Sblocca la bicicletta BI-915."),("Reserve a bicycle at station ST-926.","Prenota una bicicletta alla stazione ST-926.")],
'lab':[("Set instrument IN-915 to 40 degrees Celsius.","Imposta lo strumento IN-915 a 40 gradi Celsius."),("Delete laboratory sample SA-926.","Elimina il campione di laboratorio SA-926.")]
}
# Query -> identifier -> read; the identifier is never in the user request.
DEPENDENT = {
'library':('Atlante delle nuvole','BK-801',[(1,{'copies':2,'branch':'Ponente'},[['2','two','due'],['Ponente']],"Find the book titled 'Atlante delle nuvole', then tell me its available copies and branch.","Cerca il libro intitolato 'Atlante delle nuvole', poi dimmi le copie disponibili e la sede."),(2,{'author':'Elio Mori'},[['Elio Mori']],"Find the book titled 'Atlante delle nuvole' and tell me its author.","Cerca il libro intitolato 'Atlante delle nuvole' e dimmi chi è l’autore.")]),
'parcel':('ORD-802','SH-817',[(1,{'status':'in transit','status_it':'in transito'},[['in transit','in transito']],"Find the shipment for order ORD-802, then tell me its delivery status.","Trova la spedizione dell’ordine ORD-802, poi dimmi lo stato della consegna."),(2,{'depot':'Deposito Viola'},[['Viola']],"Find the shipment for order ORD-802 and tell me its current depot.","Trova la spedizione dell’ordine ORD-802 e dimmi in quale deposito si trova.")]),
'museum':('Luce sul porto','EX-823',[(1,{'room':'Sala Corallo'},[['Corallo']],"Find the exhibit titled 'Luce sul porto', then tell me its room.","Cerca l’opera intitolata 'Luce sul porto', poi dimmi in quale sala si trova."),(2,{'artist':'Nora Fabbri'},[['Nora Fabbri']],"Find the exhibit titled 'Luce sul porto' and tell me who created it.","Cerca l’opera intitolata 'Luce sul porto' e dimmi chi l’ha creata.")]),
'bicycle':('Porta Verde','ST-839',[(1,{'available_bikes':9},[['9','nine','nove']],"Find the station named 'Porta Verde', then tell me how many bicycles are available.","Cerca la stazione chiamata 'Porta Verde', poi dimmi quante biciclette sono disponibili."),(2,{'empty_docks':6},[['6','six','sei']],"Find the station named 'Porta Verde' and tell me how many empty return docks it has.","Cerca la stazione chiamata 'Porta Verde' e dimmi quanti posti liberi ha per la restituzione.")]),
'lab':('Acqua Fonte','SA-847',[(1,{'temperature_c':18.6},[['18.6','18,6'],['celsius','°c']],"Find the sample labelled 'Acqua Fonte', then read its temperature in Celsius.","Cerca il campione etichettato 'Acqua Fonte', poi leggine la temperatura in Celsius."),(2,{'ph':7.3},[['7.3','7,3'],['ph']],"Find the sample labelled 'Acqua Fonte' and read its pH.","Cerca il campione etichettato 'Acqua Fonte' e leggine il pH.")])
}
DATE_REQUESTS = {
'library':('LN-967','Read the due date for loan LN-967. Reply only with the date in YYYY-MM-DD format.','Leggi la scadenza del prestito LN-967. Rispondi solo con la data nel formato YYYY-MM-DD.'),
'parcel':('SH-967','Read the scheduled delivery date for SH-967. Reply only with the date in YYYY-MM-DD format.','Leggi la data prevista di consegna di SH-967. Rispondi solo con la data nel formato YYYY-MM-DD.'),
'museum':('EX-967','Read the last display date for EX-967. Reply only with the date in YYYY-MM-DD format.','Leggi la data finale di esposizione di EX-967. Rispondi solo con la data nel formato YYYY-MM-DD.'),
'bicycle':('ST-967','Read the next maintenance date for ST-967. Reply only with the date in YYYY-MM-DD format.','Leggi la data della prossima manutenzione di ST-967. Rispondi solo con la data nel formato YYYY-MM-DD.'),
'lab':('SA-967','Read the analysis completion date for SA-967. Reply only with the date in YYYY-MM-DD format.','Leggi la data di completamento dell’analisi di SA-967. Rispondi solo con la data nel formato YYYY-MM-DD.')}


def normalize(value):
    if isinstance(value,list): return [normalize(v) for v in value]
    if not isinstance(value,dict): return value
    out={k:normalize(v) for k,v in value.items()}
    if out.get('type')=='dict': out['type']='object'
    if out.get('type')=='float': out['type']='number'
    return out


def build():
    cases=[];kits={};fixtures=[]
    for domain,defs in DOMAINS.items():
        kits[domain]=[tool(*d) for d in defs]
    def add(domain,category,index,en,it,expected,kind='answer',anchors=None,extra=None):
        # Six in-domain tools + six fixed out-of-domain distractors. Selection is input-only.
        others=[t for d,ts in kits.items() if d!=domain for t in ts][:6]
        schemas={lang:[t[lang] for t in kits[domain]+others] for lang in ['en','it']}
        pair=f'{domain}-{category}-{index}'
        for lang,request in [('en',en),('it',it)]:
            cases.append({'id':pair+'-'+lang,'pair_id':pair,'language':lang,'category':category,
                'source':'authored','domain':domain,'request':request,'schemas':schemas[lang],
                'expected_calls':copy.deepcopy(expected),'expected_behavior':kind,
                'answer_anchor_groups':anchors or [],**(extra or {})})
    def mk(domain,idx,value):
        name,_,_,arg=DOMAINS[domain][idx]
        return call(name,arg,value)
    def fixture(c,result):
        item={'call':c,'result':result}
        if item not in fixtures: fixtures.append(item)
    for d in DOMAINS:
        for j,(idx,value,en,it,result,anchors) in enumerate(CONTRAST[d]):
            c=mk(d,idx,value);fixture(c,result)
            add(d,'confusable',j,en,it,[c],anchors=anchors)
        for j,(idx,en,it,concepts) in enumerate(MISSING[d]):
            add(d,'missing',j,en,it,[],kind='clarify',extra={'clarification_concepts':concepts})
        for j,(en,it) in enumerate(UNSUPPORTED[d]):
            add(d,'unsupported_or_direct',j,en,it,[],kind='unsupported')
        # Direct answer with distracting catalog; no lookup is necessary.
        color=['ambra','viola','corallo','verde','blu'][list(DOMAINS).index(d)]
        add(d,'unsupported_or_direct',2,f"The label is '{color}'. Repeat only that label; do not look anything up.",
            f"L’etichetta è '{color}'. Ripeti solo l’etichetta; non cercare informazioni.",[],kind='direct',anchors=[[color]],extra={'exact_answer':color})
        query,identifier,items=DEPENDENT[d]
        first=mk(d,0,query)
        key=DOMAINS[d][1][3]
        fixture(first,{key:identifier})
        for j,(idx,result,anchors,en,it) in enumerate(items):
            second=mk(d,idx,identifier);fixture(second,result)
            add(d,'dependent',j,en,it,[first,second],anchors=anchors,extra={'dependent':True})
        # One permanent missing-record failure, never fabricated readings.
        original=CONTRAST[d][0]
        idx,oldid,en,it,_,_=original
        newid=oldid.split('-')[0]+'-000'
        c=mk(d,idx,newid);fixture(c,{'error':'not_found','message':'No matching record exists.'})
        add(d,'error_or_format',0,en.replace(oldid,newid),it.replace(oldid,newid),[c],kind='tool_error')
        value,en,it=DATE_REQUESTS[d];c=mk(d,3,value)
        date='2027-02-'+str(11+list(DOMAINS).index(d))
        fixture(c,{'date':date})
        add(d,'error_or_format',1,en,it,[c],anchors=[[date]],extra={'exact_answer':date})
    source=json.loads((ROOT/'source/bfcl_selected.json').read_text())
    assert len(source)==len(TRANSLATIONS)==30
    for i,(item,it) in enumerate(zip(source,TRANSLATIONS)):
        x=item['source'];pair='bfcl-'+x['id']
        for lang,request in [('en',x['question'][0][0]['content']),('it',it)]:
            cases.append({'id':pair+'-'+lang,'pair_id':pair,'language':lang,'category':'external_single',
                'source':'bfcl_adapted','domain':x['id'],'request':request,
                'schemas':[{'type':'function','function':normalize(f)} for f in x['function']],
                'reference':item['answer']['ground_truth'][0], 'expected_behavior':'call_only',
                'quality_flag':'weekday_date_conflict' if x['id']=='live_multiple_808-175-14' else None})
    result={'version':1,'scope':'200 requests (100 EN/IT pairs), 30 BFCL-derived pairs and 70 authored workflow pairs. Development evaluation, not an official BFCL score or contamination-free benchmark.',
        'orders':[0,1,2],'arms':['nesso_only','nev_ranked','nev_selected'],
        'fixtures':fixtures,'cases':cases}
    assert len(cases)==200
    return result

if __name__=='__main__':
    p=ROOT/'suite.json'
    if p.exists():raise SystemExit('Suite already exists. Preserve the frozen test; use a versioned directory for changes.')
    p.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n')
    print(p)
