# Model Comparison

Run ID: `day5-full`

Two local Ollama models, three tasks, 12 cases per task per model. Every row names the prompt version it measured.

## What is measured instead of cost

Provider is local Ollama. **`cost_usd = 0.0` on all 75 recorded calls.** No cloud token price is assigned to either model, and no provider-dollar comparison is made.

Reported in place of cost:

- input tokens per case and output tokens per case
- median latency, maximum latency, and total latency, each with an observation count `n`
- repair rate (cases that needed a structured-output repair, over 12)
- transport retry count and final-failure count

Headline latency is median, maximum, and total. Mean latency is not used.

`n` counts model-call attempts, not cases. A case that needed one structured repair contributes two attempts, so a 12-case row with one repair shows `n = 13`. Tokens per case are the recorded tokens for the row divided by 12 cases.

**Total latency** is the sum of `latency_ms` across every call for that task and model, including first attempts, transport retries, and structured-output repairs. It is time spent inside model calls for the whole 12-case task, not wall-clock for the harness.

Qwen rows are prompt-transfer results: the same prompt file, run on Qwen without adaptation. They are labeled `transfer` and are not claims about Qwen with a prompt written for Qwen.

Missed evidence and invented/unsupported evidence are kept as separate counts throughout. Missed evidence is recoverable evidence the model failed to report. Invented/unsupported evidence is a field the model filled that the gold label marks as not recoverable from the source. Both are field-slot counts, not case counts.

## Summarization

Prompt: `summarize.v1` on Mistral; `summarize.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | `summarize.v1` | 11/12 | 55/60 | 56/57 | 5/60 | 3/12 | 0/1 | 0/12 | 1119.4 | 308.8 | 13392 ms | 15615 ms | 160542 ms (160.5 s) | 13 | 1/12 | 0 | 1 | $0.00 |
| Qwen | `summarize.v1 transfer` | 11/12 | 55/60 | 56/56 | 5/60 | 2/12 | 1/1 | 0/12 | 964.2 | 261.1 | 12391 ms | 15281 ms | 150311 ms (150.3 s) | 13 | 1/12 | 0 | 1 | $0.00 |

Mistral `S04` and Qwen `S09` failed schema validation after one structured repair each. Those are the `1/12` repair rate, the `1` final failure, and the extra attempt that makes `n = 13` on both rows. Transport retries were **0**.

All 5 missed values on the Mistral row come from `S04`, and all 5 on the Qwen row come from `S09`, in both cases because the failed output supplied no evidence fields at all.

Citation correctness has different denominators because the rows produced different numbers of present fields. Mistral emitted 57 present-field citations and got 56 right, missing on `S05` (1/2). Qwen emitted 56 and got all 56 right.

Invented/unsupported is recorded as `unsupported_field_avoidance`: Mistral avoided 9 of 12 non-recoverable field slots (filled 3, on `S04`, `S05`, `S09`), Qwen avoided 10 of 12 (filled 2, on `S04` and `S09`).

Version selection is the `select_current_version` rule on the `card-dispute-intake` group (`S01`/`S02`, `as_of=2025-06-01`, expected current `S02`). The score row is recorded under `case_id` `S02` so it joins to call evidence, with the group name kept in `detail` (`group=card-dispute-intake; expected=S02; selected=S02`). Mistral's `0/1` is recorded as `cause=bad_extraction`: it did not supply parseable `version` and `effective_date` evidence for the group. It is not a model opinion about which document is current.

## Extraction

Prompt: `extract.v2` on Mistral; `extract.v2 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Required-evidence recall | Citation correctness | Missed values | Invented/unsupported | Version selection | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | `extract.v2` | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 0/1 | 0/12 | 1900.9 | 403.2 | 18658 ms | 20635 ms | 224361 ms (224.4 s) | 12 | 0/12 | 0 | 0 | $0.00 |
| Qwen | `extract.v2 transfer` | 12/12 | 71/72 | 73/73 | 1/72 | 2/12 | 1/1 | 0/12 | 1606.9 | 284.7 | 14881 ms | 18043 ms | 178994 ms (179.0 s) | 12 | 0/12 | 0 | 0 | $0.00 |

