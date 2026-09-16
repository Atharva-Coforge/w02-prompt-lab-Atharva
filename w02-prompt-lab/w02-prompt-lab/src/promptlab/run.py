"""Day 5 evaluation runner: three tasks against both configured local models."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ValidationError

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.corpus import GoldLabel, load_cases, validate_corpus
from promptlab.prompts import PromptTemplate, load, render_user
from promptlab.records import OutputRecord, ScoreRecord, UsageRecord, append_record
from promptlab.report import write_reports
from promptlab.rules import candidates_from_extractions, score_version_selection
from promptlab.schemas import OUTPUT_SCHEMAS, TaskName, schema_description
from promptlab.scoring import SCORER_VERSION, failure_scores, score_output
from promptlab.structured import complete_structured
from promptlab.usage import CallRecord
from promptlab.usage import append_record as append_call_record

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
DAY5_RUN_PATH = PROJECT_ROOT / "docs" / "day5-run.jsonl"
DAY5_SCORES_PATH = PROJECT_ROOT / "docs" / "day5-scores.jsonl"
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 1024
ALL_TASKS: tuple[TaskName, ...] = ("triage", "summarization", "extraction")
TASK_PROMPTS: dict[TaskName, tuple[str, str]] = {
    "summarization": ("summarize", "v1"),
    "extraction": ("extract", "v2"),
    "triage": ("triage", "v1"),
}

AttemptKind = Literal["primary", "transport_retry", "repair", "repair_retry"]
AttemptStatus = Literal["success", "schema_invalid", "transport_error"]


class RecordingAdapter:
    """Collect every CallRecord from transport retries and structured repairs."""

    def __init__(self, inner: OllamaAdapter) -> None:
        self._inner = inner
        self.provider = inner.provider
        self.model_id = inner.model_id
        self.calls: list[CompletionResult] = []

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        result = self._inner.complete(request, run_id)
        self.calls.append(result)
        return result

    def reset(self) -> None:
        self.calls = []


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local two-model prompt comparison")
    parser.add_argument("--run-id", help="Stable identifier for this run")
    parser.add_argument("--task", choices=["triage", "summarization", "extraction"])
    parser.add_argument("--model", choices=["mistral", "qwen"])
    parser.add_argument("--limit", type=int, help="Limit cases per task for a smoke run")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configuration and corpus without calling Ollama",
    )
    return parser


def _append_jsonl(path: Path, payload: CallRecord | ScoreRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload.model_dump_json() + "\n")


def _label_str(label: GoldLabel, name: str) -> str | None:
    value = getattr(label, name, None)
    return value if isinstance(value, str) and value else None


def _attempt_kind(call_index: int, attempt: int) -> AttemptKind:
    if call_index == 0:
        return "primary" if attempt == 1 else "transport_retry"
    return "repair" if attempt == 1 else "repair_retry"


def _attempt_status(
    record: CallRecord,
    *,
    result_succeeded: bool,
    is_final_call: bool,
    case_succeeded: bool,
) -> AttemptStatus:
    if record.error_type is not None or not result_succeeded:
        return "transport_error"
    if case_succeeded and is_final_call:
        return "success"
    return "schema_invalid"


def _usage_from_call(
    record: CallRecord,
    *,
    model_name: str,
    kind: AttemptKind,
    status: AttemptStatus,
) -> UsageRecord:
    return UsageRecord(
        run_id=record.run_id,
        task=record.task,
        case_id=record.case_id,
        model_name=model_name,
        model_id=record.model_id,
        prompt_version=record.prompt_version,
        attempt=record.attempt,
        kind=kind,
        status=status,
        prompt_tokens=record.input_tokens,
        completion_tokens=record.output_tokens,
        latency_ms=float(record.latency_ms),
        cost_usd=Decimal(str(record.cost_usd)),
        error=record.error_type,
    )


def _persist_calls(
    adapter: RecordingAdapter,
    *,
    model_name: str,
    case_succeeded: bool,
    usage: list[UsageRecord],
) -> int:
    last_call_index = len(adapter.calls) - 1
    for call_index, result in enumerate(adapter.calls):
        for record in result.records:
            kind = _attempt_kind(call_index, record.attempt)
            status = _attempt_status(
                record,
                result_succeeded=result.succeeded,
                is_final_call=call_index == last_call_index,
                case_succeeded=case_succeeded,
            )
            append_call_record(record, record.run_id)
            _append_jsonl(DAY5_RUN_PATH, record)
            usage.append(_usage_from_call(record, model_name=model_name, kind=kind, status=status))
    return max(len(adapter.calls) - 1, 0)


def _add_version_scores(
    *,
    run_id: str,
    task: TaskName,
    model_name: str,
    model_id: str,
    prompt_id: str,
    prompt_version: str,
    labels: list[GoldLabel],
    outputs: dict[str, object],
    all_scores: list[ScoreRecord],
) -> None:
    grouped: dict[str, list[GoldLabel]] = defaultdict(list)
    for label in labels:
        group_name = _label_str(label, "version_group")
        if group_name:
            grouped[group_name].append(label)

    for group_name, group_labels in grouped.items():
        if len(group_labels) < 2:
            continue
        expected = next(
            (
                _label_str(label, "expected_current_case_id")
                for label in group_labels
                if _label_str(label, "expected_current_case_id")
            ),
            None,
        )
        as_of_raw = next(
            (_label_str(label, "as_of") for label in group_labels if _label_str(label, "as_of")),
            None,
        )
        if expected is None or as_of_raw is None:
            continue
        items = [
            (label.id, outputs[label.id]) for label in group_labels if label.id in outputs
        ]
        scored = score_version_selection(
            candidates_from_extractions(items),
            date.fromisoformat(as_of_raw),
            expected,
        )
        record = ScoreRecord(
            run_id=run_id,
            task=task,
            case_id=f"version:{group_name}",
            model_name=model_name,
            model_id=model_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            scorer_version=SCORER_VERSION,
            metric="version_selection_accuracy",
            numerator=scored.numerator,
            denominator=scored.denominator,
            detail=scored.detail,
        )
        append_record(DAY5_SCORES_PATH, record)
        all_scores.append(record)


def _run_case(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    source: str,
    gold: GoldLabel,
    template: PromptTemplate,
    schema: type[BaseModel],
    adapter: RecordingAdapter,
    model_name: str,
    model_id: str,
    max_repairs: int,
    usage: list[UsageRecord],
    outputs: list[OutputRecord],
    scores: list[ScoreRecord],
    validated: dict[str, object],
) -> None:
    user_content = render_user(
        template,
        variables={"schema_description": schema_description(schema)},
        untrusted=source,
    )
    request = CompletionRequest(
        task=task,
        case_id=case_id,
        prompt_id=template.prompt_id,
        prompt_version=template.version,
        system=template.system,
        user_content=user_content,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    adapter.reset()
    error: str | None = None
    output_payload: dict[str, object] | None = None
    succeeded = False
    try:
        parsed = complete_structured(
            adapter,
            request,
            schema,
            run_id,
            max_repairs=max_repairs,
        )
        output_payload = parsed.model_dump(mode="json")
        succeeded = True
        validated[case_id] = parsed
        case_scores = score_output(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            model_id=model_id,
            prompt_id=template.prompt_id,
            prompt_version=template.version,
            output=parsed,
            gold=gold,
            source=source,
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        error = str(exc)
        case_scores = failure_scores(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            model_id=model_id,
            prompt_id=template.prompt_id,
            prompt_version=template.version,
            gold=gold,
        )

    repairs = _persist_calls(
        adapter, model_name=model_name, case_succeeded=succeeded, usage=usage
    )
    output_record = OutputRecord(
        run_id=run_id,
        task=task,
        case_id=case_id,
        model_name=model_name,
        model_id=model_id,
        prompt_version=template.version,
        succeeded=succeeded,
        repairs=repairs,
        output=output_payload,
        error=error,
    )
    outputs.append(output_record)
    for score in case_scores:
        append_record(DAY5_SCORES_PATH, score)
        scores.append(score)
    print(f"{task:13} {model_name:8} {case_id:5} {'ok' if succeeded else 'failed'}")


def main() -> None:
    args = _parser().parse_args()
    counts = validate_corpus()
    if args.validate_only:
        print("Corpus valid: " + ", ".join(f"{task}={count}" for task, count in counts.items()))
        return

    run_id = cast(str | None, args.run_id)
    if run_id is None or not RUN_ID_PATTERN.fullmatch(run_id):
        raise SystemExit("--run-id is required and must use letters, numbers, '.', '_' or '-'")
    limit = cast(int | None, args.limit)
    if limit is not None and limit < 1:
        raise SystemExit("--limit must be at least 1")

    settings = Settings.from_env()
    selected_tasks: list[TaskName] = (
        [cast(TaskName, args.task)] if args.task else list(ALL_TASKS)
    )

    if args.model:
        logical_name = cast(str, args.model)
        if logical_name not in settings.models:
            configured = list(settings.models)
            raise SystemExit(f"Unknown model {logical_name!r}; configured names: {configured}")
        selected_models = [logical_name]
    else:
        selected_models = list(settings.models)

    existing = PROJECT_ROOT / "runs" / f"{run_id}.jsonl"
    if existing.exists():
        raise SystemExit(f"Run already exists: {existing}")

    DAY5_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAY5_RUN_PATH.write_text("", encoding="utf-8")
    DAY5_SCORES_PATH.write_text("", encoding="utf-8")

    all_usage: list[UsageRecord] = []
    all_outputs: list[OutputRecord] = []
    all_scores: list[ScoreRecord] = []
    validated_by_task_model: dict[tuple[TaskName, str], dict[str, object]] = defaultdict(dict)
    labels_by_task: dict[TaskName, list[GoldLabel]] = {}
    versions_by_task: dict[TaskName, str] = {}

    for task in selected_tasks:
        prompt_id, prompt_version = TASK_PROMPTS[task]
        template = load(prompt_id, prompt_version)
        schema = OUTPUT_SCHEMAS[task]
        versions_by_task[task] = template.version
        pairs = load_cases(task)
        if limit is not None:
            pairs = pairs[:limit]
        labels_by_task[task] = [gold for _case, gold in pairs]
        for logical_name in selected_models:
            model = settings.models[logical_name]
            adapter = RecordingAdapter(OllamaAdapter(model_id=model.model_id))
            validated = validated_by_task_model[(task, logical_name)]
            for case, gold in pairs:
                _run_case(
                    run_id=run_id,
                    task=task,
                    case_id=case.id,
                    source=case.document_text,
                    gold=gold,
                    template=template,
                    schema=schema,
                    adapter=adapter,
                    model_name=logical_name,
                    model_id=model.model_id,
                    max_repairs=settings.max_schema_repairs,
                    usage=all_usage,
                    outputs=all_outputs,
                    scores=all_scores,
                    validated=validated,
                )

    for task in selected_tasks:
        if task == "triage":
            continue
        for logical_name in selected_models:
            _add_version_scores(
                run_id=run_id,
                task=task,
                model_name=logical_name,
                model_id=settings.models[logical_name].model_id,
                prompt_id=TASK_PROMPTS[task][0],
                prompt_version=versions_by_task[task],
                labels=labels_by_task[task],
                outputs=validated_by_task_model[(task, logical_name)],
                all_scores=all_scores,
            )

    write_reports(
        run_id=run_id,
        models=selected_models,
        usage=all_usage,
        outputs=all_outputs,
        scores=all_scores,
        report_path=PROJECT_ROOT / "reports" / "comparison.md",
        decision_path=PROJECT_ROOT / "docs" / "model-decision.md",
    )
    print(f"Calls: {DAY5_RUN_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Scores: {DAY5_SCORES_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Report: {(PROJECT_ROOT / 'reports' / 'comparison.md').relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
