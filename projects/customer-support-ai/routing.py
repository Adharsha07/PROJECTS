"""Two-level, bounded routing labels; policy decisions remain deterministic."""
import re

RETURN_QUESTIONS = {
    "window": "What is the return window?",
    "condition": "Can I return used shoes?",
    "deadline": "What is my exact return deadline?",
    "exception": "What is the defective-product return exception?",
    "refund_guarantee": "Can you guarantee my refund?",
}
TOPICS = {"return_policy", "order_status", "unsupported", "clarify"}
ASPECTS = set(RETURN_QUESTIONS) | {"none"}
RETURN_ACTION = re.compile(r"\b(return\w*|refund\w*|exchange\w*|money\s+back|(?:send|give|take|go)\b.{0,50}\bback|change\s+my\s+mind)\b", re.I)
ARRIVAL_DEFECT = re.compile(r"\b(broken|damaged|defect\w*|faulty|cracked|split|tear\w*|torn|loose|separat\w*)\b", re.I)
POLICY_CUE = re.compile(r"\b(policy|exception|cover\w*|eligible|return option)\b", re.I)
ORDER_STATUS_CUE = re.compile(r"\b(track\w*|tracking|shipment|shipped|carrier|courier|parcel|package|delivery status|order status|where is my order|delivered)\b", re.I)
PRODUCT_FEATURE_CUE = re.compile(r"\b(leather|material|color|colour|size|fit|waterproof|comfortable|comfort|clean\w*|laces|sole|support|durab\w*|warranty|discount|price|replace|replacement|feature)\b", re.I)
MULTI_CONNECTOR = re.compile(r"\b(and|also|plus|as well as)\b|[;?].+\b(?:and|also)\b", re.I)
CONDITION_CUE = re.compile(r"\b(worn|wear|tried|try on|box|packaging|package|unused|used|condition)\b", re.I)


def _explicit_arrival_exception(question):
    return bool(ARRIVAL_DEFECT.search(question) and POLICY_CUE.search(question))


def route_question(question, classifier):
    """Classify once; proceed only when exactly one request is identified."""
    classification = classifier(question)
    # Independent intent cross-check catches a model that collapses two
    # clauses into one label (for example, product facts + return policy).
    if RETURN_ACTION.search(question) and PRODUCT_FEATURE_CUE.search(question) and MULTI_CONNECTOR.search(question):
        return "clarify", "none", None
    if RETURN_ACTION.search(question) and ORDER_STATUS_CUE.search(question) and MULTI_CONNECTOR.search(question):
        return "clarify", "none", None
    # A clear arrival-defect policy question is one request even when the
    # small model splits the incident and the policy question into two items.
    if _explicit_arrival_exception(question):
        return "return_policy", "exception", RETURN_QUESTIONS["exception"]
    if not isinstance(classification, dict) or set(classification) != {"requests"}:
        raise ValueError("Malformed classification.")
    requests = classification["requests"]
    if not isinstance(requests, list) or not requests:
        raise ValueError("At least one request must be identified.")
    if len(requests) != 1:
        return "clarify", "none", None
    request = requests[0]
    if not isinstance(request, dict) or set(request) != {"topic", "aspect"}:
        raise ValueError("Malformed request classification.")
    topic, aspect = request["topic"], request["aspect"]
    if topic not in TOPICS or aspect not in ASPECTS:
        raise ValueError("Unapproved classification.")
    if topic == "return_policy":
        if aspect == "none":
            raise ValueError("A return-policy aspect is required.")
        if aspect == "exception" and CONDITION_CUE.search(question) and not ARRIVAL_DEFECT.search(question):
            aspect = "condition"
        # Defense in depth: a model label alone cannot turn an unrelated
        # repair or sales question into a return-policy request.
        explicit_return = RETURN_ACTION.search(question)
        explicit_arrival_exception = (
            aspect == "exception"
            and ARRIVAL_DEFECT.search(question)
            and POLICY_CUE.search(question)
        )
        if not (explicit_return or explicit_arrival_exception):
            return "clarify", "none", None
        return topic, aspect, RETURN_QUESTIONS[aspect]
    if aspect != "none":
        raise ValueError("Non-return topics must use aspect none.")
    if topic == "order_status":
        if not ORDER_STATUS_CUE.search(question):
            return "clarify", "none", None
        return topic, aspect, "Where is my order?"
    return topic, aspect, "Unsupported topic" if topic == "unsupported" else None
