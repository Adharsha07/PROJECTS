# Evidence shopping assistant — milestone 1

A local, browser-based learning prototype using fictional shoe products and reviews. No API keys, packages, AI model, or network services required.

## Try it

From this directory run `npm start`, then open http://127.0.0.1:8765. Run `npm test` for the evidence behavior checks (Node 18+). Python 3 serves the static files.

Choose a product, activity and duration, then select **Examine the evidence**. This milestone uses structured questions, exact filters, duration ranking, and answer templates. It does not yet perform free-text interpretation, semantic search or LLM generation.

## Why this architecture

1. Select an exact product: ambiguity cannot quietly change which shoe we discuss.
2. Describe activity and duration: relevance depends on intended use, not star ratings.
3. Filter by activity and rank by distance from the requested duration. Sentiment never affects rank.
4. Include all reviews within one hour and display every included source. This threshold is a visible teaching assumption, not a validated comfort predictor.
5. Count positive and negative experiences in that complete eligible set. Never present those proportions as the user's probability of comfort.
6. Build an attributed, limited answer. Manufacturer claims remain separate from customer evidence.

All source text is displayed using textContent rather than HTML interpretation. Nothing is stored or sent to an external service.

## Three scenarios to inspect

| Input | Expected behavior |
| --- | --- |
| AB-123 / standing / 8 hours | Two equally relevant but conflicting reviews; show both |
| CD-456 / standing / 8 hours | Two positive, one negative; explain the majority and disagreement |
| EF-789 / standing / 8 hours | No reviews; manufacturer claim cannot establish comfort |

Try changing AB-123 to desk use. The evidence changes because the question changed, not because the program prefers a positive answer.

## Limits and next milestone

The dataset is tiny and fictional; sentiments and usage details are manually labeled. Duration proximity does not establish applicability, and this rule misses useful reviews outside its cutoff. No trustworthiness detection or real product recommendation is implemented. Tests validate these bounded behaviors, not real-world accuracy.

The next milestone can add free-text question interpretation and model-generated answers while preserving the evidence constraints. This repository contains the runnable source; use the commands above to preview it locally.
