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

Current status: **not eligible for promotion**. The latest 50-case set was used to find and refine the guardrails, so its rerun is regression evidence rather than an independent promotion test.

## First frozen run

The first 50-case run passed 43 cases on all exact checks. Supported single-request routing passed 15/15; mixed requests answered as a single request were 0/10. Two of 15 unsupported questions were mislabeled as return-policy requests, so the zero-false-accept requirement failed. Among the 13 supported cases that should not have been clarified, zero were unnecessarily clarified. Therefore the router remains experimental because it failed the more important false-accept criterion. The other failures were in unsupported/ambiguous wording; see `promotion-results.json` for details. Do not tune against and then rescore this same set; changes need a new evaluation set.

## Scope-gate fix and regression rerun

The blanket return-keyword gate was replaced by category-specific checks: ordinary return questions require a return action; arrival-defect policy questions can also proceed when both a defect cue and a policy cue appear. Order lookup requires actual tracking/status wording, and an independent cross-check stops obvious mixed product-plus-return questions even when the model emits only one request.

On the second frozen 50-case set, the first run had two false accepts, two valid defect-policy clarifications, and one missed mixed request. After the fixes, the regression rerun scored 44/50 overall, with zero unsupported-to-return routes, zero mixed requests answered as one, all 15 supported routes correct, and zero unnecessary clarifications among 13 supported cases that should be answered. All 60 automated tests pass. Because the same set guided these fixes, this result does **not** qualify as an independent promotion run. See `blind-final-results.json`; keep the classifier opt-in until it passes a new untouched set.