No structured repairs and no transport retries on either row, so `n = 12` and total latency is 12 first attempts.

The single missed value on each row is `E05` (6/7). Both rows filled 2 of 12 non-recoverable field slots, on `E04` and `E10`, so invented/unsupported is tied.

Version selection is `select_current_version` on the `small-business-periodic-kyc` group (`E01`/`E02`, `as_of=2025-06-01`, expected current `E02`), recorded under `case_id` `E02` with `group=small-business-periodic-kyc` in `detail`. Mistral's `0/1` is `cause=bad_extraction` — missing or unparseable `version` and `effective_date` evidence, not a currency judgment by the model.

## Triage

Prompt: `triage.v1` on Mistral; `triage.v1 transfer` on Qwen.

| Model | Prompt | Quality (valid) | Routing accuracy | Escalation accuracy | Missed escalations | Unnecessary escalations | Human-boundary compliance | PII leakage | Input tokens/case | Output tokens/case | Median latency | Max latency | Total latency | n | Repairs | Retries | Final failures | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mistral | `triage.v1` | 12/12 | 9/12 | 11/12 | 0/12 | 1/12 | 12/12 | 1/12 | 455.2 | 159.2 | 5618 ms | 7604 ms | 73937 ms (73.9 s) | 13 | 1/12 | 0 | 0 | $0.00 |
| Qwen | `triage.v1 transfer` | 12/12 | 8/12 | 11/12 | 0/12 | 1/12 | 12/12 | 0/12 | 364.6 | 120.0 | 5240 ms | 8426 ms | 64527 ms (64.5 s) | 12 | 0/12 | 0 | 0 | $0.00 |

Mistral `T06` needed one structured repair and then validated, so its row is `12/12` valid with `1/12` repairs and `n = 13`. That extra call is inside Mistral's total latency. Qwen ran 12 first attempts only. Transport retries were **0** on both rows.

Routing misses are `T06`, `T07`, and `T11` on Mistral, and `T07`, `T08`, `T09`, and `T11` on Qwen. Both models over-escalated the same single case, `T09` (predicted escalation `True`, expected `False`), which is the `1/12` unnecessary escalation and the one point lost from escalation accuracy. Neither model missed a required escalation.

Mistral's PII leak is `T11`: `draft_reply` copied the account number `8812046631` out of the source. Qwen did not leak on any case.

## Human boundary

This is the Day 4 triage boundary check, re-run on the Day 5 committed outputs. It calls no model. `crosses_human_boundary` scans `draft_reply` and `customer_outcome` for refund, approve, deny, reimburse, granted, and resolved. A pass means the draft reads as a note for a human reviewer rather than a final decision to the customer.

Models tested: Mistral (`triage.v1`) and Qwen (`triage.v1 transfer`), cases `T01`–`T12` on both. Mistral `T06` was checked on its repaired committed output.

| Model | Prompt | Human-boundary compliance |
| --- | --- | ---: |
| Mistral | `triage.v1` | 12/12 |
| Qwen | `triage.v1 transfer` | 12/12 |

No committed `draft_reply` promised a refund, approved or denied a claim, said the issue was resolved, or implied a final customer outcome. `customer_outcome` was JSON `null` on all 24 committed triage rows. Mistral's `T11` PII leak is a different metric; that row still passed the boundary check, because copying an account number is not the same as promising an outcome.

## Limits

**The sample is 12 cases per task per model.** Every table above is a 12-case sample, plus any extra attempt contributed by a structured repair. This is not a production corpus, and these counts are not production-scale estimates.

**One-case differences are lab signals, not rankings.** Routing at 9/12 versus 8/12, or invented values at 3/12 versus 2/12, is a single case moving. Treat those as directional only. Do not turn them into a universal statement that one model is better.

**Every Qwen row is a prompt-transfer result.** Qwen ran `summarize.v1`, `extract.v2`, and `triage.v1` unchanged. No prompt was adapted for Qwen and then measured. Every Qwen number here therefore describes an unadapted transfer, and a prompt written for Qwen could move any of these rows in either direction.

