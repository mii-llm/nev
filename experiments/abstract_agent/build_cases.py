"""Author the frozen pilot before inference. Never imported by the controller."""
import copy
import json
from pathlib import Path


def call(name, **arguments):
    return {'name':name,'arguments':arguments}


def tool(name,en,it,**parameters):
    schema={'type':'object','properties':{k:({'type':'string'} if v is None else v) for k,v in parameters.items()},'required':list(parameters)}
    return {lang:{'type':'function','function':{'name':name,'description':description,'parameters':schema}} for lang,description in [('en',en),('it',it)]}


def main():
    kits={};cases=[]
    def kit(name,tools,responses):
        kits[name]={'schemas':{lang:[t[lang] for t in tools] for lang in ['en','it']},
                    'responses':[{'call':c,'result':r} for c,r in responses]}
    def pair(kit,kind,en,it,expected,anchors=(),renamed=False):
        for lang,request in [('en',en),('it',it)]:
            cases.append({'id':f'{kit}-{kind}-{lang}','toolset':kit,'kind':kind,'language':lang,
                'request':request,'expected_calls':expected,'answer_anchor_groups':anchors,'renamed':renamed})

    kit('notes',[
        tool('find_note','Find a note by its exact title and return its identifier.','Trova una nota dal titolo esatto e restituisce il suo identificativo.',query=None),
        tool('read_note','Read the content of a note using its identifier.','Leggi il contenuto di una nota usando il suo identificativo.',note_id=None),
        tool('list_notes','List note titles in a folder.','Elenca i titoli delle note in una cartella.',folder=None),
        tool('note_count','Count notes in a folder.','Conta le note in una cartella.',folder=None)],
        [(call('find_note',query='Aurora'),{'note_id':'N-7Q2','title':'Aurora'}),
         (call('read_note',note_id='N-7Q2'),{'content':'Access code: 4821'}),
         (call('read_note',note_id='N-8R6'),{'content':'Access code: 7392'}),
         (call('list_notes',folder='Work'),{'titles':['Aurora','Atlas']}),
         (call('note_count',folder='Work'),{'count':2})])
    pair('notes','single','Read note N-8R6 and tell me its access code.','Leggi la nota N-8R6 e dimmi il codice di accesso.',[call('read_note',note_id='N-8R6')],[['7392']])
    pair('notes','selection','List the note titles in folder Work.','Elenca i titoli delle note nella cartella Work.',[call('list_notes',folder='Work')],[['Aurora'],['Atlas']])
    pair('notes','dependent','Find the note titled Aurora, then read it and tell me its access code.','Trova la nota intitolata Aurora, poi leggila e dimmi il codice di accesso.',[call('find_note',query='Aurora'),call('read_note',note_id='N-7Q2')],[['4821']])
    pair('notes','parallel','List the note titles in folder Work and read note N-8R6 for its access code.','Elenca i titoli delle note nella cartella Work e leggi la nota N-8R6 per il codice di accesso.',[call('list_notes',folder='Work'),call('read_note',note_id='N-8R6')],[['Aurora'],['Atlas'],['7392']])
    pair('notes','missing','Read my note and tell me its content.','Leggi la mia nota e dimmi il contenuto.',[])
    pair('notes','unsupported','Delete note N-8R6.','Elimina la nota N-8R6.',[])
    pair('notes','no_tool','What is 2 + 3?','Quanto fa 2 + 3?',[],[['5','five','cinque']])

    unit={'type':'string','enum':['C','F']}
    kit('sensors',[
        tool('find_sensor','Find the temperature sensor in a room and return its identifier.','Trova il sensore di temperatura in una stanza e restituisce il suo identificativo.',room=None),
        tool('read_sensor','Read the current temperature from a sensor identifier.','Leggi la temperatura attuale usando un identificativo di sensore.',sensor_id=None),
        tool('convert_temperature','Convert a temperature between Celsius (C) and Fahrenheit (F).','Converti una temperatura tra Celsius (C) e Fahrenheit (F).',value={'type':'number'},from_unit=unit,to_unit=unit),
        tool('battery_status','Read the battery percentage of a device.','Leggi la percentuale della batteria di un dispositivo.',device_id=None)],
        [(call('find_sensor',room='Studio'),{'sensor_id':'S-4J9'}),
         (call('read_sensor',sensor_id='S-4J9'),{'temperature':21.5,'unit':'C'}),
         (call('read_sensor',sensor_id='S-6K3'),{'temperature':18.2,'unit':'C'}),
         (call('convert_temperature',value=20,from_unit='C',to_unit='F'),{'temperature':68,'unit':'F'}),
         (call('battery_status',device_id='D-91'),{'percent':73})])
    pair('sensors','single','Read temperature sensor S-6K3.','Leggi la temperatura del sensore S-6K3.',[call('read_sensor',sensor_id='S-6K3')],[['18.2','18,2']])
    pair('sensors','selection','Convert 20 degrees C to F.','Converti 20 gradi C in F.',[call('convert_temperature',value=20,from_unit='C',to_unit='F')],[['68']])
    pair('sensors','dependent','Find the temperature sensor in Studio, then read its temperature.','Trova il sensore di temperatura in Studio, poi leggi la sua temperatura.',[call('find_sensor',room='Studio'),call('read_sensor',sensor_id='S-4J9')],[['21.5','21,5']])
    pair('sensors','parallel','Read temperature sensor S-6K3 and the battery percentage of device D-91.','Leggi la temperatura del sensore S-6K3 e la percentuale della batteria del dispositivo D-91.',[call('read_sensor',sensor_id='S-6K3'),call('battery_status',device_id='D-91')],[['18.2','18,2'],['73']])
    pair('sensors','missing','Read the temperature from my sensor.','Leggi la temperatura dal mio sensore.',[])
    pair('sensors','unsupported','Set sensor S-6K3 to 25 degrees C.','Imposta il sensore S-6K3 a 25 gradi C.',[])
    pair('sensors','no_tool','What is 4 + 3?','Quanto fa 4 + 3?',[],[['7','seven','sette']])

    kit('media',[
        tool('search_track','Find a music track by its exact title and return its identifier.','Trova un brano dal titolo esatto e restituisce il suo identificativo.',title=None),
        tool('track_details','Read the artist and duration of a track using its identifier.','Leggi artista e durata di un brano usando il suo identificativo.',track_id=None),
        tool('playlist_tracks','List track titles in a named playlist.','Elenca i titoli dei brani in una playlist.',playlist=None),
        tool('playlist_duration','Read the total duration in seconds of a named playlist.','Leggi la durata totale in secondi di una playlist.',playlist=None)],
        [(call('search_track',title='Aster'),{'track_id':'T-3V8'}),
         (call('track_details',track_id='T-3V8'),{'artist':'Mira','duration_seconds':187}),
         (call('track_details',track_id='T-9W2'),{'artist':'Elio','duration_seconds':204}),
         (call('playlist_tracks',playlist='Focus'),{'titles':['Aster','Lumen']}),
         (call('playlist_duration',playlist='Focus'),{'duration_seconds':391})])
    pair('media','single','Get the artist and duration in seconds of track T-9W2.','Dimmi artista e durata in secondi del brano T-9W2.',[call('track_details',track_id='T-9W2')],[['Elio'],['204']])
    pair('media','selection','List the track titles in playlist Focus.','Elenca i titoli dei brani nella playlist Focus.',[call('playlist_tracks',playlist='Focus')],[['Aster'],['Lumen']])
    pair('media','dependent','Find the track titled Aster, then get its artist and duration in seconds.','Trova il brano intitolato Aster, poi dimmi artista e durata in secondi.',[call('search_track',title='Aster'),call('track_details',track_id='T-3V8')],[['Mira'],['187']])
    pair('media','parallel','List the track titles in playlist Focus and get the artist and duration in seconds of track T-9W2.','Elenca i titoli dei brani nella playlist Focus e dimmi artista e durata in secondi del brano T-9W2.',[call('playlist_tracks',playlist='Focus'),call('track_details',track_id='T-9W2')],[['Aster'],['Lumen'],['Elio'],['204']])
    pair('media','missing','Get the artist and duration of my track.','Dimmi artista e durata del mio brano.',[])
    pair('media','unsupported','Delete playlist Focus.','Elimina la playlist Focus.',[])
    pair('media','no_tool','What is 5 + 4?','Quanto fa 5 + 4?',[],[['9','nine','nove']])

    # Identical tasks with opaque tool names: descriptions and parameter names remain informative.
    for name in list(kits):
        original=kits[name];renamed=copy.deepcopy(original)
        aliases={s['function']['name']:alias for s,alias in zip(original['schemas']['en'],['tool_a7','tool_b2','tool_c9','tool_d4'])}
        for schemas in renamed['schemas'].values():
            for s in schemas:s['function']['name']=aliases[s['function']['name']]
        for r in renamed['responses']:r['call']['name']=aliases[r['call']['name']]
        kits[name+'_renamed']=renamed
        for c in list(cases):
            if c['toolset']!=name or c['kind'] not in ('single','dependent'):continue
            c=copy.deepcopy(c);c['id']=c['id'].replace(name,name+'_renamed',1);c['toolset']=name+'_renamed';c['renamed']=True
            for expected in c['expected_calls']:expected['name']=aliases[expected['name']]
            cases.append(c)
    root=Path(__file__).parent
    (root/'toolsets.json').write_text(json.dumps(kits,ensure_ascii=False,indent=2)+'\n')
    (root/'cases.json').write_text(json.dumps({'scope':'54 authored paired requests; 27 EN/27 IT; freeze before inference; not a held-out public benchmark. No case labels or expected plans are passed to the runtime.','cases':cases},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
