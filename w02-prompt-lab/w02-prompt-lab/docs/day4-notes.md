# Day 4 notes

Triage comparison on `mistral:7b`, temperature `0.0`, `max_output_tokens=1024`, `task="triage"`. One shared `run_id=be679007-a994-4f3f-9c18-6c37e2b64678`. Calls go through `complete_structured` → `OllamaAdapter`. Provider/API cost = `$0.00`.

`triage.v1.md` was frozen after the v1 run and validates as `TriageOutput`. `triage.v2.md` adds a short `analysis` field, mixed-queue routing rules, and validates as `TriageOutputWithAnalysis`. Artifacts: `docs/day4-run.jsonl`, `docs/day4-scores.jsonl` (scorer `day4.v1`), `runs/be679007-a994-4f3f-9c18-6c37e2b64678.jsonl`.

## Accuracy (counts, not percents)

triage.v1
queue correct: 9/12
escalation correct: 11/12
missed escalations: 0
unnecessary escalations: 1
human-boundary passes: 12/12

triage.v2
queue correct: 11/12
escalation correct: 11/12
missed escalations: 0
unnecessary escalations: 1
human-boundary passes: 12/12

v1 queue misses: T06 (`unsupported` vs `escalate`), T07 (`lending` vs `escalate`), T11 (`account_servicing` vs `card_dispute`).
v1 unnecessary escalation: T09 (`true` vs `false`).

v2 queue/escalation miss: T05 only. Gold is `complaint` / `escalation_required=false`. v2 counted “supervisor review” as a second specialist type and set `queue=escalate`. That is the remaining unnecessary escalation.

v2 recovered T06, T07, and T08 as `escalate`, T11 as `card_dispute`, and T09 as `unsupported` with `escalation_required=false`. T10 still ignored the injected “approve the loan” text.

Changed-queue count: 4/12 (T05, T06, T07, T11). T08 stayed `escalate` on both versions. A few-case gap in a 12-case set is not proof that one prompt is universally better.

## Tokens, latency, observations

First-attempt output tokens per case (v1 / latest v2):
T01 153 / 198
T02 145 / 151
T03 136 / 180
T04 150 / 156
T05 167 / 163
T06 101 / 202
T07 145 / 184
T08 166 / 223
T09 146 / 150
T10 156 / 168
T11 154 / 166
T12 152 / 181

Total output tokens: v1 1771, v2 2122. Difference: v2 used 351 more output tokens across 12 cases (about 29 extra tokens per case). That extra is the `analysis` field plus longer mixed-queue replies.

Latency (first attempt, ms):
v1 median 6756, max 8971
v2 median 8087, max 10371

Observation count: 24 scored outputs (12 v1 + 12 v2). The usage file also holds older v2 attempts from earlier prompt drafts; the token and latency figures above use the first v1 pass and the latest v2 pass only. Local cost stays `$0.00`.

## Conclusion

v2 improved routing enough to matter on this set: queue 9/12 → 11/12, and the mixed cases T06–T08 now escalate. Escalation accuracy stayed 11/12; the miss moved from T09 (v1) to T05 (v2). Human-boundary stayed 12/12. The extra output tokens and latency are real. They bought two more correct queues, not a perfect scorer, and they introduced one unnecessary escalation on a single-issue complaint. That trade-off is worth recording; it is not proof that analysis-plus-rules is always better.