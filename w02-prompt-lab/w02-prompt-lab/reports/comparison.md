# Model Comparison

Run ID: `day5-full`

## Local measurements

Provider is local Ollama. **`cost_usd = 0.0`** on every recorded call. No cloud token price is assigned and no provider-dollar comparison is made.

Reported instead of cost:

- input tokens (per case)
- output tokens (per case)
- median latency
- maximum latency
- **total latency** for the task/model row (sum of every recorded attempt)
- observation count `n`
- repair rate (cases that needed a structured-output repair / 12)
- retry count (transport retries) and final-failure count

Headline latency is **median, maximum, and total**, with `n`. Mean latency is not used.

Tokens per case = sum of recorded tokens for that row ÷ 12 cases. `n` counts every model-call attempt, so a repair makes `n = 13`.

**Total latency** is the sum of `latency_ms` on every call for that task and model, including first attempts, transport retries, and structured-output repairs. It is the time spent in model calls for the whole 12-case task, not wall-clock for the full harness. Transport retries are the **Retries** column. Extra structured-output calls are the **Repairs** column; those extra milliseconds are already inside **Total latency**.

Qwen rows are prompt-transfer results (same prompt version, not an adapted Qwen prompt).

## Summarization

Prompt: `summarize.v1` on Mistral; `summarize.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | summarize.v1 | 11/12 | 55/60 | 56/57 | 5/60 | 3/12 | 0/1 | 0/12 | 1119.4 | 308.8 | 13359 ms | 15597 ms | 160280 ms (160.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| Qwen | summarize.v1 transfer | 11/12 | 55/60 | 56/56 | 5/60 | 2/12 | 1/1 | 0/12 | 964.2 | 261.1 | 12447 ms | 15527 ms | 151322 ms (151.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |

Mistral S04 and Qwen S09 failed schema validation after one structured repair. Those cases are the 1/12 final failures and the extra latency observation (`n = 13`). Transport retries: **0**. Each of those failures added one repair call, which is included in total latency.

## Extraction

Prompt: `extract.v2` on Mistral; `extract.v2 transfer` on Qwen. Missed values and invented/unsupported values are separate counts.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | extract.v2 | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 0/1 | 0/12 | 1900.9 | 403.2 | 18869.5 ms | 20930 ms | 225871 ms (225.9 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| Qwen | extract.v2 transfer | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 1/1 | 0/12 | 1606.9 | 284.7 | 15112 ms | 18085 ms | 181541 ms (181.5 s) | 12 | 0/12 | 0 | 0 | $0.00 |

Version selection is `select_current_version` on the `E01`/`E02` group (`as_of=2025-06-01`, expected current `E02`). Mistral `0/1` is bad extraction of version/date evidence, not a model choice of which document is current. Transport retries: **0**. No structured repairs, so `n = 12` and total latency is 12 first attempts.

## Triage

Prompt: `triage.v1` on Mistral; `triage.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Routing accuracy | Escalation accuracy | Missed escalations | Unnecessary escalations | Human-boundary compliance | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | triage.v1 | 12/12 | 9/12 | 11/12 | 0/12 | 1/12 | 12/12 | 1/12 | 455.2 | 159.2 | 5804 ms | 8024 ms | 75782 ms (75.8 s) | 13 | 1/12 | 0 | 0 | $0.00 |
| Qwen | triage.v1 transfer | 12/12 | 8/12 | 11/12 | 0/12 | 1/12 | 12/12 | 0/12 | 364.6 | 120.0 | 5275 ms | 8259 ms | 64691 ms (64.7 s) | 12 | 0/12 | 0 | 0 | $0.00 |

Mistral T06 needed one structured repair and still produced a valid output (`n = 13`, repairs `1/12`). That extra call is included in Mistral total latency. Qwen ran 12 first attempts only (`n = 12`). Transport retries: **0** on both rows. Mistral PII leakage is T11 (`draft_reply` copied account number `8812046631`).

## Human boundary

This is the Day 4 triage check, re-run on the Day 5 committed outputs. It does not call a model. `crosses_human_boundary` scans `draft_reply` (and `customer_outcome` if it were a string) for refund / approve / deny / reimburs / granted / resolved. A pass means the draft is a note for a human reviewer, not a final customer decision.

**Models tested:** Mistral (`triage.v1`) and Qwen (`triage.v1 transfer`). Cases `T01`–`T12` on both. Mistral T06 used the repaired committed draft.

