# Model Decision Record

Run ID: `day5-full`

Use this file to record the task-level decision after reviewing the measured comparison. Do not select one universal model solely because it leads on a different task.

## Evaluated models

- mistral
- qwen

## Evaluated configurations

- `extraction` — mistral — `extract.v2`
- `extraction` — qwen — `extract.v2 transfer`
- `summarization` — mistral — `summarize.v1`
- `summarization` — qwen — `summarize.v1 transfer`
- `triage` — mistral — `triage.v1`
- `triage` — qwen — `triage.v1 transfer`

## Task decisions

For each task, complete:

- selected model
- prompt version
- measured reason
- rejected alternative(s)
- condition that would reopen the decision
