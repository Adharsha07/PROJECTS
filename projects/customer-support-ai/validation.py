"""Validate structured return-window claims and render only trusted wording.

This intentionally does not validate arbitrary generated prose.
"""
def checked_answer(retrieval, candidate):
    sources = retrieval.get("sources", [])
    fallback = dict(retrieval, validation="fallback",
                    validation_reason="Candidate did not match an applicable source.")
    if retrieval.get("status") != "answered":
        return dict(retrieval, validation="not_applicable")
    if not isinstance(candidate, dict) or set(candidate) != {
        "policy_id", "version", "passage_id", "return_days", "starts_from"
    }:
        return fallback
    for source in sources:
        facts = source.get("facts", {})
        if (all(candidate[k] == source[k] for k in ("policy_id", "version", "passage_id"))
            and type(candidate["return_days"]) is int
            and candidate["return_days"] == facts.get("return_days")
            and candidate["starts_from"] == facts.get("starts_from")
            and candidate["starts_from"] == "delivery"):
            # Candidate prose is never displayed: render a constrained statement.
            return dict(retrieval, validation="passed",
                        answer=f"Request a return within {facts['return_days']} days after delivery. [{source['passage_id']}]")
    return fallback
