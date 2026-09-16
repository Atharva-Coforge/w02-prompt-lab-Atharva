# Day 4 notes

Triage comparison on `mistral:7b`, temperature `0.0`, `max_output_tokens=1024`, `task="triage"`. One shared `run_id=be679007-a994-4f3f-9c18-6c37e2b64678`. Calls go through `complete_structured` → `OllamaAdapter`. Provider/API cost = `$0.00`.

`triage.v1.md` was frozen after the v1 run and validates as `TriageOutput`. `triage.v2.md` is the same standing triage prompt plus a short `analysis` field, and validates as `TriageOutputWithAnalysis`. Both versions keep `rationale`. Artifacts: `docs/day4-run.jsonl`, `docs/day4-scores.jsonl` (scorer `day4.v1`), `runs/be679007-a994-4f3f-9c18-6c37e2b64678.jsonl`.

## Accuracy (counts, not percents)

triage.v1
queue correct: 9/12
escalation correct: 11/12
missed escalations: 0
unnecessary escalations: 1
human-boundary passes: 12/12

triage.v2
queue correct: 9/12
escalation correct: 11/12
missed escalations: 0
unnecessary escalations: 1
human-boundary passes: 12/12

v1 queue misses: T06 (`unsupported` vs `escalate`), T07 (`lending` vs `escalate`), T11 (`account_servicing` vs `card_dispute`).
v1 unnecessary escalation: T09 (`true` vs `false`).

v2 queue misses: T06 (`card_dispute` vs `escalate`), T07 (`lending` vs `escalate`), T11 (`account_servicing` vs `card_dispute`).
v2 unnecessary escalation: T09 (`true` vs `false`).

Changed-queue count: 1/12 (T06 only). T10 still ignored the injected “approve the loan” text. A one-case queue flip in a 12-case set is not proof that one prompt is universally better.

## Tokens, latency, observations

First-attempt output tokens per case (v1 / latest v2):
T01 153 / 209
T02 145 / 176
T03 136 / 169
T04 150 / 186
T05 167 / 182
T06 101 / 200
T07 145 / 233
T08 166 / 204
T09 146 / 187
T10 156 / 174
T11 154 / 196
T12 152 / 181

Total output tokens: v1 1771, v2 2297. Difference: v2 used 526 more output tokens across 12 cases (about 44 extra tokens per case). That extra is the `analysis` field.

Latency (first attempt, ms):
v1 median 6756, max 8971
v2 median 7048, max 10072

Observation count: 24 scored outputs (12 v1 + 12 v2). The usage file also holds older v2 attempts from earlier prompt drafts; the token and latency figures above use the first v1 pass and the latest v2 pass only. Local cost stays `$0.00`.

## Conclusion

The additional `analysis` field did not improve routing on this set: queue stayed 9/12 and escalation stayed 11/12. The same mixed cases (T06, T07) and the same T11 card-dispute miss remained. v2 paid 526 extra output tokens and higher max latency for that field. On this 12-case set, analysis did not earn its overhead. That is a measurement of one prompt change, not proof that analysis never helps.