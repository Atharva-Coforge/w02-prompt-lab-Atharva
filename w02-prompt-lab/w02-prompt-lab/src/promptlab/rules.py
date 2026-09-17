from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

VersionAttribution = Literal[
    "correct",
    "bad_extraction",
    "ambiguous_rule",
    "wrong_selection",
]


@dataclass(frozen=True)
class VersionCandidate:
    case_id: str
    version: str
    effective_date: date


@dataclass(frozen=True)
class VersionSelectionScore:
    """Score of select_current_version against a gold current document.

    numerator/denominator are counts, never a percentage. A miss is attributed to
    bad extraction (missing or unusable version/date evidence) or to the
    deterministic rule (ambiguous dates, or a different case selected).
    """

    selected: VersionCandidate | None
    expected_case_id: str
    numerator: int
    denominator: int
    attribution: VersionAttribution
    detail: str


def select_current_version(
    extractions: list[VersionCandidate], as_of: date
) -> VersionCandidate | None:
    """Return the latest version effective on or before as_of.

    Equality is intentional: a document effective on the review date applies on that date.
    Ambiguous duplicate effective dates have no determined winner and therefore return None.
    """
    eligible = [candidate for candidate in extractions if candidate.effective_date <= as_of]
    if not eligible:
        return None
    latest_date = max(candidate.effective_date for candidate in eligible)
    latest = [candidate for candidate in eligible if candidate.effective_date == latest_date]
    if len(latest) != 1:
        return None
    return latest[0]


def _field_parts(field: object) -> tuple[object, object]:
    if isinstance(field, dict):
        return field.get("status"), field.get("value")
    return getattr(field, "status", None), getattr(field, "value", None)


def _present_string(field: object) -> str | None:
    status, value = _field_parts(field)
    if status != "present" or not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _get_field(extraction: object, name: str) -> object:
    if isinstance(extraction, dict):
        return extraction.get(name)
    return getattr(extraction, name, None)


def version_candidate_from_extraction(
    case_id: str, extraction: object
) -> VersionCandidate | None:
    """Build a candidate only from present, parseable version and effective-date evidence.

    Absent, ambiguous, or unparseable fields skip this document. That is an extraction
    failure. It is not a reason to ask the model which document is current.
    """
    version = _present_string(_get_field(extraction, "version"))
    effective_raw = _present_string(_get_field(extraction, "effective_date"))
    if version is None or effective_raw is None:
        return None
    try:
        effective_date = date.fromisoformat(effective_raw)
    except ValueError:
        return None
    return VersionCandidate(case_id=case_id, version=version, effective_date=effective_date)


def candidates_from_extractions(
    items: list[tuple[str, object]],
) -> list[VersionCandidate]:
    """Keep only documents whose version and effective date were extracted as present."""

    candidates: list[VersionCandidate] = []
    for case_id, extraction in items:
        candidate = version_candidate_from_extraction(case_id, extraction)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def score_version_selection(
    extractions: list[VersionCandidate],
    as_of: date,
    expected_case_id: str,
) -> VersionSelectionScore:
    """Score the Python rule's choice, not a free-text model opinion of currency.

    The model may only supply version/effective-date evidence. This function calls
    select_current_version and compares that result to expected_case_id.
    """
    selected = select_current_version(extractions, as_of)
    selected_id = selected.case_id if selected is not None else "none"
    base_detail = f"expected={expected_case_id}; selected={selected_id}"
    expected = next(
        (candidate for candidate in extractions if candidate.case_id == expected_case_id),
        None,
    )

    if selected is not None and selected.case_id == expected_case_id:
        return VersionSelectionScore(
            selected=selected,
            expected_case_id=expected_case_id,
            numerator=1,
            denominator=1,
            attribution="correct",
            detail=base_detail,
        )

    if expected is None:
        return VersionSelectionScore(
            selected=selected,
            expected_case_id=expected_case_id,
            numerator=0,
            denominator=1,
            attribution="bad_extraction",
            detail=f"{base_detail}; cause=bad_extraction",
        )

    if expected.effective_date > as_of:
        return VersionSelectionScore(
            selected=selected,
            expected_case_id=expected_case_id,
            numerator=0,
            denominator=1,
            attribution="bad_extraction",
            detail=f"{base_detail}; cause=bad_extraction",
        )

    if selected is None:
        return VersionSelectionScore(
            selected=None,
            expected_case_id=expected_case_id,
            numerator=0,
            denominator=1,
            attribution="ambiguous_rule",
            detail=f"{base_detail}; cause=ambiguous_rule",
        )

    return VersionSelectionScore(
        selected=selected,
        expected_case_id=expected_case_id,
        numerator=0,
        denominator=1,
        attribution="wrong_selection",
        detail=f"{base_detail}; cause=wrong_selection",
    )
