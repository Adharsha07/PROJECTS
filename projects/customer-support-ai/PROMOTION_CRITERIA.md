# Experimental router promotion criteria

These are project-level go/no-go checks for changing the default router. They are intentionally stricter for wrong answers than for safe clarification.

| Measure | Required result |
|---|---:|
| Unsupported question routed into return-policy answering | 0 |
| Mixed request answered as if it were only one request | 0 |
| Correct topic and aspect on supported single requests | At least 90% |
| Supported single requests unnecessarily sent to clarification | At most 10% |
| Guardrail and API regression suite | All pass |

Report each group separately. A safe clarification counts as safer than an irrelevant answer, but still counts against usability. These thresholds are a prototype promotion gate, not proof of production readiness. The set should contain at least 50 questions across several phrasings and should be frozen before the measured run. Do not tune the prompt against that run; make changes only afterward and evaluate them on a new set.

Current status: **numeric prototype gate passed on holdout v10, but the classifier remains experimental and opt-in**. This was one small developer-authored local-model run. One mixed question was safely refused as unsupported instead of receiving the expected split-request clarification.

## First frozen run

The first 50-case run passed 43 cases on all exact checks. Supported single-request routing passed 15/15; mixed requests answered as a single request were 0/10. Two of 15 unsupported questions were mislabeled as return-policy requests, so the zero-false-accept requirement failed. Among the 13 supported cases that should not have been clarified, zero were unnecessarily clarified. Therefore the router remains experimental because it failed the more important false-accept criterion. The other failures were in unsupported/ambiguous wording; see `promotion-results.json` for details. Do not tune against and then rescore this same set; changes need a new evaluation set.

## Scope-gate fix and regression rerun

The blanket return-keyword gate was replaced by category-specific checks: ordinary return questions require a return action; arrival-defect policy questions can also proceed when both a defect cue and a policy cue appear. Order lookup requires actual tracking/status wording, and an independent cross-check stops obvious mixed product-plus-return questions even when the model emits only one request.

On the second frozen 50-case set, the first run had two false accepts, two valid defect-policy clarifications, and one missed mixed request. After the fixes, the regression rerun scored 44/50 overall, with zero unsupported-to-return routes, zero mixed requests answered as one, all 15 supported routes correct, and zero unnecessary clarifications among 13 supported cases that should be answered. All 60 automated tests pass. Because the same set guided these fixes, this result does **not** qualify as an independent promotion run. See `blind-final-results.json`; keep the classifier opt-in until it passes a new untouched set.

## New wording holdout and deadline correction

A new 50-question set was authored without adding its wording to the model prompt. Its first run scored 43/50 and found one supported exact-date question routed as a general return window. A deterministic calendar-date cue was added to route exact-date wording to the existing clarification path. The rerun scored 44/50: unsupported-to-return routes 0/15; mixed requests answered as one 0/10; supported routes 15/15; unnecessary clarifications 0/13; automated tests 61/61. The six remaining exact-match misses concern safe clarifications or ambiguous/out-of-scope labels.

Because the first run informed a code change, the rerun is regression evidence and **not** an independent promotion decision. Keep the classifier opt-in until the final code is evaluated on a fresh, untouched set. See `holdout-v3-results.json` and `holdout-v3-final-results.json`.


## Fresh frozen wording evaluation v10

The v10 set was frozen and run once against the unchanged code. No question was copied verbatim into the classifier prompt. It contains 50 questions: 15 supported, 15 unsupported, 10 mixed, and 10 ambiguous.

Results: 47/50 exact outcomes (94%); unsupported questions routed into return-policy answering 0/15; mixed requests answered as one 0/10; supported routes correct 14/15 (93.3%); unnecessary clarifications 1/12 (8.3%); ambiguous cases clarified 10/10. The full 70-test Python suite passes. Mean request time was 0.454 seconds and median 0.320 seconds in this single local run.

The numeric criteria are met. Three exact mismatches remain: one product-repair question was safely clarified, one return-window paraphrase was safely clarified, and one cycling-plus-return question was refused as unsupported rather than asking the customer to split it. No unsupported question in this set received a return answer, and no mixed question received a single-part answer. Keep the classifier opt-in: this internal evaluation is small, developer-authored, and a single run; it is not production-readiness evidence. A separate v7 run is excluded from holdout evidence because one question was also present verbatim in the prompt examples.

See holdout-v10-cases.json and holdout-v10-results.json.
