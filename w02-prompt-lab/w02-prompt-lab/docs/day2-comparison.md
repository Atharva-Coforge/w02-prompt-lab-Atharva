# Day 2 comparison

Same baseline prompt (`baseline` / `v0`), same twelve summarization cases (S01–S12), and one `run_id`. For each case, `task`, `case_id`, `prompt_id`, `prompt_version`, `temperature` (`0.0`), and `max_output_tokens` were identical for both models. Both records use `provider="ollama"` and are distinguished by configured `model_id`. Local provider charge is `cost_usd = 0.0` for every record. No per-token price is assigned.

## Output ceiling

Day 1 extraction used `max_output_tokens = 256` on Mistral and completed without truncation. Day 2 reused that ceiling first, then raised it. Both models always shared the same value.

| Ceiling | Mistral successes | Qwen successes | Notes |
| --- | ---: | ---: | --- |
| 256 | 12 / 12 | 0 / 12 | Every Qwen call hit `stop_reason="length"` (`TruncatedResponseError`). Mistral finished in 1,125 output tokens total, well under 256 per case. |
| 512 | 12 / 12 | 11 / 12 | Qwen S06 still truncated at 512 output tokens. The other eleven Qwen cases returned `stop_reason="stop"`. |

The 256 pass is `runs/4f3ba377-67ee-4e5d-8390-b1290d36717b.jsonl`. The delivered evidence is `docs/day2-run.jsonl` (`run_id=7032bb86-45a2-4c8f-a760-807381ce9266`).

## Measurements from `docs/day2-run.jsonl`

`max_output_tokens = 512` for every record.

| Model | Successes | Input tokens (sum) | Output tokens (sum) | Median latency (ms) | Max latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `mistral:7b` | 12 / 12 | 2,811 | 1,125 | 5,105.5 | 7,906 |
| `qwen3:8b` | 11 / 12 | 2,427 | 4,822 | 20,704.5 | 26,013 |

The one Qwen failure is S06 (`error_type=TruncatedResponseError`, `output_tokens=512`).

## Observation

A 256-token ceiling that was enough for Day 1 extraction on Mistral was not enough for this summarization prompt on Qwen: Qwen used 4,822 output tokens at the 512 ceiling versus Mistral’s 1,125, and median latency was about four times higher (20,704.5 ms vs 5,105.5 ms). Raising the shared ceiling from 256 to 512 moved Qwen from 0/12 to 11/12 successes without changing the prompt, so the remaining S06 truncation is a token-budget limit, not a missing adapter path.
