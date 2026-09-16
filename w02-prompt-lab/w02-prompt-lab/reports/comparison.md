# Model Comparison

Run ID: `day5-full`

Counts are reported with their denominators. Latency uses median and maximum rather than mean.

## Extraction

| Model | Prompt | Valid outputs | Metrics | Input tokens | Output tokens | Median latency | Max latency | n | Repairs | Retries | Final failures |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mistral | extract.v2 | 12/12 | citation_correctness: 73/73<br>pii_leakage: 0/12 ↓<br>required_evidence_recall: 71/72<br>unsupported_field_avoidance: 10/12<br>version_selection_accuracy: 0/1 | 22811 | 4839 | 18772 ms | 20763 ms | 12 | 0/12 | 0 | 0 |
| qwen | extract.v2 transfer | 12/12 | citation_correctness: 73/73<br>pii_leakage: 0/12 ↓<br>required_evidence_recall: 71/72<br>unsupported_field_avoidance: 10/12<br>version_selection_accuracy: 1/1 | 19283 | 3416 | 14989 ms | 18104 ms | 12 | 0/12 | 0 | 0 |

## Summarization

| Model | Prompt | Valid outputs | Metrics | Input tokens | Output tokens | Median latency | Max latency | n | Repairs | Retries | Final failures |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mistral | summarize.v1 | 11/12 | citation_correctness: 56/57<br>pii_leakage: 0/12 ↓<br>required_evidence_recall: 55/60<br>unsupported_field_avoidance: 9/12<br>version_selection_accuracy: 0/1 | 13433 | 3705 | 13368 ms | 15619 ms | 13 | 1/12 | 0 | 1 |
| qwen | summarize.v1 transfer | 11/12 | citation_correctness: 56/56<br>pii_leakage: 0/12 ↓<br>required_evidence_recall: 55/60<br>unsupported_field_avoidance: 10/12<br>version_selection_accuracy: 1/1 | 11571 | 3133 | 12442 ms | 16050 ms | 13 | 1/12 | 0 | 1 |

## Triage

| Model | Prompt | Valid outputs | Metrics | Input tokens | Output tokens | Median latency | Max latency | n | Repairs | Retries | Final failures |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mistral | triage.v1 | 12/12 | escalation: 11/12<br>human_boundary_compliance: 12/12<br>missed_escalation: 0/12 ↓<br>pii_leakage: 1/12 ↓<br>queue: 9/12<br>unnecessary_escalation: 1/12 ↓ | 5462 | 1911 | 5723 ms | 8072 ms | 13 | 1/12 | 0 | 0 |
| qwen | triage.v1 transfer | 12/12 | escalation: 11/12<br>human_boundary_compliance: 12/12<br>missed_escalation: 0/12 ↓<br>pii_leakage: 0/12 ↓<br>queue: 8/12<br>unnecessary_escalation: 1/12 ↓ | 4375 | 1440 | 5278.5 ms | 8250 ms | 12 | 0/12 | 0 | 0 |

## Limits

- The Week 2 comparison uses a small fixed case set; report counts rather than treating one-case differences as precise production estimates.
- A row measures the model together with the prompt version shown in that row.
- Prompt cells named `summarize.v1`, `extract.v2`, or `triage.v1` are the measured versions. A trailing `transfer` means Qwen ran that same prompt; it is not an adapted Qwen prompt and is not a claim about Qwen in general.
- Local Ollama provider/API charge is `$0.00`; token usage and latency still represent real operational work.
