"""CPU-only checks of the mock execution boundary and pilot scoring."""
import unittest
from agent import parse_calls, validate_call, mock_tool, TOOL_DATA, schemas
from run_pilot import score

class BoundaryTests(unittest.TestCase):
    def test_compact_schemas_change_display_only(self):
        compact=schemas('en','compact')
        self.assertNotIn('pattern',str(compact))
        self.assertNotIn('additionalProperties',str(compact))
        self.assertEqual([x['function']['name'] for x in compact],list(TOOL_DATA))
        self.assertEqual(validate_call({'name':'get_order_status','arguments':{'order_id':'invented'}},list(TOOL_DATA),'invented'),'invalid_argument_value')
    def test_call_parser_rejects_mixed_and_malformed_content(self):
        call={'name':'get_invoice','arguments':{'order_id':'ORD-6101'}}
        import json
        block='<tool_call>'+json.dumps(call)+'</tool_call>'
        self.assertEqual(parse_calls(block),([call],None))
        self.assertIsNotNone(parse_calls('Already sent! '+block)[1])
        self.assertIsNotNone(parse_calls('<tool_call>{bad}</tool_call>')[1])
        self.assertIsNotNone(parse_calls('<tool_call>')[1])
    def test_unknown_and_ungrounded_calls_never_pass(self):
        c={'name':'get_invoice','arguments':{'order_id':'ORD-6101'}}
        self.assertIsNone(validate_call(c,list(TOOL_DATA),'Invoice for ORD-6101'))
        self.assertEqual(validate_call(c,['get_order_status'],'Invoice for ORD-6101'),'function_not_available')
        self.assertEqual(validate_call(c,list(TOOL_DATA),'Please get my invoice'),'argument_not_grounded_in_request')
        self.assertEqual(validate_call(c,list(TOOL_DATA),'ORD-61011'),'argument_not_grounded_in_request')
        self.assertEqual(validate_call({'name':'send_email','arguments':{}},list(TOOL_DATA),''),'function_not_available')
        c['arguments']['unexpected']='anything'
        self.assertEqual(validate_call(c,list(TOOL_DATA),'ORD-6101'),'wrong_arguments')
    def test_two_step_requires_distinct_turns_and_observation_anchor(self):
        calls=[{'name':'get_order_status','arguments':{'order_id':'ORD-6101'}},
               {'name':'get_invoice','arguments':{'order_id':'ORD-6101'}}]
        case={'category':'two_step','expected_calls':calls,'answer_anchor_groups':[['TRK-ORD-6101'],['invoice_ORD-6101.pdf']]}
        r={'emitted_calls':calls,'trace':[],'executed_calls':[{'turn':0,'call':c} for c in calls],
           'final':'TRK-ORD-6101 invoice_ORD-6101.pdf','available_tools':list(TOOL_DATA),'errors':[],'truncated':False}
        self.assertFalse(score(case,r)['strict_mechanical_pass'])
        r['executed_calls'][1]['turn']=1
        self.assertTrue(score(case,r)['strict_mechanical_pass'])
        r['final']='Your order is ready.'
        self.assertFalse(score(case,r)['strict_mechanical_pass'])
    def test_mock_returns_explicit_fixture(self):
        self.assertEqual(mock_tool({'name':'get_invoice','arguments':{'order_id':'ORD-6101'}}),
                         {'order_id':'ORD-6101','filename':'invoice_ORD-6101.pdf'})


class SingleReadTests(unittest.TestCase):
    def run_response(self, text, message='Invoice for ORD-8123', top='get_invoice', truncated=False):
        from types import SimpleNamespace
        from agent import HybridAgent
        agent=HybridAgent.__new__(HybridAgent)
        agent.torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None))
        agent.schema_style='compact'
        agent.generate=lambda messages:(text,10,truncated)
        ranking={'names':[top]+[n for n in TOOL_DATA if n!=top], 'elapsed_ms':0}
        return agent.run(message,'en','nev_ranked',ranking,policy='single_read')

    def block(self, name='get_invoice', **args):
        import json
        return '<tool_call>'+json.dumps({'name':name,'arguments':args})+'</tool_call>'

    def test_duplicate_executes_once_and_invalid_extra_never_executes(self):
        good=self.block(order_id='ORD-8123')
        r=self.run_response(good+good+self.block('get_order_status',order_id='12345'))
        self.assertEqual(len(r['executed_calls']),1)
        self.assertEqual(len(r['emitted_calls']),3)
        self.assertEqual(r['answer_source'],'application_template')
        self.assertIn('invoice_ORD-8123.pdf',r['final'])
        self.assertEqual(r['errors'],['duplicate_call','invalid_argument_value'])

    def test_disagreement_multiple_calls_and_references_defer(self):
        good=self.block(order_id='ORD-8123')
        candidates=[self.run_response(good,top='get_order_status'),
            self.run_response(good+self.block('get_order_status',order_id='ORD-8123')),
            self.run_response(good,message='Invoice for ORD-8123 or ORD-8124')]
        for r in candidates:
            self.assertEqual(r['executed_calls'],[])
            self.assertEqual(r['answer_source'],'application_deferral')
            self.assertTrue(r['blocked_reason'])

    def test_malformed_ungrounded_truncated_and_no_call_defer(self):
        candidates=[self.run_response('<tool_call>{bad}</tool_call>'),
            self.run_response(self.block(order_id='ORD-9999')),
            self.run_response(self.block(order_id='ORD-8123'),truncated=True),
            self.run_response('The invoice is paid.')]
        for r in candidates:
            self.assertEqual(r['executed_calls'],[])
            self.assertEqual(r['answer_source'],'application_deferral')
            self.assertNotIn('paid',r['final'])

    def test_renderer_uses_actual_observation_including_all_payments(self):
        from single_read import render_result
        observation={'month':'2026-11','currency':'GBP','payments':[1.25,8.50],'total':9.75}
        en=render_result('list_transactions',observation,'en')
        it=render_result('list_transactions',observation,'it')
        self.assertIn('1.25 GBP, 8.50 GBP',en)
        self.assertIn('9.75 GBP',en)
        self.assertIn('1,25 GBP, 8,50 GBP',it)
        self.assertIn('9,75 GBP',it)
        self.assertNotIn('63.75',en)

if __name__=='__main__': unittest.main()
