# Classifier redesign: scoped topic, then return detail

## Design

The old classifier chose among many peer labels. It confused a return duration with a calendar deadline, and sometimes mistook a product-feature question for a return-condition question.

The experimental classifier returns a structured `requests` list. Each item contains a topic (`return_policy`, `order_status`, `unsupported`, or `clarify`) and, for a return-policy item, an aspect (`window`, `condition`, `deadline`, `exception`, or `refund_guarantee`). The API only proceeds with one request.

Duration and a general time limit map to `window`; a specific calendar-date request maps to `deadline`. Contrastive prompt examples distinguish an actual request to return something from questions about product features or durability. The classifier is called once. Invalid output, a clear `unsupported` result, or a `clarify` result stops before retrieval and answer generation. These checks bound the flow but cannot guarantee that the model chooses the right topic.

The normal app continues to use the previously reviewed keyword router and local extraction. The redesigned classifier remains opt-in with `--local-model --model-router`.

## Exploratory reassessment

On the same 15 developer-authored cases, the latest single run passed 14/15 expected outcomes, versus 8/15 for the keyword baseline. The redesigned classifier passed 9/9 original cases and 5/6 added cases. It correctly rejected both product-feature questions about waterproofing and product durability. It also mapped “send them back” duration wording to the return window and distinguished a worn-item question from a duration question.

The one failed expected decision was a mixed return-and-shipping request. The classifier returned output that did not satisfy the schema. The API safely stopped and asked the user to rephrase, but the classifier did not explicitly select `clarify`, so that case remains a classifier failure. Six requests triggered fact extraction and all six passed the separate facts validator.

This is a small exploratory set, not a representative or independent benchmark. Prompt examples and evaluation cases share concepts, the same cases were reused during iteration, and the run does not measure general wording faithfulness. Passing 14/15 does not establish production reliability. See `reassessment-results.json` for the recorded results.

## Fresh challenge and product-scope probes

A later 14-case challenge set, written after the prompt iteration and absent from the prompt examples, passed 6/14 on the strict topic, aspect, status, and citation checks. It found failures on exact calendar-date requests, defective-item exceptions, tracking paraphrases, vague requests, and mixed requests. Three malformed or rejected classifier results were handled by a safe clarification. One refund-guarantee case was scored against an `insufficient_evidence` status even though the backend returned its explicit `unsupported` refusal; the intent label was correct, so that expected-status mismatch overstates the user-facing failure. The detailed saved report preserves the original scoring. See `holdout-results.json`.

The focused product-scope probe then tested 12 new product-feature questions plus four return-boundary controls. The model rejected 11/12 product questions as unsupported. The remaining product question failed classification and safely triggered clarification; none of the 12 was incorrectly routed into return-policy retrieval. Two of four boundary controls passed: the window and condition questions. The defective-item question was misrouted to condition, and a mixed request failed classification but safely asked for clarification. This is encouraging evidence for the product-feature gate, with weak performance on some less common supported topics; the sample is still too small to promote the router. See `product-scope-results.json`.

## Automated checks

The current suite has 61 passing test methods. They verify routing schema enforcement, one classifier call per request, no retrieval after unsupported/unclear/mixed questions, the scope-gate false-accept cases, exact-calendar-deadline handling, policy-version selection, and HTTP behavior. Most routing cases use mocked classifier outputs; they validate guardrail code rather than real model accuracy.


The request-list iteration adds independent checks for return intent, explicit arrival-defect policy questions, real tracking intent, and obvious mixed product-plus-return requests. A broad return-keyword rule initially blocked some valid defect questions. The category-specific gate now lets those policy questions reach the existing “not specified” response while repair and discount questions stop before retrieval. A separate 50-question wording set found an exact-date routing error; a deterministic date cue now sends that request to the existing clarify response. The initial run scored 43/50, and the regression rerun 44/50 with zero unsupported-to-return routes, zero mixed requests answered as one, supported routing 15/15, unnecessary clarification 0/13, and 61 tests passing. Since the first run drove a code fix, the rerun is not an independent promotion result. See `holdout-v3-results.json`, `holdout-v3-final-results.json`, and `PROMOTION_CRITERIA.md`.

## Next evaluation

Keep the new classifier behind its opt-in flag. The next promotion decision requires a new untouched evaluation set; do not tune against or rescore the regression set as if it were blind. Continue reporting false acceptance separately from safe rejection, since an unrelated answer is riskier than a clarification.
