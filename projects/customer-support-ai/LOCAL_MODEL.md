# Local model integration

Status: source published and verified through local inference. Hosting remains local. No hosted model service or API key is used.

## Run

With Ollama running and qwen2.5:1.5b-instruct already installed:

```sh
python3 api.py --port 0 --local-model
```

Open the printed address. Without --local-model, the original deterministic baseline remains available.

## Architecture and limits

Browser -> local Python HTTP API -> deterministic policy selection -> Ollama loopback API -> structured claim validation -> controlled sentence or verified-passage fallback.

The adapter extracts return-window facts from the selected passage text. Expected facts are not included in the model input. It does not implement semantic retrieval, improve question routing, generate unrestricted prose, or perform order actions. Other claim types skip model extraction and retain the verified passage. No claim of general quality improvement is made.

The adapter is pinned to the installed local model and a fixed loopback address; it ignores proxy settings. It requests JSON-schema output, uses a bounded context/output length and timeout, and rejects incomplete or malformed responses. Generation failures preserve the verified passage. Schema compliance does not prove factual correctness, hence the separate validator.

## Verification

40 automated test methods passed, including HTTP checks, local adapter mocks and validation failures. Live model smoke checks accepted both the older 30-day and newer 14-day policies. Browser requests measured about 2.0 seconds and 1.2 seconds respectively in this session; these are individual observations, not reproducible performance benchmarks. First direct inference took about 3.2 seconds. Model extraction failures must be evaluated separately from correct fallback answers.

The model-enabled server is left running for review. No model weights, credentials, browser screenshots or machine-specific session identifiers need to be committed to the source repository.
