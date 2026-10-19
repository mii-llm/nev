"""Evaluation-contract checks, not model-accuracy tests."""
import copy
import json
from pathlib import Path
import unittest
from collections import Counter
from run_eval import score, reference_match, ordered_schemas, schema_errors
from abstract_agent.runtime import validate_call
from abstract_agent.fixtures import FixtureExecutor
from jsonschema import Draft202012Validator

DATA=json.loads((Path(__file__).parent/'suite.json').read_text())

class EvaluationTests(unittest.TestCase):
    def test_balance_and_unique_pairs(self):
        cases=DATA['cases']
        self.assertEqual(len(cases),200)
        self.assertEqual(len({c['id'] for c in cases}),200)
        self.assertEqual(Counter(c['language'] for c in cases),{'en':100,'it':100})
        self.assertEqual(Counter(c['category'] for c in cases),{'external_single':60,'confusable':40,'missing':30,'unsupported_or_direct':30,'dependent':20,'error_or_format':20})
        for pair in {c['pair_id'] for c in cases}:
            a,b=[c for c in cases if c['pair_id']==pair]
            self.assertEqual(a.get('expected_calls'),b.get('expected_calls'))
            self.assertEqual(a.get('reference'),b.get('reference'))
            for order in range(3):
                self.assertEqual([s['function']['name'] for s in ordered_schemas(a,order)],[s['function']['name'] for s in ordered_schemas(b,order)])

    def test_schemas_and_grounded_authored_plans(self):
        keys=[]
        for r in DATA['fixtures']:
            keys.append(json.dumps(r['call'],sort_keys=True))
        self.assertEqual(len(keys),len(set(keys)))
        for c in DATA['cases']:
            schemas=c['schemas'];tools={s['function']['name']:s for s in schemas}
            self.assertEqual(len(tools),len(schemas))
            for s in schemas:Draft202012Validator.check_schema(s['function']['parameters'])
            observations=[]
            for call in c.get('expected_calls',[]):
                self.assertIsNone(validate_call(call,tools,c['request'],observations),c['id'])
                result=FixtureExecutor(DATA['fixtures'])(call)
                if c['expected_behavior']!='tool_error':self.assertNotIn('error',result,c['id'])
                observations.append(result)
            if c.get('dependent'):
                self.assertEqual(validate_call(c['expected_calls'][1],tools,c['request'],[]),'argument_not_grounded',c['id'])

    def test_bfcl_optional_omission_and_strict_types(self):
        c={'reference':{'f':{'x':[3],'mode':['','all']}},'schemas':[{'function':{'name':'f','parameters':{'required':['x'],'properties':{'x':{'type':'integer'},'mode':{'type':'string','default':'all'}}}}}]}
        self.assertTrue(reference_match([{'name':'f','arguments':{'x':3}}],c))
        self.assertTrue(reference_match([{'name':'f','arguments':{'x':3,'mode':'all'}}],c))
        self.assertFalse(reference_match([{'name':'f','arguments':{'x':'3'}}],c))
        self.assertFalse(reference_match([{'name':'f','arguments':{'x':3,'extra':'all'}}],c))
        c['reference']['f']['x']=[1]
        self.assertFalse(reference_match([{'name':'f','arguments':{'x':True}}],c))

    def test_blocked_bad_call_is_not_clarification_success(self):
        c=next(c for c in DATA['cases'] if c['category']=='missing' and c['language']=='en')
        r={'final':'Which book ID should I use?','status':'answered','executed_calls':[],
           'emitted_calls':[{'name':'bad','arguments':{}}],'trace':[{'validation':[{'error':'unknown_tool'}]}]}
        s=score(c,r);self.assertFalse(s['completion_proxy']);self.assertEqual(s['blocked_calls'],1)
        r['emitted_calls']=[];r['trace']=[]
        self.assertTrue(score(c,r)['completion_proxy'])

    def test_dependency_must_use_separate_turn(self):
        c=next(c for c in DATA['cases'] if c['category']=='dependent')
        r={'final':'2 Ponente','status':'answered','executed_calls':[{'turn':0,'call':k} for k in c['expected_calls']],
           'emitted_calls':c['expected_calls'],'trace':[]}
        self.assertFalse(score(c,r)['call_correct'])
        r['executed_calls'][1]['turn']=1
        self.assertTrue(score(c,r)['completion_proxy'])

    def test_format_and_error_scores(self):
        c=next(c for c in DATA['cases'] if c['category']=='error_or_format' and 'exact_answer' in c)
        r={'final':'The date is '+c['exact_answer'],'status':'answered','executed_calls':[{'turn':0,'call':k} for k in c['expected_calls']],
           'emitted_calls':c['expected_calls'],'trace':[]}
        self.assertTrue(score(c,r)['completion_proxy']);self.assertFalse(score(c,r)['strict_completion_proxy'])
        r['final']=c['exact_answer'];self.assertTrue(score(c,r)['strict_completion_proxy'])

if __name__=='__main__':unittest.main()
