import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))

from app import App, answer_policy, init_db


class CustomerSupportAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App(Path(self.temp.name) / "support.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_login_and_order_scoping(self):
        session = self.app.login({"email": "demo@example.com", "password": "demo-password-123"})
        self.assertEqual(session["user"]["role"], "customer")
        orders = self.app.orders(session["token"])
        self.assertEqual([row["id"] for row in orders], ["order-1002", "order-1001"])

    def test_new_user_registration_and_authentication(self):
        result = self.app.register({"email": "new@example.com", "password": "a-long-password"})
        self.assertEqual(result["user"]["email"], "new@example.com")
        self.assertEqual(self.app.current_user(result["token"])["email"], "new@example.com")
        with self.assertRaises(PermissionError):
            self.app.login({"email": "new@example.com", "password": "wrong-password"})

    def test_policy_version_is_selected_by_purchase_date(self):
        october = answer_policy("How long do I have to return these shoes?", {
            "purchase_date": "2026-10-25", "country": "US", "category": "footwear"
        })
        november = answer_policy("How long do I have to return these shoes?", {
            "purchase_date": "2026-11-01", "country": "US", "category": "footwear"
        })
        self.assertEqual(october["facts"]["return_days"], 30)
        self.assertEqual(october["version"], "v1")
        self.assertEqual(november["facts"]["return_days"], 14)
        self.assertEqual(november["version"], "v2")

    def test_policy_requires_context_and_does_not_invent_deadline(self):
        missing = answer_policy("How long do I have to return this?", {})
        self.assertEqual(missing["status"], "clarify")
        deadline = answer_policy("What is the exact final date?", {
            "purchase_date": "2026-10-25", "country": "US", "category": "footwear"
        })
        self.assertEqual(deadline["status"], "clarify")

    def test_customer_ticket_and_agent_resolution(self):
        customer = self.app.login({"email": "demo@example.com", "password": "demo-password-123"})
        ticket = self.app.create_ticket(customer["token"], {
            "subject": "Package has not arrived", "message": "Please check order-1002", "order_id": "order-1002", "priority": "high"
        })
        self.assertEqual(ticket["status"], "open")
        self.assertEqual(len(self.app.tickets(customer["token"])), 1)
        agent = self.app.login({"email": "agent@example.com", "password": "agent-password-123"})
        resolved = self.app.resolve_ticket(agent["token"], ticket["id"], {"resolution_note": "Carrier trace opened."})
        self.assertEqual(resolved["status"], "resolved")

    def test_customer_cannot_see_other_customer_order_or_resolve_ticket(self):
        customer = self.app.login({"email": "demo@example.com", "password": "demo-password-123"})
        with self.assertRaises(ValueError):
            self.app.create_ticket(customer["token"], {
                "subject": "Other order", "message": "I need help", "order_id": "order-does-not-exist"
            })
        with self.assertRaises(PermissionError):
            self.app.resolve_ticket(customer["token"], 1, {"resolution_note": "No"})

    def test_chat_understands_order_policy_and_clarifies_unknowns(self):
        session = self.app.login({"email": "demo@example.com", "password": "demo-password-123"})
        order = self.app.chat(session["token"], {"message": "Where is order-1002?"})
        self.assertEqual(order["kind"], "order")
        self.assertIn("In transit", order["message"])
        policy = self.app.chat(session["token"], {
            "message": "How long do I have to return these shoes?",
            "context": {"purchase_date": "2026-10-25", "country": "US", "category": "footwear"},
        })
        self.assertEqual(policy["kind"], "policy")
        self.assertIn("30 days", policy["message"])
        unclear = self.app.chat(session["token"], {"message": "Can you help me?"})
        self.assertEqual(unclear["kind"], "handoff")


if __name__ == "__main__":
    unittest.main()

