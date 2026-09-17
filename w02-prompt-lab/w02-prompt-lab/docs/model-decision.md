# Model Decision Record

Date: 2026-09-16
Author: Atharva
Status: accepted for this lab
Run ID: `day5-full`

Use this file to record the task-level decision after reviewing the measured comparison. Do not select one universal model solely because it leads on a different task.

## Constraints

These constraints were fixed before the run. They are not rewritten from the scores.

- Deployment: local Ollama only. `provider = "ollama"`. Model identity comes from configuration (`model_id`). No cloud credential, and no Anthropic / Azure OpenAI / other hosted-API candidate.
- Cost: `cost_usd = 0.0` on every recorded call. Do not invent a commercial token price or a provider-dollar comparison.
- Comparison axes: quality counts with denominators, input/output tokens per case, median, maximum, and **total** task latency with `n`, repair rate, transport retries, and final failures. Mean latency is not a headline number. Total latency is the sum of every recorded attempt for that task and model, including repairs.
- Sample: 12 cases per task. Results are directional, not production-scale estimates. No production-volume reliability claim.
- Prompting: each row names its prompt version. A Qwen row that reuses the Mistral-tuned prompt is a prompt-transfer result, not an adapted-prompt result.
- Human boundary: no committed `draft_reply` may promise a refund, approve or deny a claim, state that the issue is resolved, or imply a final customer outcome.
- Architecture: the model extracts; Python validates and scores. `select_current_version` decides document currency. Scoring does not call a model.

## Candidates

- Mistral (configured local Ollama model)
- Qwen (configured local Ollama model)

Prompt versions in scope for the final comparison: `summarize.v1`, `extract.v2`, `triage.v1`. Qwen runs of those same files are labeled `transfer`.

## Eliminated on hard constraints

Neither local candidate is eliminated. Both are Ollama, both are `cost_usd = 0.0`, both accept the text cases, and both were available for the run.

Not in the candidate set (untested, not rejected after measurement):

- any cloud model
- an adapted Qwen prompt for any task
- `extract.v3`, `extract.v1`, `baseline.v0`
- `triage.v2` (Day 4 kept `triage.v1`; Day 5 did not re-run v2)

## Evidence

Source: `docs/day5-run.jsonl` and `docs/day5-scores.jsonl`, run_id `day5-full`. Full tables: `reports/comparison.md`. Every row names the prompt version.

| Task | Model | Prompt version | Quality (valid) | Task-specific counts | Tokens in/out per case | Median / max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| summarization | Mistral | `summarize.v1` | 11/12 | recall 55/60; citations 56/57; missed 5/60; invented 3/12; version 0/1; PII 0/12 | 1119.4 / 308.8 | 13359 / 15597 ms | 160280 ms (160.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| summarization | Qwen | `summarize.v1 transfer` | 11/12 | recall 55/60; citations 56/56; missed 5/60; invented 2/12; version 1/1; PII 0/12 | 964.2 / 261.1 | 12447 / 15527 ms | 151322 ms (151.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| extraction | Mistral | `extract.v2` | 12/12 | recall 71/72; citations 73/73; missed 1/72; invented 2/12; version 0/1; PII 0/12 | 1900.9 / 403.2 | 18869.5 / 20930 ms | 225871 ms (225.9 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| extraction | Qwen | `extract.v2 transfer` | 12/12 | recall 71/72; citations 73/73; missed 1/72; invented 2/12; version 1/1; PII 0/12 | 1606.9 / 284.7 | 15112 / 18085 ms | 181541 ms (181.5 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| triage | Mistral | `triage.v1` | 12/12 | routing 9/12; escalation 11/12; missed 0/12; unnecessary 1/12; human-boundary 12/12; PII 1/12 | 455.2 / 159.2 | 5804 / 8024 ms | 75782 ms (75.8 s) | 13 | 1/12 | 0 | 0 | $0.00 |
| triage | Qwen | `triage.v1 transfer` | 12/12 | routing 8/12; escalation 11/12; missed 0/12; unnecessary 1/12; human-boundary 12/12; PII 0/12 | 364.6 / 120.0 | 5275 / 8259 ms | 64691 ms (64.7 s) | 12 | 0/12 | 0 | 0 | $0.00 |

Notes on the evidence:

- Mistral summarization S04 and Qwen summarization S09 failed schema validation after one structured repair (the `1/12` final failures and `n = 13`). Those repair calls are included in total latency.
- Extraction version selection is `select_current_version` on `E01`/`E02` (`as_of=2025-06-01`, expected current `E02`). Mistral `0/1` is bad extraction of version/date evidence.
- Mistral triage T06 needed one structured repair and still validated (`n = 13`; extra call in total latency). Mistral PII leakage is T11 (`draft_reply` copied `8812046631`).
- Transport retries were **0** on every row. Extra calls this run were structured-output repairs only.
- Local Ollama latency depends on lab hardware. Total latency is the sum of recorded model-call attempts for that task and model.

## Decision

Per task, not one model for every task:

- **Summarization:** Mistral + `summarize.v1`. Quality is tied at `11/12`; the Qwen row is an unadapted transfer; a one-case invented/unsupported gap is not a ranking.
- **Extraction:** Qwen + `extract.v2 transfer`. Quality is tied at `12/12`; version selection is `1/1` versus Mistral `0/1`.
- **Triage:** Qwen + `triage.v1 transfer`. Human boundary is `12/12` on both models; PII is `0/12` versus Mistral `1/12`; routing `8/12` versus `9/12` is one case, not a ranking.

## Rejected alternatives

- **One universal model.** Qwen is not selected for summarization, and Mistral is not selected for extraction or triage. A lead on one task is not applied to the others.
- **Qwen + `summarize.v1 transfer` for summarization.** Same `11/12` quality and same `55/60` recall. Invented `2/12` versus `3/12` is one case. The row is transfer, not an adapted Qwen prompt, so it is not treated as a general Qwen win.
- **Mistral + `extract.v2` for extraction.** Tied quality, recall, citations, missed values, and invented values. Rejected because version selection failed (`0/1`) from incomplete version/date extraction.
- **Mistral + `triage.v1` for triage.** Routing is one case higher (`9/12` versus `8/12`). Rejected because T11 leaked PII and T06 needed a structured repair. Human-boundary compliance does not separate the rows (`12/12` both).
- **`triage.v2`, `extract.v3`, and adapted Qwen prompts.** Not measured in this comparison, so they are untested combinations, not scored rejections.
- **Any cloud model or invented token price.** Outside the local-Ollama constraint. Cost remains `$0.00`.

## Review triggers

Re-open the decision when any of these is true (conditions, not a calendar date):

- An adapted Qwen prompt is written and remeasured for a task that currently uses a transfer row.
- `extract.v3` or `triage.v2` is run through this harness and scored against the same gold labels.
- Mistral extraction of `version` and `effective_date` on the `E01`/`E02` group becomes complete enough for `select_current_version` to return `E02`.
- Mistral T11 no longer copies an account number into `draft_reply`.
- Summarization schema failures change (S04 and/or S09 validate, or additional cases fail).
- The triage routing gap grows beyond one case, or human-boundary compliance falls below `12/12` on either model.
- The pinned Ollama model ids change, or the case set grows beyond these 12 cases per task.
- Production volume, residency, or a non-zero provider price becomes a real constraint. This lab still does not invent that price.
