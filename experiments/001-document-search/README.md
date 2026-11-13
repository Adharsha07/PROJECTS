# Experiment 001: Build a tiny document search engine

Learn the retrieval step that many AI applications use before generating an answer.

## Run it

Requires Python 3.9 or newer. No packages, account, network access, or API key needed.

From the repository root:

```sh
python3 experiments/001-document-search/search.py "machine learning data"
python3 experiments/001-document-search/check.py
```

The first command ranks the machine-learning note first, with score `0.612`.

## What happens inside?

1. **Tokenize:** lowercase each sentence and split it into words.
2. **Count:** represent each sentence as a bag of word counts.
3. **Compare:** cosine similarity compares the query's counts with each document's counts.
4. **Rank:** return the three highest positive scores.

For example, "machine learning data" shares three words with the machine-learning note. Its score is 3 / sqrt(3 × 8), approximately 0.612. Cosine similarity normalizes by vector lengths so longer text does not automatically win.

Read `tokenize`, then `similarity`, then `search` in search.py. The command-line entry point simply prints the results.

## Why this matters for AI engineering

A retrieval-augmented generation (RAG) system first retrieves relevant text, then gives it to a language model as context. This experiment implements a simple retrieval baseline. It does not call a language model or generate answers.

## Limits

This method matches exact words. It does not understand synonyms, word order, or meaning: "automobile" will not match "car". Its scores measure word overlap, not confidence or factual accuracy. Documents are small and built into the script.

## Your exercise (10 minutes)

Add a fifth note about a topic you know. Predict which query will rank it first, run that query, then try a synonym absent from the note. Explain why the second query behaves differently.

Next experiment idea: compare this baseline with TF-IDF, which gives common words less weight.

## Verification

`check.py` checks ranking, case handling, empty queries, no matches, duplicate words and result limits. Run it to reproduce the checks locally.
