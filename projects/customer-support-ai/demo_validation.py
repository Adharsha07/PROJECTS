from support import respond
from validation import checked_answer

evidence = respond("What is the return window?", {
    "purchase_date": "2026-10-25", "country": "US", "category": "footwear"
})
candidate = {"policy_id": "returns", "version": "v1", "passage_id": "returns-v1-window",
             "return_days": 30, "starts_from": "delivery"}
for event in ["delivery", "purchase"]:
    result = checked_answer(evidence, dict(candidate, starts_from=event))
    print(f"Candidate starting event: {event}; validation: {result['validation']}")
    print(result["answer"])
