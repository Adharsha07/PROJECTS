import io
import json
import unittest
from unittest.mock import patch
from local_model import propose_facts
from support import respond

class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.evidence=respond('return window', {'purchase_date':'2026-10-25','country':'US','category':'footwear'})
    def fake(self, body):
        class Opener:
            def open(inner, request, timeout):
                self.payload=json.loads(request.data)
                self.assertEqual(request.full_url,'http://127.0.0.1:11434/api/chat')
                return io.BytesIO(json.dumps(body).encode())
        return Opener()
    def test_schema_and_local_destination(self):
        facts={'policy_id':'returns','version':'v1','passage_id':'returns-v1-window','return_days':30,'starts_from':'delivery'}
        with patch('local_model.build_opener',return_value=self.fake({'done':True,'message':{'content':json.dumps(facts)}})):
            self.assertEqual(propose_facts(self.evidence),facts)
        self.assertFalse(self.payload['stream'])
        self.assertNotIn('facts',self.payload['messages'][1]['content'])
        self.assertEqual(len(self.payload['format']['required']),5)
    def test_incomplete_response_rejected(self):
        with patch('local_model.build_opener',return_value=self.fake({'done':True,'done_reason':'length'})):
            with self.assertRaises(ValueError): propose_facts(self.evidence)
    def test_malformed_output_rejected(self):
        with patch('local_model.build_opener',return_value=self.fake({'done':True,'message':{'content':'not json'}})):
            with self.assertRaises(ValueError): propose_facts(self.evidence)
    def test_unapproved_model_rejected(self):
        with self.assertRaises(ValueError): propose_facts(self.evidence,model='remote-cloud')

if __name__=='__main__': unittest.main()
