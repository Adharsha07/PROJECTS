"""Run with python3 check.py; no third-party dependencies."""
import math
from search import DOCUMENTS, search, similarity, tokenize

assert tokenize("Hello, WORLD!") == ["hello", "world"]
assert math.isclose(similarity("a a b", "a a b"), 1.0)
assert similarity("", "data") == 0
assert similarity("data", "") == 0
assert search("", DOCUMENTS) == []
assert search("zzzz", DOCUMENTS) == []
results = search("machine learning data", DOCUMENTS)
assert results[0][1] == DOCUMENTS[1]
assert math.isclose(results[0][0], 3 / math.sqrt(24))
assert search("PYTHON", DOCUMENTS)[0][1] == DOCUMENTS[0]
assert len(search("data", DOCUMENTS, limit=1)) == 1
print("All 10 checks passed.")
