"""Dependency-free policy retrieval baseline; no LLM or live tools."""
import argparse
import json
import re
from datetime import date
from pathlib import Path

def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Dates must use YYYY-MM-DD.")
    return date.fromisoformat(value)

def load_policies():
    return json.loads((Path(__file__).parent / "data/policies.json").read_text())

def validate(policies):
    identities = set()
    for p in policies:
        key = (p["policy_id"], p["version"], tuple(sorted(p["scope"].items())))
        if key in identities:
            raise ValueError("Duplicate policy identity.")
        identities.add(key)
        start = parse_date(p["purchase_from"])
        end = parse_date(p["purchase_before"]) if p["purchase_before"] else None
        if end and end <= start:
            raise ValueError("Policy interval must have a positive duration.")
        ids = [s["id"] for s in p["passages"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate passage identity.")

def respond(question, context=None, policies=None):
    context = context or {}
    policies = load_policies() if policies is None else policies
    validate(policies)
    q = question.lower()
    def result(status, answer, sources=None, **extra):
        return dict(status=status, answer=answer, sources=sources or [], **extra)
    # Deliberately bounded routing, not general natural-language understanding.
    if re.search(r"\b(order|tracking|shipment)\b", q):
        return result("unavailable", "Live order lookup is not connected. I cannot determine your order status.")
    if re.search(r"\b(guarantee|guaranteed|promise)\b", q):
        return result("unsupported", "I cannot guarantee refund approval or execute a refund.")
    if not re.search(r"\b(return|returns|refund|refunded|defective)\b", q):
        return result("insufficient_evidence", "No supported policy topic was identified. Please ask about returns.")
    missing = [k for k in ("purchase_date", "country", "category") if not context.get(k)]
    if missing:
        return result("clarify", "Please provide: " + ", ".join(missing), missing=missing)
    try:
        purchased = parse_date(context["purchase_date"])
        delivered = parse_date(context["delivery_date"]) if context.get("delivery_date") else None
        if delivered and delivered < purchased:
            raise ValueError("Delivery cannot precede purchase.")
    except ValueError as exc:
        return result("invalid_input", str(exc))
    eligible = [p for p in policies if p["scope"] == {
        "country": context["country"].upper(), "category": context["category"].lower()
    } and parse_date(p["purchase_from"]) <= purchased
       and (not p["purchase_before"] or purchased < parse_date(p["purchase_before"]))]
    if not eligible:
        return result("insufficient_evidence", "There is no applicable policy for this purchase date and scope.")
    if len(eligible) != 1:
        return result("conflict", "Multiple policies apply. A support reviewer must resolve the conflict.")
    p = eligible[0]
    exact_deadline = bool(re.search(r"\b(deadline|last day|exact date)\b", q))
    # Select the passage type conservatively. Unknown exceptions never become invented rules.
    if re.search(r"\b(defective|exception|exceptions|damaged)\b", q):
        return result("insufficient_evidence", "The supplied policy does not specify this exception. Please contact support.", policy_version=p["version"])
    condition = bool(re.search(r"\b(used|unused|worn|packaging|condition)\b", q))
    passage = next((s for s in p["passages"] if s["id"].endswith("-condition" if condition else "-window")), None)
    if not passage:
        return result("insufficient_evidence", "The applicable policy has no passage supporting this answer.")
    citation = dict(policy_id=p["policy_id"], version=p["version"], passage_id=passage["id"],
                    source_id=p["source_id"], text=passage["text"], facts=passage.get("facts", {}))
    answer = passage["text"] + " [" + passage["id"] + "]"
    if exact_deadline:
        # Date arithmetic is deferred until store cutoff/timezone rules are explicit.
        return result("clarify", answer + " Exact deadline calculation is not implemented; provide delivery details to support.",
                      [citation], policy_version=p["version"], missing=[] if delivered else ["delivery_date"])
    return result("answered", answer, [citation], policy_version=p["version"])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--purchase-date")
    parser.add_argument("--delivery-date")
    parser.add_argument("--country")
    parser.add_argument("--category")
    args = parser.parse_args()
    context = {key: getattr(args, key) for key in
               ("purchase_date", "delivery_date", "country", "category")}
    print(json.dumps(respond(args.question, context), indent=2))

if __name__ == "__main__":
    main()
