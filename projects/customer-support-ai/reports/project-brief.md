# Evidence Based Customer Support Assistant

## Project report

### Executive summary

We built a local prototype that answers return-policy questions using fictional store policies. It selects applicable policy evidence, cites the source passage, and checks structured claims against that evidence. If the evidence does not support a claim, the app preserves verified source text.

The main challenge was routing different customer wording safely. The system had to recognize return requests while stopping unrelated product questions, mixed requests, and exact-date questions that the policy cannot calculate.

### What the prototype does

The web interface sends a shopper question to a Python API. The normal app uses a reviewed keyword route and deterministic policy selection. An optional local Qwen classifier identifies request intent. For supported policy questions, the backend retrieves the applicable policy, validates the claim and citation, and returns controlled wording or a verified-passage fallback.

The app does not connect to real orders, authenticate customers, execute refunds, or run as a public website. Its store and policies are fictional.

### Challenges and fixes

| Challenge | What happened | Response |
|---|---|---|
| Literal routing | Keyword rules missed paraphrases such as “send them back.” | Added a bounded request classifier and measured it against new wording. |
| Product questions | Some product-feature questions looked like return questions to the classifier. | Added deterministic scope checks before policy retrieval and kept the model route opt-in. |
| Arrival defects | A detached shoe part was classified as ordinary return condition. | Expanded the arrival-defect cues so unknown exceptions return “not specified” evidence. |
| Exact dates | A request phrased as a calendar cutoff was answered with the general number of days. | Aligned the routing and retrieval deadline checks; exact dates now trigger clarification. |
| Multiple facts and intents | A single return-condition question could be split into two model labels, while a mixed product/return question could be collapsed. | Coalesced condition facts that use the same policy passage and added independent product/return checks. |

### Latest evaluation

The frozen v10 wording set had 50 developer-authored questions. The code was unchanged during the local Qwen run, and no question was copied verbatim into the classifier examples.

| Measure | Result |
|---|---:|
| Exact expected outcomes | 47/50 (94%) |
| Unsupported questions routed to return answers | 0/15 |
| Mixed requests answered as one | 0/10 |
| Supported routes correct | 14/15 (93.3%) |
| Unnecessary clarifications among answerable supported cases | 1/12 (8.3%) |
| Ambiguous questions clarified | 10/10 |
| Automated tests | 70/70 |

All stated numeric prototype thresholds passed. However, one mixed question about cycling suitability and returning the shoes was rejected as unsupported instead of prompting the customer to split the request. The system did not answer the return-policy part, so this was a safe but less helpful outcome. Two other exact mismatches were safe clarifications: one unsupported product-repair question and one return-window paraphrase.

### Evaluation limits

The v10 result comes from one small, developer-authored evaluation using one local model run. It is not production-readiness evidence. A prior v7 run was excluded from holdout claims because one question appeared verbatim in the classifier prompt. The v10 set and detailed outcomes are published with a SHA-256 so the measured inputs can be checked.

Observed mean request time was 0.454 seconds and median was 0.320 seconds in this run. These are one-session observations, not a performance benchmark.

### Main engineering lesson

A model that sounds confident is not enough. The system needs bounded model decisions, authoritative evidence, validation, safe fallbacks, and evaluation measures that distinguish a harmful false answer from an overly cautious clarification. A clean aggregate score can also hide a usability miss, so results should be broken down by question type.

### Next milestone

Keep the model classifier opt-in. The next evaluation should focus on mixed requests that combine product-use questions with return questions, with cases reviewed by someone who did not write the prompt. Do not tune against v10 and then describe the same set as independent evidence.

### How to present the project

> “I built a local evidence-based customer-support assistant. The model helps interpret customer wording, but the backend retrieves the applicable policy, validates the claim and citation, and falls back to verified text when needed. I tested it on a frozen set of 50 questions. It had no unsupported return answers and no mixed request answered as only one part, while supported routing reached 93.3%. One mixed question was safely refused instead of being split, so I kept the model route experimental and identified that as the next evaluation target.”

### Project links

- GitHub project: https://github.com/Adharsha07/PROJECTS/tree/main/projects/customer-support-ai
- v10 cases: https://github.com/Adharsha07/PROJECTS/blob/main/projects/customer-support-ai/holdout-v10-cases.json
- v10 results: https://github.com/Adharsha07/PROJECTS/blob/main/projects/customer-support-ai/holdout-v10-results.json
- Promotion criteria: https://github.com/Adharsha07/PROJECTS/blob/main/projects/customer-support-ai/PROMOTION_CRITERIA.md
