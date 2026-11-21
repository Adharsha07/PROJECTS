import unittest
from support import respond
from validation import checked_answer

CONTEXT = {"purchase_date":"2026-10-25","country":"US","category":"footwear"}
class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.retrieval=respond("What is the return window?", CONTEXT)
        self.candidate={"policy_id":"returns","version":"v1","passage_id":"returns-v1-window",
                        "return_days":30,"starts_from":"delivery"}
    def test_correct_facts_pass(self):
        result=checked_answer(self.retrieval,self.candidate)
        self.assertEqual(result["validation"],"passed")
        self.assertIn("30 days after delivery",result["answer"])
    def test_purchase_event_falls_back(self):
        result=checked_answer(self.retrieval,dict(self.candidate,starts_from="purchase"))
        self.assertEqual(result["validation"],"fallback")
        self.assertEqual(result["answer"],self.retrieval["answer"])
    def test_wrong_duration_falls_back(self):
        self.assertEqual(checked_answer(self.retrieval,dict(self.candidate,return_days=14))["validation"],"fallback")
    def test_wrong_policy_version_falls_back(self):
        self.assertEqual(checked_answer(self.retrieval,dict(self.candidate,version="v2"))["validation"],"fallback")
    def test_fabricated_citation_falls_back(self):
        self.assertEqual(checked_answer(self.retrieval,dict(self.candidate,passage_id="invented"))["validation"],"fallback")
    def test_extra_prose_cannot_bypass_validation(self):
        result=checked_answer(self.retrieval,dict(self.candidate,answer="Refund guaranteed"))
        self.assertEqual(result["validation"],"fallback")
        self.assertNotIn("guaranteed",result["answer"])
    def test_non_answer_cannot_be_overridden(self):
        r=respond("What is the return window?",{})
        self.assertEqual(checked_answer(r,self.candidate)["status"],"clarify")
    def test_conditions_have_no_return_window_facts(self):
        r=respond("Can I return used shoes?",CONTEXT)
        self.assertEqual(checked_answer(r,self.candidate)["validation"],"fallback")
    def test_malformed_candidate_falls_back(self):
        for candidate in [None,[],{},dict(self.candidate,return_days="30")]:
            self.assertEqual(checked_answer(self.retrieval,candidate)["validation"],"fallback")
if __name__ == "__main__":
    unittest.main()
