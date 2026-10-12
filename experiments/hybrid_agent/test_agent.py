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

if __name__=='__main__': unittest.main()
