# Local policy API and form

Python 3.9+; standard library only. Source is published, public hosting is not configured.

## Run

Start Ollama separately with the installed qwen2.5:1.5b-instruct model. From this directory:

```sh
python3 api.py --port 0 --local-model
python3 -m unittest -v
```

Open the printed address for the browser form. Omit --local-model for the deterministic baseline. A fixed port can be specified instead of 0 if available.

## Routes

- GET / and GET /api/answer serve the form.
- GET /health returns service availability and whether model mode is enabled. It does not probe Ollama; per-answer generation results show actual success or failure. The legacy model_connected field remains false because this health check does not verify connectivity.
- POST /api/answer accepts JSON with question and optional context. Context keys: purchase_date, delivery_date, country, category. Dates use YYYY-MM-DD. Values must be strings. Questions are limited to 2000 characters and bodies to 16 KiB. Extra fields are rejected; clients cannot supply model candidates.

## Responses

200 means the question was handled, not necessarily answered. Inspect body status: answered, clarify, insufficient_evidence, unavailable, unsupported or conflict. Sources include version, passage identity, source text and structured facts where available.

400: malformed JSON or request fields. 413: body too large. 415: wrong content type. 422: invalid purchase data. 500: service failure without private exception details.

Validation can be passed, fallback, verified_passage or not_applicable. Generation can be structured, failed, skipped or disabled. Model time measures the attempted inference call, not total end-to-end latency.

## Pipeline and boundaries

Request validation -> deterministic applicability and passage selection -> optional local model extraction -> fact validation -> controlled sentence or original-passage fallback.

The model sees selected passage text and identifiers, not the expected structured facts. It does not rewrite arbitrary prose, perform semantic search, or interpret every paraphrase. Condition claims bypass this return-window adapter. Model failure does not suppress an otherwise valid retrieved passage.

40 automated test methods passed, including 11 HTTP methods and local adapter mocks. Two policy versions were also exercised with real model inference in the browser. Further model evaluation is required.

This localhost-only development server has no authentication, database, TLS, production hosting or rate limiting. It does not enable CORS or log customer request bodies. Do not expose it as a production service.
