"""Data contracts and safety checks for the TriageMate workflow."""

from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any


class Category(str, Enum):
    PRODUCT_BUG = "PRODUCT_BUG"
    TEST_FAILURE = "TEST_FAILURE"
    ENVIRONMENT = "ENVIRONMENT"
    KNOWN_FLAKE = "KNOWN_FLAKE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class Failure:
    run_id: str
    test_id: str
    test_name: str
    suite: str
    component: str
    owner: str = ""
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    service_log: str = ""
    expected: str = ""
    actual: str = ""
    environment: str = ""
    failure_url: str | None = None
    git_diff_summary: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Failure":
        required = ("run_id", "test_id", "test_name", "suite", "component")
        missing = [name for name in required if not value.get(name)]
        if missing:
            raise ValueError(f"Failure is missing required fields: {', '.join(missing)}")
        known_fields = {item.name for item in fields(cls) if item.init}
        return cls(**{name: value[name] for name in known_fields if name in value})


@dataclass
class TriageResult:
    category: Category
    confidence: float
    rationale: str
    evidence_quote: str
    history_ref: str | None = None
    suggested_owner: str | None = None
    recommended_action: str = ""
    needs_human: bool = False
    validation_errors: list[str] = field(default_factory=list)
    ticket_draft: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "category": self.category.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence_quote": self.evidence_quote,
            "history_ref": self.history_ref,
            "suggested_owner": self.suggested_owner,
            "recommended_action": self.recommended_action,
            "needs_human": self.needs_human,
        }
        if self.validation_errors:
            result["validation_errors"] = self.validation_errors
        if self.ticket_draft is not None:
            result["ticket_draft"] = self.ticket_draft
        return result


def evidence_block(failure: Failure, history: list[dict[str, Any]]) -> str:
    history_text = "\n\n---\n\n".join(
        f"[{item.get('source', 'history')}] {item.get('text', '')}" for item in history
    ) or "No matching history was retrieved."
    return "\n".join(
        (
            f"[Test] {failure.test_name} - {failure.suite}, owner {failure.owner}",
            f"[Failure] {failure.error_type}: {failure.error_message}",
            f"[Stack trace] {failure.stack_trace}",
            f"[Service log] {failure.service_log}",
            f"[Code change] {failure.git_diff_summary}",
            f"[History]\n{history_text}",
        )
    )


def validate_result(result: TriageResult, supplied_evidence: str, threshold: float = 0.70) -> TriageResult:
    errors: list[str] = []
    if not 0.0 <= result.confidence <= 1.0:
        errors.append("confidence must be between 0.0 and 1.0")
    if not result.evidence_quote or result.evidence_quote not in supplied_evidence:
        errors.append("evidence_quote must be a non-empty verbatim substring of supplied evidence")
    if result.category is Category.KNOWN_FLAKE and not result.history_ref:
        errors.append("KNOWN_FLAKE requires a history_ref")
    if result.confidence < threshold:
        errors.append(f"confidence is below the {threshold:.2f} human-review threshold")

    result.validation_errors = errors
    result.needs_human = bool(errors) or result.category is Category.INSUFFICIENT_EVIDENCE
    if errors and any("history_ref" in error or "evidence_quote" in error for error in errors):
        result.category = Category.INSUFFICIENT_EVIDENCE
    return result