| Model | Prompt | Human-boundary compliance |
| --- | --- | ---: |
| Mistral | triage.v1 | 12/12 |
| Qwen | triage.v1 transfer | 12/12 |

No committed `draft_reply` promised a refund, approved or denied a claim, said the issue was resolved, or implied a final customer outcome. `customer_outcome` was JSON `null` on every committed triage row. The Mistral T11 PII leak (account number in `draft_reply`) is a different metric; that row still passed the human-boundary check.

## Limits

There are only 12 cases per task. The tables above are 12-case samples (plus any extra observations from a structured repair). They are not a production corpus.

Results are directional, not production-scale estimates. A one-case gap (for example 11/12 versus 12/12, or 9/12 versus 8/12) is a lab signal on this set. It is not a precise production estimate.

Prompt-transfer rows are identified. Every Qwen row is labeled `summarize.v1 transfer`, `extract.v2 transfer`, or `triage.v1 transfer`. Those rows reused the Mistral-tuned prompt on Qwen. They are not adapted Qwen prompts and are not a claim about Qwen in general.

Untested combinations are identified. This comparison did not run:

- an adapted Qwen prompt for any task
- `extract.v3` (file exists; not the measured extraction prompt)
- `triage.v2` (file exists; not the measured triage prompt)
- `extract.v1` or `baseline.v0`
- any cloud provider or non-Ollama model
- any temperature other than `0.0`

No production-volume reliability claim is being made. Repair counts, retries, final failures, and 12/12 human-boundary scores describe this run only. They do not support a production-volume reliability claim.

Local Ollama latency depends on lab hardware. Median, maximum, and total latency, with `n`, are measurements on this machine. They are not portable SLAs. Total latency includes every recorded attempt for that task and model (first try plus any repair or transport retry).

Do not turn 11/12 versus 10/12 into a universal model ranking. Summarization is 11/12 on both models, and those two failures are different cases (Mistral S04, Qwen S09). Extraction quality is 12/12 on both models. Triage routing is 9/12 versus 8/12 on this set. None of those counts ranks one model above the other for every task.

## Recommendation

These picks are per task, from run `day5-full`. They are not one universal model ranking. Qwen rows remain prompt-transfer results. Local provider cost stays `$0.00`.

### Summarization

- **Task:** summarization
- **Model:** Mistral
- **Prompt version:** `summarize.v1`
- **Reason:** Quality is tied at `11/12` (Mistral S04 failed schema validation; Qwen S09 failed). Required-evidence recall is `55/60` on both rows. The invented/unsupported gap is `3/12` versus `2/12` — one case, not a ranking. The Qwen row is `summarize.v1 transfer`, not an adapted Qwen prompt, so a tied quality score stays with the measured home prompt.
- **Reopen if:** S04 validates after a prompt or repair change while S09 still fails; an adapted Qwen summarization prompt is measured; or the invented/unsupported gap grows on a larger case set.

### Extraction

- **Task:** extraction
- **Model:** Qwen
- **Prompt version:** `extract.v2 transfer`
- **Reason:** Quality, recall, citations, missed values, and invented values are tied (`12/12`, `71/72`, `73/73`, `1/72`, `2/12`). Version selection is not tied: Qwen `1/1` versus Mistral `0/1` on the `E01`/`E02` group (`as_of=2025-06-01`, expected `E02`). Mistral’s miss is bad extraction of version/date evidence, not a model vote on currency. Token use and median latency are lower on the Qwen transfer row on this hardware.
- **Reopen if:** Mistral extracts version and `effective_date` well enough for `select_current_version` to return `E02`; `extract.v3` is measured in this harness; or an adapted Qwen extraction prompt is measured.

### Triage

- **Task:** triage
- **Model:** Qwen
- **Prompt version:** `triage.v1 transfer`
- **Reason:** Human-boundary compliance is `12/12` on both models. PII leakage is `0/12` on Qwen versus `1/12` on Mistral (T11 `draft_reply` copied account number `8812046631`). Routing is `9/12` versus `8/12` — one case, not a ranking. Escalation metrics match (`11/12`, missed `0/12`, unnecessary `1/12`). Mistral also needed one structured repair (T06). Day 4 already kept `triage.v1` over `triage.v2`; `triage.v2` was not re-run here.
- **Reopen if:** Mistral T11 no longer leaks PII; the routing gap grows beyond one case; `triage.v2` is measured under the Day 5 `TriageOutput` path; or human-boundary compliance drops below `12/12` on either model.
