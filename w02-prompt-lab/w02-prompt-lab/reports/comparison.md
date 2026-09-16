# Model Comparison

Run ID: `day5-full`

One table per task. Quality, token usage, latency, and repairs are in the same table. Counts use numerators and denominators, not percentages. Latency is median and maximum with observation count `n`. Mean latency is not used. Local Ollama `cost_usd` is `$0.00`. Qwen rows are prompt-transfer results: the same prompt version, not an adapted Qwen prompt.

Tokens per case are totals for that row divided by 12 cases. `n` is the number of recorded model-call attempts (repairs add extra observations).

## Summarization

Prompt: `summarize.v1` on Mistral; `summarize.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | n | Repairs | Final failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | summarize.v1 | 11/12 | 55/60 | 56/57 | 5/60 | 3/12 | 0/1 | 0/12 | 1119.4 | 308.8 | 13368 ms | 15619 ms | 13 | 1/12 | 1 |
| Qwen | summarize.v1 transfer | 11/12 | 55/60 | 56/56 | 5/60 | 2/12 | 1/1 | 0/12 | 964.2 | 261.1 | 12442 ms | 16050 ms | 13 | 1/12 | 1 |

Mistral S04 and Qwen S09 failed schema validation after one structured repair. Those cases are the 1/12 final failures and contribute the extra latency observation (`n = 13`).

## Extraction

Prompt: `extract.v2` on Mistral; `extract.v2 transfer` on Qwen. Missed values and invented/unsupported values are separate counts.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | n | Repairs | Final failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | extract.v2 | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 0/1 | 0/12 | 1900.9 | 403.2 | 18772 ms | 20763 ms | 12 | 0/12 | 0 |
| Qwen | extract.v2 transfer | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 1/1 | 0/12 | 1606.9 | 284.7 | 14989 ms | 18104 ms | 12 | 0/12 | 0 |

Version selection is `select_current_version` on the `E01`/`E02` group (`as_of=2025-06-01`, expected current `E02`). Mistral `0/1` is bad extraction of version/date evidence, not a model choice of which document is current.

## Triage

Prompt: `triage.v1` on Mistral; `triage.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Routing accuracy | Escalation accuracy | Missed escalations | Unnecessary escalations | Human-boundary compliance | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | n | Repairs | Final failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | triage.v1 | 12/12 | 9/12 | 11/12 | 0/12 | 1/12 | 12/12 | 1/12 | 455.2 | 159.2 | 5723 ms | 8072 ms | 13 | 1/12 | 0 |
| Qwen | triage.v1 transfer | 12/12 | 8/12 | 11/12 | 0/12 | 1/12 | 12/12 | 0/12 | 364.6 | 120.0 | 5278.5 ms | 8250 ms | 12 | 0/12 | 0 |

Mistral T06 needed one structured repair and still produced a valid output (`n = 13`, repairs `1/12`). Mistral PII leakage is T11 (`draft_reply` copied account number `8812046631`). Human-boundary compliance is `12/12` under both models.

Transport retries: `0` on every row. Provider cost: `$0.00`.
