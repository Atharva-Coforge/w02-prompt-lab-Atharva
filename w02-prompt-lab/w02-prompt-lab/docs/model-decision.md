# Model Decision Record

Date: 2026-09-16
Author: Atharva
Status: accepted for this lab
Run ID: `day5-full`

This record fixes a per-task model and prompt version from the measured comparison in `reports/comparison.md`. Task decisions are made independently. No task inherits a conclusion because a model led on a different task.

## Constraints

These constraints were fixed before the run. They are not rewritten to match the scores.

- **Deployment:** local Ollama only. `provider = "ollama"` on every call, and model identity comes from configuration (`MODEL_A`, `MODEL_B` resolved into `model_id`). No cloud credential is required or committed, and no hosted-API candidate was considered.
- **Cost:** `cost_usd = 0.0` on all 75 recorded calls. No commercial token price is invented and no provider-dollar comparison is made.
- **Comparison axes:** quality as counts with denominators; input and output tokens per case; median, maximum, and total latency with an observation count `n`; repair rate; transport retries; final failures. Mean latency is not a headline number.
- **Sample:** 12 cases per task per model. Results are directional. No production-volume reliability claim.
- **Prompting:** every row names its prompt version. A Qwen row that reuses the same prompt file without adaptation is a prompt-transfer result, labeled `transfer`, and is not an adapted-prompt result.
- **Human boundary:** no committed `draft_reply` may promise a refund, approve or deny a claim, state that the issue is resolved, or imply a final customer outcome.
- **Architecture:** the model supplies evidence; Python validates and scores. `select_current_version` decides which document is current. No prompt asks a model to judge document currency, and scoring calls no model.

## Candidates

- Mistral — configured local Ollama model (`MODEL_A`)
- Qwen — configured local Ollama model (`MODEL_B`)

Prompt versions in scope: `summarize.v1`, `extract.v2`, `triage.v1`. Qwen runs of those same files are labeled `transfer`.

## Eliminated on hard constraints

Neither candidate is eliminated. Both run under local Ollama, both record `cost_usd = 0.0`, both accepted every case, and both were available for the full run.

Not in the candidate set — untested here, not rejected after measurement:

- any cloud model
- an adapted Qwen prompt for any task
- `extract.v3`, `extract.v1`, `baseline.v0`
- `triage.v2` (Day 4 kept `triage.v1`; Day 5 did not re-run v2)

## Evidence

Source: `docs/day5-run.jsonl` (75 call records) and `docs/day5-scores.jsonl` (340 score records), both under run_id `day5-full`. Full tables and per-case detail: `reports/comparison.md`. Every score record joins to a call record on run id, task, case id, and model id.

