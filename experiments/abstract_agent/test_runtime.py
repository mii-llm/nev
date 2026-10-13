import json
from pathlib import Path
import unittest
from fixtures import FixtureExecutor
from runtime import GenericAgent,parse_calls,validate_call
from run_eval import score


ROOT=Path(__file__).parent
KITS=json.loads((ROOT/'toolsets.json').read_text())
CASES=json.loads((ROOT/'cases.json').read_text())['cases']


class ScriptedBackend:
    def __init__(self,outputs,choice=None):self.outputs=iter(outputs);self.choice=choice
    def synchronize(self):pass
    def generate(self,messages):return next(self.outputs),12,False
    def rank(self,request,language,tools,executed,observations,gate):
        names=[s['function']['name'] for s in tools]
        return {'choice':self.choice or names[0],'probabilities':{n:1/len(names) for n in names},'elapsed_ms':0}


def emit(name,**args):return '<tool_call>'+json.dumps({'name':name,'arguments':args})+'</tool_call>'


class RuntimeTests(unittest.TestCase):
    def test_frozen_fixtures_are_valid_and_balanced(self):
        self.assertEqual(len(CASES),54)
        self.assertEqual(sum(c['language']=='it' for c in CASES),27)
        for c in CASES:
            kit=KITS[c['toolset']];tools={s['function']['name']:s for s in kit['schemas'][c['language']]};observations=[]
            for call in c['expected_calls']:
                self.assertIsNone(validate_call(call,tools,c['request'],observations),c['id'])
                result=FixtureExecutor(kit['responses'])(call);self.assertNotIn('error',result,c['id']);observations.append(result)

    def test_dependency_needs_previous_result(self):
        tools={s['function']['name']:s for s in KITS['notes']['schemas']['en']}
        c={'name':'read_note','arguments':{'note_id':'N-7Q2'}}
        self.assertEqual(validate_call(c,tools,'Find Aurora.',[]),'argument_not_grounded')
        self.assertIsNone(validate_call(c,tools,'Find Aurora.',[{'note_id':'N-7Q2'}]))

    def test_strict_schema_and_markup(self):
        tools={s['function']['name']:s for s in KITS['notes']['schemas']['en']}
        for args in [{},{'note_id':2},{'note_id':'N-7Q2','extra':'x'}]:
            self.assertEqual(validate_call({'name':'read_note','arguments':args},tools,'N-7Q2 x',[]),'schema_violation')
        for raw in ['<tool_call>{broken}</tool_call>','Sure! '+emit('read_note',note_id='N-7Q2'),'<tool_call>{}']:
            self.assertIsNotNone(parse_calls(raw)[1])

    def test_atomic_batch_rejection_then_repair(self):
        kit=KITS['notes'];seen=[]
        backend=ScriptedBackend([emit('read_note',note_id='N-8R6')+emit('read_note',note_id='invented'),emit('read_note',note_id='N-8R6'),'7392'])
        def execute(c):seen.append(c);return FixtureExecutor(kit['responses'])(c)
        r=GenericAgent(backend).run('Read N-8R6.','en',kit['schemas']['en'],execute,'nesso_only',1)
        self.assertEqual(len(seen),1);self.assertEqual(r['executed_calls'][0]['turn'],1)
        self.assertIn('argument_not_grounded',r['errors'])

    def test_duplicate_cache_avoids_reexecution(self):
        kit=KITS['notes'];c=emit('read_note',note_id='N-8R6')
        r=GenericAgent(ScriptedBackend([c,c,'7392'])).run('Read N-8R6.','en',kit['schemas']['en'],FixtureExecutor(kit['responses']),'nesso_only',1)
        self.assertEqual(len(r['executed_calls']),1);self.assertTrue(r['trace'][1]['observations'][0]['cached'])

    def test_gate_blocks_without_fake_answer(self):
        kit=KITS['notes']
        r=GenericAgent(ScriptedBackend([emit('read_note',note_id='N-8R6')],'__unsupported__')).run('Delete N-8R6.','en',kit['schemas']['en'],FixtureExecutor(kit['responses']),'nev_gated',1)
        self.assertEqual(r['executed_calls'],[]);self.assertEqual(r['final'],'');self.assertEqual(r['status'],'blocked_by_nev')

    def test_real_dependency_and_score(self):
        c=next(c for c in CASES if c['id']=='notes-dependent-en');kit=KITS['notes']
        r=GenericAgent(ScriptedBackend([emit('find_note',query='Aurora'),emit('read_note',note_id='N-7Q2'),'The code is 4821.'])).run(c['request'],'en',kit['schemas']['en'],FixtureExecutor(kit['responses']),'nesso_only',1)
        self.assertTrue(score(c,r)['completion_proxy'])
        r['executed_calls'][1]['turn']=0
        self.assertFalse(score(c,r)['executed_calls_exact'])

if __name__=='__main__':unittest.main()
