"""Day 2 runner: same summarization request against both configured local models."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.usage import CallRecord, append_record

PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"
CASES_PATH = PROJECT_ROOT / "cases" / "summarization.jsonl"
RUN_DOCS_PATH = PROJECT_ROOT / "docs" / "day2-run.jsonl"
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0
PROMPT_ID = "baseline"
PROMPT_VERSION = "v0"


def load_cases() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, object] = json.loads(line)
        cases.append((str(row["id"]), str(row["source"])))
    return cases


def build_request(case_id: str, source: str, template: str) -> CompletionRequest:
    return CompletionRequest(
        task="summarization",
        case_id=case_id,
        prompt_id=PROMPT_ID,
        prompt_version=PROMPT_VERSION,
        system=template.replace("{document_text}", source),
        user_content="",
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


def write_run_docs(records: list[CallRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def main() -> None:
    settings = Settings.from_env()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    cases = load_cases()
    run_id = str(uuid.uuid4())
    adapters = (
        OllamaAdapter(model_id=settings.models["mistral"].model_id),
        OllamaAdapter(model_id=settings.models["qwen"].model_id),
    )
    records: list[CallRecord] = []

    for case_id, source in cases:
        request = build_request(case_id, source, template)
        for adapter in adapters:
            result = adapter.complete(request, run_id)
            for record in result.records:
                append_record(record, run_id)
                records.append(record)
            print(
                f"{adapter.model_id} {case_id}: succeeded={result.succeeded} "
                f"attempts={len(result.records)}"
            )

    write_run_docs(records, RUN_DOCS_PATH)
    print(f"wrote runs/{run_id}.jsonl")
    print(f"wrote {RUN_DOCS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
