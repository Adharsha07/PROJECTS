import copy
import json
import unittest
from pathlib import Path
from support import load_policies, respond, validate

BASE = {"purchase_date":"2026-11-02", "country":"US", "category":"footwear"}
class PolicyTests(unittest.TestCase):
    def test_planned_cases(self):
        cases = json.loads((Path(__file__).parent / "evaluation-cases.json").read_text())["cases"]
        statuses = {"old-purchase":"answered", "boundary-purchase":"answered",
                    "missing-purchase-date":"clarify", "missing-delivery-date":"clarify",
                    "unsupported-scope":"insufficient_evidence", "used-item":"answered",
                    "unknown-exception":"insufficient_evidence", "order-status":"unavailable",
                    "refund-guarantee":"unsupported"}
        for case in cases:
            with self.subTest(case=case["id"]):
                r = respond(case["question"], case["context"])
                self.assertEqual(r["status"], statuses[case["id"]])
                expected = case["expect"]
                if "policy_version" in expected:
                    self.assertEqual(r["policy_version"], expected["policy_version"])
                if "citation" in expected:
                    self.assertIn(expected["citation"], [s["passage_id"] for s in r["sources"]])
                if "return_days_after_delivery" in expected:
                    self.assertIn(str(expected["return_days_after_delivery"]) + " days", r["answer"])
                if case["id"] == "missing-purchase-date":
                    self.assertIn("purchase_date", r["missing"])
                if case["id"] == "missing-delivery-date":
                    self.assertIn("delivery_date", r["missing"])
    def test_pre_boundary(self):
        r=respond("return window", dict(BASE,purchase_date="2026-10-31"))
        self.assertEqual(r["policy_version"],"v1")
    def test_missing_scope(self):
        self.assertEqual(respond("return window", {})["missing"],
                         ["purchase_date","country","category"])
    def test_no_policy_before_coverage(self):
        self.assertEqual(respond("return window",dict(BASE,purchase_date="2025-12-31"))["status"],
                         "insufficient_evidence")
    def test_invalid_dates(self):
        for value in ["2026-02-30","20261102","tomorrow"]:
            self.assertEqual(respond("return window",dict(BASE,purchase_date=value))["status"],
                             "invalid_input")
    def test_delivery_before_purchase(self):
        self.assertEqual(respond("return deadline",dict(BASE,delivery_date="2026-10-01"))["status"],
                         "invalid_input")
    def test_overlap_fails_closed(self):
        policies=load_policies()
        extra=copy.deepcopy(policies[1]);extra["version"]="v3";policies.append(extra)
        self.assertEqual(respond("return window",BASE,policies)["status"],"conflict")
    def test_bad_interval_rejected(self):
        policies=load_policies();policies[0]["purchase_before"]=policies[0]["purchase_from"]
        with self.assertRaises(ValueError): validate(policies)
    def test_citation_exactly_matches_source(self):
        policies=load_policies();r=respond("return window",BASE,policies)
        s=r["sources"][0]
        p=next(p for p in policies if p["version"]==s["version"])
        self.assertEqual(s["text"],next(x["text"] for x in p["passages"] if x["id"]==s["passage_id"]))
        self.assertEqual(s["source_id"],p["source_id"])
    def test_unknown_question(self):
        self.assertEqual(respond("Is this waterproof?",BASE)["sources"],[])
    def test_case_normalization(self):
        self.assertEqual(respond("return window",dict(BASE,country="us",category="FOOTWEAR"))["status"],"answered")
    def test_deadline_not_invented(self):
        r=respond("exact return deadline",dict(BASE,delivery_date="2026-11-05"))
        self.assertEqual(r["status"],"clarify")
        self.assertIn("not implemented",r["answer"])
if __name__ == "__main__":
    unittest.main()