| Task | Model | Prompt version | Quality (valid) | Task-specific counts | Tokens in/out per case | Median / max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| summarization | Mistral | `summarize.v1` | 11/12 | recall 55/60; citations 56/57; missed 5/60; invented 3/12; version 0/1; PII 0/12 | 1119.4 / 308.8 | 13392 / 15615 ms | 160542 ms (160.5 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| summarization | Qwen | `summarize.v1 transfer` | 11/12 | recall 55/60; citations 56/56; missed 5/60; invented 2/12; version 1/1; PII 0/12 | 964.2 / 261.1 | 12391 / 15281 ms | 150311 ms (150.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| extraction | Mistral | `extract.v2` | 12/12 | recall 71/72; citations 73/73; missed 1/72; invented 2/12; version 0/1; PII 0/12 | 1900.9 / 403.2 | 18658 / 20635 ms | 224361 ms (224.4 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| extraction | Qwen | `extract.v2 transfer` | 12/12 | recall 71/72; citations 73/73; missed 1/72; invented 2/12; version 1/1; PII 0/12 | 1606.9 / 284.7 | 14881 / 18043 ms | 178994 ms (179.0 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| triage | Mistral | `triage.v1` | 12/12 | routing 9/12; escalation 11/12; missed 0/12; unnecessary 1/12; human-boundary 12/12; PII 1/12 | 455.2 / 159.2 | 5618 / 7604 ms | 73937 ms (73.9 s) | 13 | 1/12 | 0 | 0 | $0.00 |
| triage | Qwen | `triage.v1 transfer` | 12/12 | routing 8/12; escalation 11/12; missed 0/12; unnecessary 1/12; human-boundary 12/12; PII 0/12 | 364.6 / 120.0 | 5240 / 8426 ms | 64527 ms (64.5 s) | 12 | 0/12 | 0 | 0 | $0.00 |

Notes on the evidence:

- Mistral `S04` and Qwen `S09` failed schema validation after one structured repair each. Those are the `1/12` repair rates, the `1` final failure, and the extra attempt that makes `n = 13` on both summarization rows. All 5 missed values on each row come from that one failed case.
- Mistral triage `T06` needed one structured repair and then validated, so the row is `12/12` valid with `n = 13`. The repair call is included in total latency.
- Transport retries were **0** on every row: all 75 records are `attempt = 1` with no error. Every extra call in this run was a structured-output repair.
- Missed evidence and invented/unsupported evidence are separate field-slot counts. Invented/unsupported is recorded as `unsupported_field_avoidance`: 9/12 slots avoided by Mistral on summarization, 10/12 by Qwen, and 10/12 by both on extraction.
- Version selection is `select_current_version`, not a model opinion. Summarization uses the `card-dispute-intake` group (`S01`/`S02`, `as_of=2025-06-01`, expected `S02`); extraction uses `small-business-periodic-kyc` (`E01`/`E02`, `as_of=2025-06-01`, expected `E02`). Each row is stored under the expected case id with the group name in `detail`. Both Mistral misses are recorded as `cause=bad_extraction`.
- Mistral triage `T11` copied account number `8812046631` into `draft_reply`, which is the single PII leak in the run.
- Both models over-escalated only `T09`. Neither missed a required escalation.
- Latency depends on lab hardware. Total latency is the sum of every recorded attempt for the row.

## Decision

Three independent per-task decisions. All three select Qwen, which is the outcome of three separate comparisons rather than a choice to standardize on one model. Each task is justified only by its own measurements, and each pick rests on an unadapted prompt-transfer row.

- **Summarization:** Qwen + `summarize.v1 transfer`. Quality and recall are tied; Qwen leads on citation correctness, invented values, version selection, tokens, and latency; nothing measured favors Mistral.
- **Extraction:** Qwen + `extract.v2 transfer`. Every quality axis is tied; version selection separates the rows `1/1` against `0/1`, and that output is what the currency rule consumes.
- **Triage:** Qwen + `triage.v1 transfer`. Human boundary is `12/12` on both; Qwen leaks no PII where Mistral leaks one case; Mistral's one-case routing lead does not outweigh a leaked account number.

## Rejected alternatives

- **Mistral + `summarize.v1` for summarization.** Tied on quality (`11/12`) and recall (`55/60`). Rejected because Qwen matched or beat it on every remaining measured axis: citations `56/56` against `56/57`, invented `2/12` against `3/12`, version selection `1/1` against `0/1`, and lower tokens and median latency. Keeping Mistral here would have required an argument that is not about measurement.
- **Mistral + `extract.v2` for extraction.** Tied on quality, recall, citations, missed values, and invented values, with no repairs on either row. Rejected on version selection (`0/1`), caused by incomplete `version` and `effective_date` extraction, which breaks the downstream currency rule.
- **Mistral + `triage.v1` for triage.** Holds a one-case routing lead (`9/12` against `8/12`). Rejected because it leaked PII on `T11` and needed a structured repair on `T06`, while escalation counts and human-boundary compliance are identical.
- **Declaring one universal model on principle.** Not done. Each task was argued from its own counts. The three decisions agreeing on Qwen is a measured result, and any one of them can reopen without disturbing the other two.
- **Treating version selection as important for extraction but incidental for summarization.** Rejected as reasoning backwards from a preferred answer. `SummarizationOutput` and `PolicyExtraction` both carry `version` and `effective_date` as first-class evidence fields, so the metric means the same thing on both tasks.
- **`triage.v2`, `extract.v3`, and adapted Qwen prompts.** Not measured in this comparison, so they are untested combinations rather than scored rejections.
- **Any cloud model, or a comparison in provider dollars.** Outside the local-Ollama constraint. Cost stays `$0.00` and no price is invented.

## Review triggers

Re-open the decision when any of these becomes true. These are conditions, not a calendar date.

- An adapted Qwen prompt is written and measured for any task. All three current picks are unadapted transfer rows, so this trigger applies to every one of them.
- Mistral supplies parseable `version` and `effective_date` evidence so `select_current_version` returns `S02` for the summarization group or `E02` for the extraction group.
- Mistral triage `T11` stops copying an account number into `draft_reply`.
- `extract.v3` or `triage.v2` is run through this harness and scored against the same gold labels.
- The summarization schema failures change: `S04` or `S09` starts validating, or additional cases start failing.
- The triage routing gap grows beyond one case, or human-boundary compliance falls below `12/12` on either model.
- The version groups grow beyond one document pair per task, giving `version_selection_accuracy` a denominator above 1.
- The pinned Ollama model ids change, or the case set grows beyond 12 cases per task.
- Production volume, data residency, or a non-zero provider price becomes a real constraint. This lab still does not invent that price.
