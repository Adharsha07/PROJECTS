# Experiment 002: Answer from evidence

## The concept

A useful assistant must distinguish **what a manufacturer claims**, **what a customer experienced**, and **what remains unknown**. Missing evidence does not mean a product is bad.

Think of two separate jobs:
1. Retrieval: find evidence for the correct product and topic.
2. Answering: describe what those sources actually support, with attribution.

An exact product code is a hard constraint. A review of a different shoe cannot establish anything about the requested shoe. Alternatives must be labeled separately.

## Try it

Python 3.9+, no dependencies, API keys or paid services. From the repository root:

```sh
python3 experiments/002-evidence-shopping/assistant.py AB-123
python3 experiments/002-evidence-shopping/assistant.py CD-456
python3 experiments/002-evidence-shopping/assistant.py GH-000
python3 -m unittest discover -s experiments/002-evidence-shopping -v
```

All products and evidence are fictional teaching examples.

| Product | Evidence | What you should observe |
| --- | --- | --- |
| AB-123 | Manufacturer advertises all-day comfort, no reviews | Label it as a claim, not proof of eight-hour comfort |
| CD-456 | Reviewer reports pain after eight hours | Preserve that report without promising comfort |
| GH-000 | Color specification only | Say there is not enough comfort evidence |

The AB-123 example also lists other products with reviews separately. Their inclusion is not an endorsement; reviews can be negative.

## What this implementation demonstrates

This is a deterministic evidence-handling prototype: structured product/topic filtering and template-based responses. It is **not a complete RAG system**, does not use an LLM or embeddings, and does not implement semantic or hybrid search. Those can be added later while retaining these evidence rules.

The program quotes the supplied evidence rather than inferring whether a product is suitable. The topic is an explicit input, not a natural-language question. Source IDs make each claim traceable.

## How we evaluate it

Seven automated tests cover exact identity, source attribution, preserving negative evidence, missing evidence, wrong-product evidence, an empty catalog and conflicting sources.

Passing these tests establishes these example behaviors only. It does not prove the system can handle arbitrary questions or detect unreliable source material.

## Your learning checkpoint

Run the three examples and compare their answers. Why would replacing "manufacturer claims" with "this product guarantees" make the first answer less trustworthy?

Next concept: evaluating retrieval and answers separately on a larger set of examples.
