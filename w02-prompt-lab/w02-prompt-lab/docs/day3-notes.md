# Day 3 notes

I ran summarization (`summarize.v1.md`, S01–S12) and extraction (`extract.v2.md`, E01–E12) on `mistral:7b` at temperature `0.0` and `max_output_tokens=1024`, all under one `run_id`. Repair lives in `complete_structured`, capped at one attempt. The file I’m submitting is `docs/day3-run.jsonl` (`run_id=59b65aed-afe3-4bf6-8092-2a7555458f58`). Same id in `runs/59b65aed-afe3-4bf6-8092-2a7555458f58.jsonl`.

## What went wrong at first

The first pass dumped `model.model_json_schema()` into the prompt. Mistral copied that schema back at me — `$defs`, `properties`, `type` — so almost everything failed extra-forbid, and extraction often came back looking empty.

I stopped pasting JSON Schema. `schema_description` now walks the Pydantic fields and describes an instance (`document_status` as a string, `EvidenceField` as value/status/citation). After that, extraction still failed a lot because the model wrapped good JSON in “Here is the JSON…” plus markdown fences, and the parser only stripped fences when they were at the very start. I taught `_parse_json_text` to pull a fenced block or the first `{`…`}` object. That was the change that actually made extraction validate.

S04 and S09 then failed for a dumber reason: those docs have an “Appendix Table” section, and the model emitted an `appendix_table` key. Null still isn’t allowed. I added two lines to the generated description: only the listed keys, and headings are citations, not fields. I left the parser alone so I wouldn’t start silently dropping extras.

Day 1’s 256-token ceiling is not enough for this JSON. 256 truncated mid-object. 1024 is what this run used. Day 3 never said to keep 256.

## Numbers from the submitted run

Repair rate = cases that needed a semantic repair / 12.

- Summarization repair rate: **0 / 12** (12 / 12 validated)
- Extraction repair rate: **0 / 12** (12 / 12 validated)
- Example leakage count: **0** (no Northglass / Norwyn / Bellwater / Redhaven / East Kestrel in extraction outputs)
- Citation-existence failure count: **1** — S12 `title` came back with citation `"1."` instead of `"1. Newsletter"`. The other present fields used a real heading.

Every output in `docs/day3-run.jsonl` re-validates as `SummarizationOutput` or `PolicyExtraction`. No extra keys. Every usage record is attempt 1, `stop_reason=stop`.

S04 and S09 validated as `unsupported` rather than `contradictory`. That’s a status call, not a parse failure. I didn’t chase it further because the schema already accepted them.