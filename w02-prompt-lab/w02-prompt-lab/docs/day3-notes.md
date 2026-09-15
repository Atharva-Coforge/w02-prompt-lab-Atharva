# Day 3 notes

Delivered evidence is `docs/day3-run.jsonl` (`run_id=2a84dac0-9d13-425d-a37a-37b61eeb6112`). One model (`mistral:7b`), temperature `0.0`, `max_output_tokens=1024`. Summarization used `summarize.v1.md` over S01–S12. Extraction used `extract.v2.md` over E01–E12. `complete_structured` allowed at most one semantic repair.

## First run (not delivered)

`run_id=7891dfe4-bc48-4b24-ad63-96e529850d1a` used `schema_description` as `json.dumps(model.model_json_schema())`.

Summarization succeeded on 3 / 12 cases (S04, S05, S12). The other nine failed after one repair. Extraction succeeded on 0 / 12 cases.

The most common validation error was the model echoing the JSON Schema document instead of a filled instance: extra keys `$defs`, `properties`, `required`, `type`, and `additionalProperties`, with `document_status` wrapped as an `EvidenceField` object and `title` set to the string `"SummarizationOutput"`. Extraction replies were empty (`Expecting value: line 1 column 1`), which matched the same oversized schema dump sitting on top of the few-shot prompt.

## What changed

`schema_description` was rewritten to walk `model.model_fields` and describe an instance: allowed keys, Literal options, and nested `EvidenceField` as `{value, status, citation}`. It still comes from the Pydantic model. It no longer pastes a JSON Schema document. The delivered run used that description.

## Delivered measurements

Repair rate is cases that used a semantic repair / 12.

| Task | Successes | Repair rate | Notes |
| --- | ---: | --- | --- |
| Summarization | 10 / 12 | **2 / 12** | S05 and S12 still failed after one repair |
| Extraction | 2 / 12 | **12 / 12** | Only E03 and E09 validated, both after repair |

Remaining summarization failures were not schema-echo. S05 used `document_status="ambiguous"` (not a legal `DocumentStatus`) and omitted `value` on absent fields. S12 omitted `value` on absent fields. Most failed extraction cases were still empty JSON after repair.

## Example leakage

Distinctive strings from the two `extract.v2.md` examples (Northglass, Norwyn, Bellwater, Redhaven, East Kestrel) were searched in every extraction output.

**Example leakage count: 0**

## Citation-existence

For every returned `EvidenceField` with `status: "present"`, `citation` was checked against the numbered section headings in that case’s source (`1. Document Control`, `2. Purpose`, …). 71 present fields were returned. 12 used a full heading. 59 used only the section number (`"1"`, `"2"`). Those numbers appear in the heading line but are not the heading as written.

**Citation-existence failure count: 59**
