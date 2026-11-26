# Sample data source and transformations

## Source

- Dataset: [Card Transactions — synthetic fraud dataset for SQL practice](https://github.com/goktugozdem2/card-transactions-sql-dataset)
- License: [CC0 1.0 Universal](https://github.com/goktugozdem2/card-transactions-sql-dataset/blob/main/LICENSE)
- Source revision used: [`a552cec9fc337d4fc6192350fbed45d4fb091ea5`](https://github.com/goktugozdem2/card-transactions-sql-dataset/commit/a552cec9fc337d4fc6192350fbed45d4fb091ea5)
- Source files: [`transactions.csv`](https://raw.githubusercontent.com/goktugozdem2/card-transactions-sql-dataset/main/transactions.csv), [`accounts.csv`](https://raw.githubusercontent.com/goktugozdem2/card-transactions-sql-dataset/main/accounts.csv), [`merchants.csv`](https://raw.githubusercontent.com/goktugozdem2/card-transactions-sql-dataset/main/merchants.csv), and [`chargebacks.csv`](https://raw.githubusercontent.com/goktugozdem2/card-transactions-sql-dataset/main/chargebacks.csv)
- The upstream README reports 2,165 transaction rows, 200 accounts, 25 merchants and 76 chargebacks. It says the data is generated with a fixed seed and contains planted analytics scenarios.

## Included data

`transactions.csv` joins transaction rows to merchant name/category/country and account country. Account IDs are pseudonymized as `ACCT-###`. Account email and IP fields are omitted. The public source is explicitly synthetic; no real card data is included.

The app derives a rolling one-hour count, prior transaction median per account, whether the source device fingerprint is shared by multiple accounts, and prior chargebacks opened within 30 days before a transaction. These values are illustrative features computed from this sample, not production feature definitions.

Each transaction also carries its matching source chargeback reason/status as a post-transaction outcome. Fraud-prefixed dispute reasons are shown as “fraud-coded dispute”; other disputes remain separate; no recorded chargeback is not proof of a legitimate transaction. Outcome fields are not read by the risk-scoring function.

The upstream file does not provide currency or payment channel. Amounts are therefore presented as source units with no currency symbol, and channel is not scored. Country mismatch is merchant country versus account country. This is a dataset-derived proxy, not a geolocation or cross-border authorization feature.