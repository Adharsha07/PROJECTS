import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from api import Handler, RequestError, answer_request

PAYLOAD={"question":"What is the return window?","context":{
    "purchase_date":"2026-10-25","country":"US","category":"footwear"}}

class ServiceTests(unittest.TestCase):
    def test_no_model_returns_verified_passage(self):
        r=answer_request(PAYLOAD)
        self.assertEqual(r["validation"],"verified_passage")
        self.assertIn("30 days after delivery",r["answer"])
    def test_generator_mismatch_falls_back(self):
        def wrong(evidence):
            return {"policy_id":"returns","version":"v1","passage_id":"returns-v1-window",
                    "return_days":30,"starts_from":"purchase"}
        r=answer_request(PAYLOAD,wrong)
        self.assertEqual(r["validation"],"fallback")
        self.assertIn("after delivery",r["answer"])
    def test_generator_failure_falls_back(self):
        def broken(_): raise RuntimeError("private detail")
        r=answer_request(PAYLOAD,broken)
        self.assertEqual(r["generation"],"failed")
        self.assertNotIn("private detail",str(r))
    def test_bad_types(self):
        for payload in [None,[],{},{"question":""},{"question":22},
                        {"question":"returns","context":{"country":123}},
                        dict(PAYLOAD,candidate={})]:
            with self.subTest(payload=payload), self.assertRaises(RequestError):
                answer_request(payload)

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
    def request(self, payload, path="/api/answer", content_type="application/json", raw=False):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
        try:
            conn.request("POST",path,body=payload if raw else json.dumps(payload),
                         headers={"Content-Type":content_type})
            response=conn.getresponse()
            return response.status,json.loads(response.read())
        finally: conn.close()
    def test_valid_question(self):
        status,r=self.request(PAYLOAD)
        self.assertEqual(status,200)
        self.assertEqual(r["status"],"answered")
        self.assertEqual(r["sources"][0]["passage_id"],"returns-v1-window")
    def test_missing_details(self):
        status,r=self.request({"question":"What is the return window?"})
        self.assertEqual(status,200)
        self.assertEqual(r["status"],"clarify")
        self.assertIn("purchase_date",r["missing"])
    def test_bad_request(self):
        self.assertEqual(self.request({"question":42})[0],400)
    def test_malformed_json(self):
        self.assertEqual(self.request("{broken",raw=True)[0],400)
    def test_wrong_content_type(self):
        self.assertEqual(self.request(PAYLOAD,content_type="text/plain")[0],415)
    def test_unknown_route(self):
        self.assertEqual(self.request(PAYLOAD,path="/wrong")[0],404)
    def test_invalid_date(self):
        payload=dict(PAYLOAD,context=dict(PAYLOAD["context"],purchase_date="bad"))
        self.assertEqual(self.request(payload)[0],422)
    def test_oversized_body(self):
        self.assertEqual(self.request(" " * 17000,raw=True)[0],413)
    def test_caller_cannot_supply_candidate(self):
        self.assertEqual(self.request(dict(PAYLOAD,candidate={"return_days":99}))[0],400)
    def test_health(self):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
        try:
            conn.request("GET","/health");response=conn.getresponse()
            self.assertEqual(response.status,200)
            self.assertFalse(json.loads(response.read())["model_connected"])
        finally: conn.close()
    def test_browser_form_routes(self):
        for path in ("/", "/api/answer"):
            conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
            try:
                conn.request("GET",path)
                response=conn.getresponse()
                self.assertEqual(response.status,200)
                self.assertIn("text/html",response.getheader("Content-Type"))
                self.assertIn(b"Check the policy",response.read())
            finally: conn.close()
if __name__=="__main__": unittest.main()

