# Evidence shopping assistant — milestone 2

A local, browser-based learning prototype using fictional shoe products and reviews. The default workflow runs without API keys, packages, models, or network services.

## Try it

From this directory run `npm start`, then open http://127.0.0.1:8765. Run `npm test` for the evidence behavior checks (Node 18+). Python 3 serves the static files.

Choose a product, activity and duration, then select **Examine the evidence**. You can also enter a question such as “Shift Walker on my feet for eight hours?” and use **Fill in the question fields** to review the interpretation before submitting.

For optional semantic ranking and a model-assisted summary, run Ollama locally with `OLLAMA_ORIGINS=http://127.0.0.1:8765 ollama serve`, and install the models with `ollama pull nomic-embed-text` and `ollama pull llama3.2`. Then select **Summarize with local models**. The browser sends only the normalized activity and duration and the eligible fictional review text to loopback. Embeddings order the complete eligible set for the summary. The generator returns verbatim review excerpts with citation IDs, and validation requires each eligible review exactly once. The evidence status, counts, and conclusions come from the deterministic engine. Missing evidence skips model calls, and a failed model request leaves the evidence answer available.

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

The interpreter supports a bounded set of catalog names, activities, and hour expressions. Semantic ranking orders only eligible evidence, and the model-assisted summary quotes the reviews.
