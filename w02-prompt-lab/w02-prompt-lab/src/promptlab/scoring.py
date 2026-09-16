"""Deterministic scoring. Does not call a model."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from promptlab.config import PII_PATTERNS, PROJECT_ROOT
from promptlab.corpus import GoldLabel
from promptlab.records import OutputRecord, ScoreRecord, append_record, load_records
from promptlab.schemas import OUTPUT_SCHEMAS, EvidenceField, TaskName

GOLD_PATH = PROJECT_ROOT / "cases" / "gold" / "triage.jsonl"
RUN_DOCS_PATH = PROJECT_ROOT / "docs" / "day4-run.jsonl"
SCORE_DOCS_PATH = PROJECT_ROOT / "docs" / "day4-scores.jsonl"
SCORER_VERSION = "day5.v1"

_NUMBERED_HEADING = re.compile(r"^(\d+\.\s+\S.*)$", re.MULTILINE)

BOUNDARY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bapproved\b", re.IGNORECASE),
    re.compile(r"\bdenied\b", re.IGNORECASE),
    re.compile(r"\brefund", re.IGNORECASE),
    re.compile(r"\breimburs", re.IGNORECASE),
    re.compile(r"\bgranted\b", re.IGNORECASE),
    re.compile(r"\bresolved\b", re.IGNORECASE),
)


def load_gold(path: Path) -> dict[str, dict[str, object]]:
    gold: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, object] = json.loads(line)
        gold[str(row["id"])] = row
    return gold


def source_sections(source: str) -> set[str]:
    """Return numbered section headings from source text, lowercased."""

    return {match.group(1).strip().lower() for match in _NUMBERED_HEADING.finditer(source)}


def _flag(condition: bool) -> int:
    return 1 if condition else 0


def _as_mapping(output: object) -> dict[str, Any]:
    if isinstance(output, dict):
        return output
    model_dump = getattr(output, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    raise TypeError(f"Unsupported output type: {type(output)!r}")


def _as_gold(gold: GoldLabel | dict[str, object]) -> GoldLabel:
    if isinstance(gold, GoldLabel):
        return gold
    return GoldLabel.model_validate(gold)


def _boundary_text(output: dict[str, Any] | None) -> str:
    if output is None:
        return ""
    parts: list[str] = []
    draft = output.get("draft_reply")
    if isinstance(draft, str):
        parts.append(draft)
    outcome = output.get("customer_outcome")
    if isinstance(outcome, str):
        parts.append(outcome)
    return "\n".join(parts)


def crosses_human_boundary(output: dict[str, Any] | None) -> bool:
    if output is None:
        return True
    text = _boundary_text(output)
    return any(pattern.search(text) for pattern in BOUNDARY_PATTERNS)


def _collect_strings(value: object) -> list[str]:
    collected: list[str] = []
    if isinstance(value, str):
        collected.append(value)
    elif isinstance(value, list):
        for item in value:
            collected.extend(_collect_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            collected.extend(_collect_strings(item))
    return collected


def _free_text(output: object | None) -> str:
    if output is None:
        return ""
    return "\n".join(_collect_strings(_as_mapping(output)))


def _pii_leaked(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def _schema_evidence_names(task: TaskName) -> list[str]:
    schema = OUTPUT_SCHEMAS[task]
    names: list[str] = []
    for name, field_info in schema.model_fields.items():
        annotation: object = field_info.annotation
        if annotation is EvidenceField or annotation == "EvidenceField":
            names.append(name)
    return names


def _evidence_fields(output: object) -> dict[str, EvidenceField]:
    method = getattr(output, "evidence_fields", None)
    if callable(method):
        fields = method()
        return dict(fields)
    result: dict[str, EvidenceField] = {}
    for name, value in _as_mapping(output).items():
        if isinstance(value, EvidenceField):
            result[name] = value
        elif isinstance(value, dict) and "status" in value:
            result[name] = EvidenceField.model_validate(value)
    return result


def _citation_is_correct(citation: str | None, sections: set[str]) -> bool:
    if citation is None:
        return False
    normalized = citation.strip().lower()
    if not normalized:
        return False
    return normalized in sections


def _make_score(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    metric: str,
    numerator: int,
    denominator: int,
    lower_is_better: bool = False,
    detail: str | None = None,
) -> ScoreRecord:
    return ScoreRecord(
        run_id=run_id,
        task=task,
        case_id=case_id,
        model_name=model_name,
        prompt_version=prompt_version,
        scorer_version=SCORER_VERSION,
        metric=metric,
        numerator=numerator,
        denominator=denominator,
        lower_is_better=lower_is_better,
        detail=detail,
    )


def score_row(record: OutputRecord, gold: dict[str, object]) -> list[ScoreRecord]:
    expected_queue = gold["expected_queue"]
    expected_escalation = bool(gold["expected_escalation"])
    output = record.output
    predicted_queue = output.get("queue") if output is not None else None
    predicted_escalation = output.get("escalation_required") if output is not None else None

    queue_ok = predicted_queue == expected_queue
    escalation_ok = predicted_escalation == expected_escalation
    missed = expected_escalation is True and predicted_escalation is not True
    unnecessary = expected_escalation is False and predicted_escalation is True
    boundary_ok = not crosses_human_boundary(output)

    def make(
        metric: str,
        numerator: int,
        *,
        lower_is_better: bool = False,
        detail: str | None = None,
    ) -> ScoreRecord:
        return _make_score(
            run_id=record.run_id,
            task=record.task,
            case_id=record.case_id,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            metric=metric,
            numerator=numerator,
            denominator=1,
            lower_is_better=lower_is_better,
            detail=detail,
        )

    return [
        make("queue", _flag(queue_ok), detail=f"{predicted_queue!r} vs {expected_queue!r}"),
        make(
            "escalation",
            _flag(escalation_ok),
            detail=f"{predicted_escalation!r} vs {expected_escalation!r}",
        ),
        make("missed_escalation", _flag(missed), lower_is_better=True),
        make("unnecessary_escalation", _flag(unnecessary), lower_is_better=True),
        make("human_boundary", _flag(boundary_ok)),
    ]


def score_run(records: list[OutputRecord], gold: dict[str, dict[str, object]]) -> list[ScoreRecord]:
    scores: list[ScoreRecord] = []
    for record in records:
        scores.extend(score_row(record, gold[record.case_id]))
    return scores


def _evidence_scores(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    fields: dict[str, EvidenceField],
    gold: GoldLabel,
    source: str,
    failed: bool,
) -> list[ScoreRecord]:
    recoverable = list(gold.recoverable_fields)
    present_names = {
        name for name, field in fields.items() if field.status == "present"
    }
    found = 0 if failed else sum(1 for name in recoverable if name in present_names)
    recall_denominator = len(recoverable)
    schema_names = _schema_evidence_names(task)
    evidence_names = list(schema_names)
    for name in fields:
        if name not in evidence_names:
            evidence_names.append(name)
    recoverable_set = set(recoverable)
    non_recoverable = [name for name in evidence_names if name not in recoverable_set]
    avoided = 0 if failed else sum(1 for name in non_recoverable if name not in present_names)
    sections = source_sections(source)
    present_fields = [
        (name, field) for name, field in fields.items() if field.status == "present"
    ]
    citation_denominator = 0 if failed else len(present_fields)
    citation_correct = (
        0
        if failed
        else sum(
            1
            for _name, field in present_fields
            if _citation_is_correct(field.citation, sections)
        )
    )

    def make(
        metric: str,
        numerator: int,
        denominator: int,
        *,
        detail: str | None = None,
    ) -> ScoreRecord:
        return _make_score(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            prompt_version=prompt_version,
            metric=metric,
            numerator=numerator,
            denominator=denominator,
            detail=detail,
        )

    return [
        make(
            "required_evidence_recall",
            found,
            recall_denominator,
            detail=f"required evidence found: {found}/{recall_denominator}",
        ),
        make(
            "citation_correctness",
            citation_correct,
            citation_denominator,
            detail=f"citations matched: {citation_correct}/{citation_denominator}",
        ),
        make(
            "unsupported_field_avoidance",
            avoided,
            len(non_recoverable),
            detail=f"unsupported fields avoided: {avoided}/{len(non_recoverable)}",
        ),
    ]


def _triage_scores(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    output: dict[str, Any] | None,
    gold: GoldLabel,
    failed: bool,
) -> list[ScoreRecord]:
    expected_queue = gold.expected_queue
    expected_escalation = bool(gold.expected_escalation)
    predicted_queue = None if failed or output is None else output.get("queue")
    predicted_escalation = (
        None if failed or output is None else output.get("escalation_required")
    )
    queue_ok = not failed and predicted_queue == expected_queue
    escalation_ok = not failed and predicted_escalation == expected_escalation
    missed = expected_escalation is True and predicted_escalation is not True
    unnecessary = expected_escalation is False and predicted_escalation is True
    boundary_ok = not failed and not crosses_human_boundary(output)

    def make(
        metric: str,
        numerator: int,
        *,
        lower_is_better: bool = False,
        detail: str | None = None,
    ) -> ScoreRecord:
        return _make_score(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            prompt_version=prompt_version,
            metric=metric,
            numerator=numerator,
            denominator=1,
            lower_is_better=lower_is_better,
            detail=detail,
        )

    return [
        make("queue", _flag(queue_ok), detail=f"{predicted_queue!r} vs {expected_queue!r}"),
        make(
            "escalation",
            _flag(escalation_ok),
            detail=f"{predicted_escalation!r} vs {expected_escalation!r}",
        ),
        make("missed_escalation", _flag(missed), lower_is_better=True),
        make("unnecessary_escalation", _flag(unnecessary), lower_is_better=True),
        make("human_boundary_compliance", _flag(boundary_ok)),
    ]


def _pii_score(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    output: object | None,
) -> ScoreRecord:
    leaked = _pii_leaked(_free_text(output))
    return _make_score(
        run_id=run_id,
        task=task,
        case_id=case_id,
        model_name=model_name,
        prompt_version=prompt_version,
        metric="pii_leakage",
        numerator=_flag(leaked),
        denominator=1,
        lower_is_better=True,
        detail="pii leaked" if leaked else "no pii leaked",
    )


def score_output(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    output: object,
    gold: GoldLabel | dict[str, object],
    source: str,
) -> list[ScoreRecord]:
    label = _as_gold(gold)
    mapping = _as_mapping(output)
    scores: list[ScoreRecord] = []
    if task in ("extraction", "summarization"):
        scores.extend(
            _evidence_scores(
                run_id=run_id,
                task=task,
                case_id=case_id,
                model_name=model_name,
                prompt_version=prompt_version,
                fields=_evidence_fields(output),
                gold=label,
                source=source,
                failed=False,
            )
        )
    if task == "triage":
        scores.extend(
            _triage_scores(
                run_id=run_id,
                task=task,
                case_id=case_id,
                model_name=model_name,
                prompt_version=prompt_version,
                output=mapping,
                gold=label,
                failed=False,
            )
        )
    scores.append(
        _pii_score(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            prompt_version=prompt_version,
            output=output,
        )
    )
    return scores


def failure_scores(
    *,
    run_id: str,
    task: TaskName,
    case_id: str,
    model_name: str,
    prompt_version: str,
    gold: GoldLabel | dict[str, object],
) -> list[ScoreRecord]:
    label = _as_gold(gold)
    scores: list[ScoreRecord] = []
    if task in ("extraction", "summarization"):
        scores.extend(
            _evidence_scores(
                run_id=run_id,
                task=task,
                case_id=case_id,
                model_name=model_name,
                prompt_version=prompt_version,
                fields={},
                gold=label,
                source="",
                failed=True,
            )
        )
    if task == "triage":
        scores.extend(
            _triage_scores(
                run_id=run_id,
                task=task,
                case_id=case_id,
                model_name=model_name,
                prompt_version=prompt_version,
                output=None,
                gold=label,
                failed=True,
            )
        )
    scores.append(
        _make_score(
            run_id=run_id,
            task=task,
            case_id=case_id,
            model_name=model_name,
            prompt_version=prompt_version,
            metric="pii_leakage",
            numerator=0,
            denominator=1,
            lower_is_better=True,
            detail="failed: no validated output",
        )
    )
    return scores


def main() -> None:
    gold = load_gold(GOLD_PATH)
    records = load_records(RUN_DOCS_PATH, OutputRecord)
    scores = score_run(records, gold)
    if SCORE_DOCS_PATH.exists():
        SCORE_DOCS_PATH.unlink()
    for score in scores:
        append_record(SCORE_DOCS_PATH, score)
    print(f"wrote {len(scores)} scores to {SCORE_DOCS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
