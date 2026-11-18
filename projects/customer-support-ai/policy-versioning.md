# Decision 001: filter for applicability before ranking by relevance

## Problem

An older policy can match a customer's wording better than the current one. A document's update timestamp does not establish whether it governs a purchase.

## Decision

Preserve policy identity, version, effective purchase-date interval, scope and authoritative source identity alongside text. Determine eligibility before text relevance ranking. Retain older versions for purchases they still govern.

The fictional fixture uses half-open date intervals: purchase date >= purchase_from and purchase date < purchase_before. A null upper bound means no specified end date. These are store-defined example rules, not legal guidance.

For the same country and category:
- Purchases before November 1, 2026 use v1 (30 days).
- Purchases on or after November 1, 2026 use v2 (14 days).

Both fixtures define the return window from delivery, not purchase. Purchase date selects the policy version; delivery date is needed to calculate a customer's actual deadline. Keeping those dates separate prevents a subtle application error.

## Missing or conflicting context

Ask for purchase date when it changes the answer. Ask for country/category when needed to choose scope. Do not apply a US footwear policy to another scope silently.

If multiple incompatible authoritative policies match, flag the conflict for review rather than inventing precedence. If none match, acknowledge missing evidence. Never fill the gap with model memory.

## Citation contract

Return policy ID, version and passage ID with each policy claim. A citation must refer to a retrieved, applicable passage, and the text must support the claim. A citation's presence alone does not prove correctness.

## Tradeoff and next work

Explicit metadata reduces applicability mistakes but requires accurate policy ingestion and maintained date boundaries. The first implementation should validate intervals and test boundaries before adding embeddings or model generation. Evaluate retrieval eligibility separately from answer faithfulness.
