# Sentinel Fraud Intelligence — runnable prototype

A static investigator workbench for transaction triage. It combines explainable risk signals, mock policy evidence retrieval and a cited investigation draft in one browser UI. The demo is published on GitHub Pages; scoring and retrieval run in the browser.

> **Demo only:** the transactions and merchants come from a public synthetic dataset. Policy excerpts and investigator recommendations are fictional. The score is a hand-authored heuristic, not a trained or validated fraud model. The prototype does not authorize, block, reverse or dispute payments. Do not use it with real customer or payment data.

## Open the hosted demo

After the GitHub Pages workflow completes, the demo will be available at:

[Sentinel Fraud Intelligence](https://adharsha07.github.io/ai-engineering-experiments/projects/fraud-intelligence/)

## Run locally

Requires Python 3.10+ for its built-in static file server; there are no package dependencies.

```sh
cd projects/fraud-intelligence
python3 -m http.server 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop with `Ctrl+C`.

## What you can try

- Filter and search the transaction review table, sorted by explainable risk score.
- Open any transaction to see the signals that contributed to its score.
- Review policy excerpts selected by overlapping signal tags; each excerpt carries a demo source ID and title.
- Copy a concise investigation draft or export the synthetic transaction list as CSV.

## Demo data

- `data/transactions.csv` contains all 2,165 transactions from the [Card Transactions synthetic fraud dataset](https://github.com/goktugozdem2/card-transactions-sql-dataset). The upstream repo publishes 2,165 transaction rows, 200 accounts, 25 merchants and 76 chargeback records; its `LICENSE` dedicates the work to the public domain under CC0 1.0.
- `data/policies.json` contains three fictional policy excerpts tagged for retrieval. They are examples, not bank policy.
- `data/SOURCE.md` documents the source files, transformations and field limits. Account email and IP fields were excluded. The source does not provide transaction currency or payment channel, so the app displays source amount units and does not score on channel.
- The upstream data is synthetic. A recorded dispute is not a complete fraud label, so dispute outcomes are shown only as post-transaction context and are excluded from the heuristic score.

## How scoring works

The browser adds weighted points for amount relative to the account's prior median, one-hour authorization velocity, a device shared across accounts, cross-border activity and prior dispute history. The UI shows the resulting 0–99 score and each contributing reason. Risk bands are low (<35), medium (35–59) and high (60+). These thresholds and weights are illustrative. Transaction outcomes recorded after the event are not score inputs.

Policy evidence is selected from the local JSON file by overlap between signal tags and policy tags. The investigator draft includes the evidence identifiers and suggested next step. It is an aid for human review and takes no financial action.

## Architecture path toward AWS

This static app is a front-end prototype. A production design could move the scoring and data access behind managed services while preserving human review:

- Ingestion: payment processor events through Amazon MSK or Kinesis Data Streams, with schema and idempotency checks.
- Storage: encrypted S3 lake zones plus a governed transaction store such as Aurora or DynamoDB, depending on access patterns.
- Detection: versioned SageMaker model endpoint combined with separately auditable rules; log features, model version and explanations.
- Evidence: approved policies in S3, indexed in Amazon OpenSearch Serverless or Bedrock Knowledge Bases with document version, access controls and citations.
- Orchestration: Step Functions for repeatable case workflow; Bedrock agents only for bounded evidence gathering and report drafting.
- Operations: investigator approval gates, immutable CloudTrail/audit records, least-privilege IAM, KMS encryption, PII minimization and model drift/quality monitoring.

Do not connect this prototype directly to a payment action. A production rollout needs institution-specific validation, security review, compliance approval, representative evaluation data, bias and drift monitoring, and explicit investigator controls.