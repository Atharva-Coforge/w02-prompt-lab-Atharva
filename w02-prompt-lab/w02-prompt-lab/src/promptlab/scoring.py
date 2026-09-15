"""Deterministic Day 4 triage scoring. Does not call a model."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from promptlab.config import PROJECT_ROOT
from promptlab.records import OutputRecord, ScoreRecord, append_record, load_records

GOLD_PATH = PROJECT_ROOT / "cases" / "gold" / "triage.jsonl"
RUN_DOCS_PATH = PROJECT_ROOT / "docs" / "day4-run.jsonl"
SCORE_DOCS_PATH = PROJECT_ROOT / "docs" / "day4-scores.jsonl"
SCORER_VERSION = "day4.v1"

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


def _flag(condition: bool) -> int:
    return 1 if condition else 0


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
        return ScoreRecord(
            run_id=record.run_id,
            task=record.task,
            case_id=record.case_id,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            scorer_version=SCORER_VERSION,
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
