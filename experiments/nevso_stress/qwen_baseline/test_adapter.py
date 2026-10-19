import json
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).parent))
from backend import native_messages

class AdapterTests(unittest.TestCase):
    def envelope(self):
        schema=[{'type':'function','function':{'name':'lookup','description':'Read a record.','parameters':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']}}}]
        return [{'role':'system','content':'Use tools when needed.\n<tools>\n'+json.dumps(schema)+'\n</tools>'},{'role':'user','content':'Read K-5.'}],schema
    def test_exact_schema_and_request_preserved(self):
        messages,schemas=self.envelope();converted,tools=native_messages(messages)
        self.assertEqual(tools,schemas);self.assertEqual(converted[0]['content'],'Use tools when needed.')
        self.assertEqual(converted[1],messages[1]);self.assertIn('<tools>',messages[0]['content'])
    def test_tool_history_uses_native_structure(self):
        messages,_=self.envelope()
        call={'name':'lookup','arguments':{'id':'K-5'}}
        messages.extend([{'role':'assistant','content':'<tool_call>'+json.dumps(call)+'</tool_call>'},{'role':'tool','content':'{"value":17}'}])
        converted,_=native_messages(messages)
        self.assertEqual(converted[2]['tool_calls'],[{'type':'function','function':call}])
        self.assertEqual(converted[3],messages[3])
    def test_malformed_and_mixed_outputs_are_not_repaired(self):
        for text in ['<tool_call>{broken}</tool_call>','Sure! <tool_call>{"name":"lookup","arguments":{"id":"K-5"}}</tool_call>']:
            messages,_=self.envelope();messages.append({'role':'assistant','content':text})
            converted,_=native_messages(messages);self.assertEqual(converted[-1],messages[-1])
    def test_warmup_without_tools(self):
        messages=[{'role':'system','content':'Reply briefly.'},{'role':'user','content':'Hello.'}]
        self.assertEqual(native_messages(messages),(messages,None))

if __name__=='__main__':unittest.main()
