"""Day 4 runner: validated triage under one run_id."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import BaseModel, ValidationError

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.prompts import PromptTemplate, load, render_user
from promptlab.records import OutputRecord, append_record
from promptlab.schemas import TriageOutput
from promptlab.structured import complete_structured
from promptlab.usage import CallRecord
from promptlab.usage import append_record as append_usage_record

CASES_PATH = PROJECT_ROOT / "cases" / "triage.jsonl"
RUN_DOCS_PATH = PROJECT_ROOT / "docs" / "day4-run.jsonl"
PROMPT_ID = "triage"
PROMPT_VERSION = "v1"
MAX_OUTPUT_TOKENS = 1024
TEMPERATURE = 0.0


class CountingAdapter:
    """Count adapter.complete calls so repair rate can be measured."""

    def __init__(self, inner: OllamaAdapter) -> None:
        self._inner = inner
        self.provider = inner.provider
        self.model_id = inner.model_id
        self.calls = 0
        self.last_records_list: list[CallRecord] = []

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        self.calls += 1
        result = self._inner.complete(request, run_id)
        self.last_records_list = list(result.records)
        return result


def load_cases(path: Path) -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, object] = json.loads(line)
        cases.append((str(row["id"]), str(row["source"])))
    return cases


def build_request(
    template: PromptTemplate,
    case_id: str,
    source: str,
) -> CompletionRequest:
    user_content = render_user(template, variables={"case_id": case_id}, untrusted=source)
    return CompletionRequest(
        task="triage",
        case_id=case_id,
        prompt_id=template.prompt_id,
        prompt_version=template.version,
        system=template.system,
        user_content=user_content,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


def run_case(
    adapter: CountingAdapter,
    request: CompletionRequest,
    schema: type[BaseModel],
    run_id: str,
    model_name: str,
) -> OutputRecord:
    adapter.calls = 0
    first_error: str | None = None
    output: dict[str, object] | None = None
    succeeded = False

    try:
        validated = complete_structured(adapter, request, schema, run_id, max_repairs=1)
        output = validated.model_dump()
        succeeded = True
    except (json.JSONDecodeError, ValidationError) as exc:
        first_error = str(exc)

    for record in adapter.last_records_list:
        append_usage_record(record, run_id)

    return OutputRecord(
        run_id=run_id,
        task=request.task,
        case_id=request.case_id,
        model_name=model_name,
        model_id=adapter.model_id,
        prompt_version=request.prompt_version,
        succeeded=succeeded,
        repairs=max(adapter.calls - 1, 0),
        output=output,
        error=first_error,
    )


def main() -> None:
    settings = Settings.from_env()
    model = settings.models["mistral"]
    inner = OllamaAdapter(model_id=model.model_id)
    adapter = CountingAdapter(inner)
    run_id = str(uuid.uuid4())
    RUN_DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RUN_DOCS_PATH.exists():
        RUN_DOCS_PATH.unlink()

    template = load(PROMPT_ID, PROMPT_VERSION)
    for case_id, source in load_cases(CASES_PATH):
        request = build_request(template, case_id, source)
        record = run_case(adapter, request, TriageOutput, run_id, model.logical_name)
        append_record(RUN_DOCS_PATH, record)
        print(
            f"triage {case_id} {template.version}: succeeded={record.succeeded} "
            f"repairs={record.repairs}"
        )

    print(f"run_id={run_id}")
    print(f"wrote runs/{run_id}.jsonl")
    print(f"wrote {RUN_DOCS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
