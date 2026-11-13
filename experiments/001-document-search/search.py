"""A tiny document retriever using bag-of-words cosine similarity."""
import argparse
import math
import re
from collections import Counter

DOCUMENTS = [
    "Python is a programming language used for automation and data analysis.",
    "Machine learning models learn patterns from training data.",
    "Retrieval finds relevant documents before a language model generates an answer.",
    "Git tracks changes in code. GitHub hosts repositories for collaboration.",
]

def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())

def similarity(left, right):
    a, b = Counter(tokenize(left)), Counter(tokenize(right))
    dot = sum(count * b[word] for word, count in a.items())
    norm = math.sqrt(sum(n*n for n in a.values()) * sum(n*n for n in b.values()))
    return dot / norm if norm else 0.0

def search(query, documents, limit=3):
    ranked = sorted(
        ((similarity(query, document), document) for document in documents),
        key=lambda item: item[0], reverse=True,
    )
    return [(score, document) for score, document in ranked if score > 0][:limit]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Words to search for")
    args = parser.parse_args()
    results = search(args.query, DOCUMENTS)
    if not results:
        print("No matching words found. Try a different query.")
    for score, document in results:
        print(f"{score:.3f} | {document}")

if __name__ == "__main__":
    main()
