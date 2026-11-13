import unittest
from assistant import EVIDENCE, answer, retrieve

class EvidenceTests(unittest.TestCase):
    def test_exact_product(self):
        self.assertEqual([s["id"] for s in retrieve("AB-123", "comfort", EVIDENCE)], ["spec-ab"])

    def test_claim_is_labeled(self):
        result = answer("AB-123")
        self.assertIn("Manufacturer claim (not independent confirmation)", result["answer"])
        self.assertIn("[spec-ab]", result["answer"])
        self.assertNotIn("review-cd", str(result["sources"]))

    def test_review_is_preserved(self):
        result = answer("CD-456")
        self.assertIn("my feet hurt after eight", result["answer"])
        self.assertIn("Individual customer report", result["answer"])

    def test_missing_topic(self):
        result = answer("GH-000")
        self.assertEqual(result["sources"], [])
        self.assertIn("not have enough evidence", result["answer"])
        self.assertNotIn("uncomfortable", result["answer"])

    def test_wrong_product_only(self):
        result = answer("AB-123", records=[EVIDENCE[1]])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["alternatives"], ["CD-456"])

    def test_no_evidence(self):
        result = answer("UNKNOWN", records=[])
        self.assertEqual(result["alternatives"], [])
        self.assertIn("not have enough evidence", result["answer"])

    def test_conflicting_evidence_is_not_hidden(self):
        conflicting = dict(EVIDENCE[1], id="negative-ab", product="AB-123")
        result = answer("AB-123", records=EVIDENCE + [conflicting])
        self.assertEqual(len(result["sources"]), 2)
        self.assertIn("my feet hurt after eight", result["answer"])
        self.assertIn("Manufacturer claim", result["answer"])

if __name__ == "__main__":
    unittest.main()
