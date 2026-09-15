from __future__ import annotations

from typing import Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field

TaskName = Literal["triage", "summarization", "extraction"]
FieldStatus = Literal["present", "absent", "ambiguous"]
DocumentStatus = Literal["valid", "contradictory", "superseded", "unsupported"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceField(StrictModel):
    value: str | list[str] | None
    status: FieldStatus
    citation: str | None = None


class TriageOutput(StrictModel):
    queue: Literal[
        "card_dispute",
        "fraud_report",
        "account_servicing",
        "lending",
        "complaint",
        "escalate",
        "unsupported",
    ]
    escalation_required: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    draft_reply: str
    human_review_required: Literal[True]
    customer_outcome: None = None


class SummarizationOutput(StrictModel):
    document_status: DocumentStatus
    title: EvidenceField
    version: EvidenceField
    effective_date: EvidenceField
    purpose: EvidenceField
    required_steps: EvidenceField
    exceptions: EvidenceField

    def evidence_fields(self) -> dict[str, EvidenceField]:
        return {
            "title": self.title,
            "version": self.version,
            "effective_date": self.effective_date,
            "purpose": self.purpose,
            "required_steps": self.required_steps,
            "exceptions": self.exceptions,
        }


class PolicyExtraction(StrictModel):
    document_status: DocumentStatus
    policy_name: EvidenceField
    version: EvidenceField
    effective_date: EvidenceField
    jurisdictions: EvidenceField
    beneficial_ownership_threshold: EvidenceField
    review_frequency: EvidenceField
    required_documents: EvidenceField

    def evidence_fields(self) -> dict[str, EvidenceField]:
        return {
            "policy_name": self.policy_name,
            "version": self.version,
            "effective_date": self.effective_date,
            "jurisdictions": self.jurisdictions,
            "beneficial_ownership_threshold": self.beneficial_ownership_threshold,
            "review_frequency": self.review_frequency,
            "required_documents": self.required_documents,
        }


OUTPUT_SCHEMAS: dict[TaskName, type[StrictModel]] = {
    "triage": TriageOutput,
    "summarization": SummarizationOutput,
    "extraction": PolicyExtraction,
}


def _type_text(annotation: object) -> str:
    origin = get_origin(annotation)
    if origin is Literal:
        options = ", ".join(repr(value) for value in get_args(annotation))
        return f"one of {options}"
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        inner = ", ".join(
            f"{name}: {_type_text(field.annotation)}"
            for name, field in annotation.model_fields.items()
        )
        return f"object {{ {inner} }}"
    if origin is not None:
        args = ", ".join(_type_text(arg) for arg in get_args(annotation))
        return f"{getattr(origin, '__name__', origin)}[{args}]"
    return getattr(annotation, "__name__", str(annotation))


def schema_description(model: type[BaseModel]) -> str:
    lines = [
        f"Return one filled JSON instance of {model.__name__}.",
        "Do not return a JSON Schema. Do not include $defs, properties, required, or type.",
        "document_status is a string, not an EvidenceField object.",
        "Allowed keys:",
    ]
    for name, field in model.model_fields.items():
        lines.append(f"- {name}: {_type_text(field.annotation)}")
    return "\n".join(lines)
