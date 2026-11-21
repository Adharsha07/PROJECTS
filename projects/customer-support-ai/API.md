# Local policy API milestone

Status: source published; implemented and tested locally. Not deployed to public hosting. Python 3.9+; standard library only.

## Start and test

From this directory:

```sh
python3 api.py --port 8766
```

Run `python3 -m unittest -v` separately. The suite has 36 test methods, including 11 real HTTP tests and the existing acceptance-case subtests. HTTP tests open a temporary loopback port and close the server afterward.

Open the server's printed local address in a browser to use the form. GET / and GET /api/answer serve the form; POST /api/answer processes submitted questions.

## Request contract

`POST /api/answer`, Content-Type `application/json`:

```json
{
  "question": "What is the return window?",
  "context": {
    "purchase_date": "2026-10-25",
    "country": "US",
    "category": "footwear"
  }
}
```

Context is optional: missing information produces clarification, not invented values. Supported context keys: purchase_date, delivery_date, country, category. Dates use YYYY-MM-DD. All values must be strings. Unknown request fields are rejected. Question length is limited to 2000 characters and body size to 16 KiB.

## Response behavior

- 200: handled question, including answered, clarify, insufficient_evidence, unavailable or unsupported results. Inspect the body status; HTTP success does not mean the assistant found an answer.
- 400: invalid JSON, unsupported fields or wrong types.
- 413: oversized body.
- 415: unsupported media type.
- 422: invalid domain input such as a malformed purchase date.
- 500: policy-service failure; no answer produced and internal details omitted.
- GET /health: service availability and model_connected=false.

Responses include answer, sources, status and validation. Cited sources carry policy identity, version, passage identity, text and structured facts when supplied by the fixture.

## Pipeline and why

HTTP handler -> validate request -> retrieve applicable evidence -> return verified passage.

The default path has no model. It reports generation=disabled and validation=verified_passage when answering. The internal answer_request function accepts a future trusted server-side generator callback: its proposed structured facts pass through checked_answer; mismatches or generation exceptions fall back to the original retrieved passage. Clients cannot submit candidates through the public endpoint. Tests exercise this optional path using local callbacks; no external API is called.

The endpoint and business logic are separate so a later framework or interface can reuse the same behavior. This is a small local development API, not a production service. No authentication, database, rate limiting, TLS, production deployment, model integration is provided; a local web form is included. It binds to localhost, does not enable CORS and does not log customer question bodies. Do not expose it publicly as a production server.
