"""Reproducible product-flow evaluation for the customer-support platform."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app import App, answer_policy


def run_evaluation() -> dict:
    cases: list[dict] = []

    def record(name: str, category: str, operation) -> None:
        try:
            detail = operation()
            cases.append({"name": name, "category": category, "passed": True, "detail": detail or "Expected behavior observed."})
        except Exception as error:  # Evaluation records a failure instead of stopping early.
            cases.append({"name": name, "category": category, "passed": False, "detail": f"{type(error).__name__}: {error}"})

    def require(condition: bool, detail: str) -> str:
        if not condition:
            raise AssertionError(detail)
        return detail

    with tempfile.TemporaryDirectory() as directory:
        app = App(Path(directory) / "evaluation.sqlite3")
        customer = app.login({"email": "demo@example.com", "password": "demo-password-123"})
        agent = app.login({"email": "agent@example.com", "password": "agent-password-123"})
        newcomer = app.register({"email": "new@example.com", "password": "evaluation-pass"})

        record("Valid customer login", "authentication", lambda: require(customer["user"]["role"] == "customer", "Customer session created."))

        def invalid_login():
            try:
                app.login({"email": "demo@example.com", "password": "incorrect-pass"})
            except PermissionError:
                return "Incorrect password rejected."
            raise AssertionError("Incorrect password was accepted.")
        record("Invalid password rejection", "authentication", invalid_login)

        record("Customer order list", "order_access", lambda: require(
            [order["id"] for order in app.orders(customer["token"])] == ["order-1002", "order-1001"],
            "Only the two seeded customer orders were returned.",
        ))
        record("Unknown order isolation", "order_access", lambda: require(app.orders(customer["token"], "order-9999") == [], "Unknown order returned no data."))
        record("New account order isolation", "order_access", lambda: require(app.orders(newcomer["token"]) == [], "New customer cannot see demo orders."))

        october = {"purchase_date": "2026-10-25", "country": "US", "category": "footwear"}
        november = {"purchase_date": "2026-11-01", "country": "US", "category": "footwear"}
        record("Policy version v1", "policy", lambda: require(answer_policy("How long can I return this?", october)["version"] == "v1", "October purchase selected v1."))
        record("Policy version v2", "policy", lambda: require(answer_policy("How long can I return this?", november)["version"] == "v2", "November purchase selected v2."))
        record("Missing context clarification", "policy", lambda: require(answer_policy("How long can I return this?", {})["status"] == "clarify", "Missing applicability fields requested."))
        record("Exact deadline clarification", "policy", lambda: require(answer_policy("What is the exact final day to return?", october)["status"] == "clarify", "Exact date was not invented."))
        record("Unsupported product question", "policy", lambda: require(answer_policy("Are these waterproof?", october)["status"] == "clarify", "Out-of-scope product question was stopped."))
        record("Defect evidence boundary", "policy", lambda: require(answer_policy("Does the policy cover a defective item?", october)["status"] == "insufficient_evidence", "Undocumented defect exception was not invented."))
        record("Refund guarantee refusal", "policy", lambda: require(answer_policy("Can you guarantee my refund?", october)["status"] == "unsupported", "Refund approval was not promised."))

        ticket_box: dict = {}

        def create_ticket():
            ticket = app.create_ticket(customer["token"], {
                "subject": "Package has not arrived", "message": "Please investigate the carrier status.",
                "order_id": "order-1002", "priority": "high",
            })
            ticket_box["ticket"] = ticket
            return require(ticket["status"] == "open", "Customer created a high-priority ticket linked to an owned order.")
        record("Customer ticket creation", "handoff", create_ticket)

        def foreign_order_ticket():
            try:
                app.create_ticket(newcomer["token"], {"subject": "Wrong order", "message": "Please inspect it.", "order_id": "order-1002"})
            except ValueError:
                return "Ticket could not link to another customer's order."
            raise AssertionError("Another customer's order was accepted.")
        record("Ticket order ownership", "handoff", foreign_order_ticket)

        record("Agent queue visibility", "agent_workflow", lambda: require(
            app.tickets(agent["token"])[0]["customer_email"] == "demo@example.com", "Agent saw the customer queue with identity context."
        ))

        def customer_cannot_resolve():
            try:
                app.resolve_ticket(customer["token"], ticket_box["ticket"]["id"], {"resolution_note": "Closed"})
            except PermissionError:
                return "Customer resolution attempt was rejected."
            raise AssertionError("Customer resolved an agent-only ticket.")
        record("Agent-only resolution", "authorization", customer_cannot_resolve)

        record("Agent resolves ticket", "agent_workflow", lambda: require(
            app.resolve_ticket(agent["token"], ticket_box["ticket"]["id"], {"resolution_note": "Carrier trace opened."})["status"] == "resolved",
            "Agent resolved the ticket with a note.",
        ))
        record("Resolution audit trail", "auditability", lambda: require(
            [event["action"] for event in app.audit_events(agent["token"])[:2]] == ["ticket.resolved", "ticket.created"],
            "Creation and resolution events were recorded in order.",
        ))

        def customer_cannot_read_audit():
            try:
                app.audit_events(customer["token"])
            except PermissionError:
                return "Customer audit-log access was rejected."
            raise AssertionError("Customer read the agent audit log.")
        record("Agent-only audit access", "authorization", customer_cannot_read_audit)

        payload = "<img src=x onerror=alert(1)>"
        stored = app.create_ticket(customer["token"], {"subject": "Markup payload", "message": payload})
        interface = (Path(__file__).parent / "static" / "index.html").read_text()
        record("Stored text rendering boundary", "browser_safety", lambda: require(
            stored["message"] == payload and "textContent" in interface,
            "Stored customer text remains data and the UI renders it with textContent.",
        ))

    passed = sum(case["passed"] for case in cases)
    by_category: dict[str, dict[str, int]] = {}
    for case in cases:
        group = by_category.setdefault(case["category"], {"passed": 0, "total": 0})
        group["total"] += 1
        group["passed"] += int(case["passed"])
    return {
        "evaluation": "Customer Support AI product flow v1",
        "cases": len(cases),
        "passed": passed,
        "pass_rate": round(passed / len(cases), 4),
        "by_category": by_category,
        "results": cases,
        "limitations": [
            "The data and policies are fictional.",
            "The evaluator exercises application functions locally, not a production deployment.",
            "It does not establish security compliance, availability, or real-world model accuracy.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_evaluation()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
