# Sentinel Fraud Intelligence — runnable prototype

A local investigator workbench for transaction triage. It combines explainable risk signals, mock policy evidence retrieval and a cited investigation draft in one browser UI.

> **Demo only:** every transaction, customer ID, merchant and policy excerpt is fabricated and stored in the local JSON files under `data/`. The score is a hand-authored heuristic, not a trained or validated fraud model. The prototype does not authorize, block, reverse or dispute payments. Do not use it with real customer or payment data.

## Run locally

Requires Python 3.10+; there are no Python package dependencies.

```sh
cd projects/fraud-intelligence
python3 server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop with `Ctrl+C`.

## What you can try

- Filter and search the transaction review table, sorted by explainable risk score.
- Open any transaction to see the signals that contributed to its score.
- Review policy excerpts selected by overlapping signal tags; each excerpt carries a demo source ID and title.
- Copy a concise investigation draft or export the current synthetic transaction list as CSV.

## How scoring works

The Python API adds weighted points for a transaction amount relative to the customer's fabricated usual amount, one-hour authorization velocity, a new device, cross-border country, card-not-present channel and recent dispute history. The UI shows the resulting 0–99 score and each contributing reason. Risk bands are low (<35), medium (35–59) and high (60+). These thresholds and weights are illustrative. A dispute history is explicitly context only, not proof of fraud.

The investigator endpoint is `POST /api/investigate` with `{"transaction_id":"TX-10482"}`. It returns the transaction, heuristic score, signal explanations, relevant policy excerpts, and a suggested next step. `GET /api/transactions` returns the ranked input data with analysis; `GET /api/policies` returns the whole mock policy library.

## Demo data

- `data/transactions.json` contains nine invented card transactions and fabricated customer profile aggregates used by the scoring rules.
- `data/policies.json` contains three fictional policy excerpts tagged for retrieval. They are examples, not bank policy.
- No external dataset, account connection, or customer data is used. The file structure lets you replace fixtures with an approved, appropriately licensed dataset without mixing records into the application logic.

## Architecture path toward AWS

This is intentionally a small local slice. A production design could replace each boundary with managed services while preserving human review:

- Ingestion: payment processor events through Amazon MSK or Kinesis Data Streams, with schema and idempotency checks.
- Storage: encrypted S3 lake zones plus a governed transaction store such as Aurora or DynamoDB, depending on access patterns.
- Detection: versioned SageMaker model endpoint combined with separately auditable rules; log features, model version and explanations.
- Evidence: approved policies in S3, indexed in Amazon OpenSearch Serverless or Bedrock Knowledge Bases with document version, access controls and citations.
- Orchestration: Step Functions for repeatable case workflow; Bedrock agents only for bounded evidence gathering and report drafting.
- Operations: investigator approval gates, immutable CloudTrail/audit records, least-privilege IAM, KMS encryption, PII minimization and model drift/quality monitoring.

Do not connect this prototype directly to a payment action. A production rollout needs institution-specific validation, security review, compliance approval, representative evaluation data, bias and drift monitoring, and explicit investigator controls.