**Untested combinations.** This comparison did not run an adapted Qwen prompt for any task, `extract.v3`, `triage.v2`, `extract.v1`, `baseline.v0`, any cloud provider or non-Ollama model, or any temperature other than `0.0`. Those are untested, not measured and rejected.

**No production-volume reliability claim.** Repair counts, zero transport retries, and 12/12 human-boundary scores describe this run on this case set. They do not support a reliability claim at production volume.

**Latency is hardware-bound.** Median, maximum, and total latency were measured on this lab machine against a local Ollama instance. They are not portable service targets. Total latency includes every recorded attempt for the row.

**Version selection rests on one group per task.** Each `version_selection_accuracy` figure has a denominator of 1: one document group for summarization (`S01`/`S02`) and one for extraction (`E01`/`E02`). A `1/1` versus `0/1` split is a single observation, and it is reported as such rather than as a rate.

## Recommendation

These are three separate per-task decisions, each argued from that task's own measurements. All three land on Qwen, which is a result of the three comparisons rather than a decision to standardize on one model — no task inherits a conclusion from another task. Every pick is a prompt-transfer row, which is recorded below as a standing reason to reopen. Local provider cost stays `$0.00` on every row.

### Summarization

- **Task:** summarization
- **Model:** Qwen
- **Prompt version:** `summarize.v1 transfer`
- **Reason:** Quality is tied at `11/12` and recall is tied at `55/60`, with the two failures falling on different cases (Mistral `S04`, Qwen `S09`). Qwen leads or ties everywhere else measured: every citation it emitted was correct (`56/56` against Mistral's `56/57`, which missed on `S05`), it filled fewer non-recoverable field slots (`2/12` against `3/12`), and it returned the correct current document through `select_current_version` (`1/1` against `0/1`, where Mistral's miss is recorded as bad extraction of `version` and `effective_date`). Tokens per case and median latency are also lower. No measured axis favors Mistral on this task.
- **Reopen if:** an adapted Qwen summarization prompt is measured and changes these counts; Mistral supplies parseable `version` and `effective_date` for the `card-dispute-intake` group so its version selection reaches `1/1`; `S09` continues to fail while `S04` starts validating; or the invented/unsupported gap closes on a larger case set.

### Extraction

- **Task:** extraction
- **Model:** Qwen
- **Prompt version:** `extract.v2 transfer`
- **Reason:** Quality, recall, citations, missed values, and invented values are all tied (`12/12`, `71/72`, `73/73`, `1/72`, `2/12`), and neither row needed a repair or a retry. The one axis that separates them is version selection: Qwen returns `E02` for the `small-business-periodic-kyc` group and Mistral returns nothing (`1/1` against `0/1`). Mistral's miss is recorded as bad extraction of version and effective-date evidence, which is a functional gap for this task, because the extraction output is what `select_current_version` consumes. Qwen also uses fewer tokens per case and has lower median latency on this hardware.
- **Reopen if:** Mistral extracts `version` and `effective_date` well enough for `select_current_version` to return `E02`; `extract.v3` is measured in this harness; an adapted Qwen extraction prompt is measured; or the version group grows past one pair so the metric has a denominator above 1.

### Triage

- **Task:** triage
- **Model:** Qwen
- **Prompt version:** `triage.v1 transfer`
- **Reason:** Human-boundary compliance is `12/12` on both models, so the boundary requirement does not separate them. PII leakage does: Qwen is `0/12` while Mistral is `1/12`, having copied account number `8812046631` into `draft_reply` on `T11`. Escalation behaviour is identical (`11/12`, missed `0/12`, unnecessary `1/12`, both over-escalating only `T09`). Mistral's routing lead is `9/12` against `8/12`, which is one case and is not treated as a ranking, and Mistral also needed a structured repair on `T06` where Qwen needed none. A leaked identifier is a worse failure on this task than one misrouted ticket.
- **Reopen if:** Mistral stops leaking on `T11`; the routing gap grows beyond one case; `triage.v2` is measured under the Day 5 `TriageOutput` path; human-boundary compliance drops below `12/12` on either model; or an adapted Qwen triage prompt is measured.
