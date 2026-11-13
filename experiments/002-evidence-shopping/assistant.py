"""Evidence handling demo with fictional products; no AI service required."""
import argparse

EVIDENCE = [
    {"id": "spec-ab", "product": "AB-123", "kind": "manufacturer", "topic": "comfort",
     "text": "Advertised as offering all-day comfort."},
    {"id": "review-cd", "product": "CD-456", "kind": "review", "topic": "comfort",
     "text": "Comfortable for two hours; my feet hurt after eight."},
    {"id": "review-ef", "product": "EF-789", "kind": "review", "topic": "comfort",
     "text": "One reviewer reports comfort during an eight-hour shift."},
    {"id": "spec-gh", "product": "GH-000", "kind": "manufacturer", "topic": "color",
     "text": "Available in blue."},
]

def retrieve(product, topic, records):
    # Exact product identity is a constraint, not a similarity score.
    return [r for r in records
            if r["product"] == product and r["topic"] == topic]

def answer(product, topic="comfort", records=None):
    records = EVIDENCE if records is None else records
    sources = retrieve(product, topic, records)
    if not sources:
        message = "I do not have enough evidence about this product's " + topic + "."
    else:
        parts = []
        for source in sources:
            label = ("Manufacturer claim (not independent confirmation)"
                     if source["kind"] == "manufacturer"
                     else "Individual customer report (experiences may vary)")
            parts.append(f"{label}: {source['text']} [{source['id']}]")
        message = "\n".join(parts)
        message += "\nThis does not establish how the product will work for you."
    # Alternatives stay separate and never answer for the requested product.
    alternatives = sorted({r["product"] for r in records
                           if r["product"] != product and r["topic"] == topic
                           and r["kind"] == "review"}) if not sources or all(
                               s["kind"] == "manufacturer" for s in sources) else []
    return {"product": product, "answer": message, "sources": sources,
            "alternatives": alternatives}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", nargs="?", default="AB-123")
    parser.add_argument("--topic", default="comfort",
                        help="Structured topic, e.g. comfort or color")
    args = parser.parse_args()
    result = answer(args.product, args.topic)
    print(f"Requested product: {result['product']}")
    print(result["answer"])
    if result["alternatives"]:
        print("Other products with relevant reviews (not substitutes or recommendations): "
              + ", ".join(result["alternatives"]))

if __name__ == "__main__":
    main()
