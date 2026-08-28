"""Batch TriageMate workflow for fixture data or a future CI adapter."""

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from .triage_models import Category, Failure, TriageResult, evidence_block, validate_result
from .triage_tools import TriageTools

CONFIDENCE_THRESHOLD = float(os.getenv("TRIAGE_CONFIDENCE_THRESHOLD", "0.70"))


def _heuristic_classify(failure: Failure, history: list[dict[str, Any]]) -> TriageResult:
    """Offline fallback for the demo; an LLM classifier can be injected into triage_batch."""
    error = f"{failure.error_type} {failure.error_message} {failure.service_log}".lower()
    history_ref = history[0].get("source") if history else None
    if history and any("flak" in item.get("text", "").lower() for item in history):
        category, confidence = Category.KNOWN_FLAKE, 0.86
        quote = history[0].get("text", "")
        action = "Review the known flaky pattern and rerun the test."
    elif any(word in error for word in ("credential", "service unavailable", "connection refused", "seed", "network")):
        category, confidence = Category.ENVIRONMENT, 0.83
        quote = failure.service_log or failure.error_message
        action = "Check the affected service, credentials, and test data."
    elif ("http 5" in error or "internal server error" in error) and (failure.service_log or failure.git_diff_summary):
        category, confidence = Category.PRODUCT_BUG, 0.84
        quote = failure.service_log or failure.git_diff_summary
        action = "Investigate the backend error and the recent component change."
    elif any(word in error for word in ("assertion", "locator", "element not found", "expected")):
        category, confidence = Category.TEST_FAILURE, 0.78
        quote = failure.error_message or failure.stack_trace
        action = "Inspect the assertion, locator, or test data."
    elif failure.stack_trace or failure.service_log or failure.git_diff_summary:
        category, confidence = Category.PRODUCT_BUG, 0.82
        quote = failure.stack_trace or failure.service_log or failure.git_diff_summary
        action = "Investigate the component change and attach the cited evidence."
    else:
        category, confidence = Category.INSUFFICIENT_EVIDENCE, 0.25
        quote, action = "", "Collect the missing test artifacts before classifying."
    return TriageResult(
        category=category,
        confidence=confidence,
        rationale=f"The supplied failure evidence supports {category.value}.",
        evidence_quote=quote,
        history_ref=history_ref,
        suggested_owner=failure.owner or None,
        recommended_action=action,
    )


def _parse_llm_result(value: str | dict[str, Any]) -> TriageResult:
    payload = json.loads(value) if isinstance(value, str) else value
    return TriageResult(
        category=Category(payload["category"]),
        confidence=float(payload["confidence"]),
        rationale=str(payload.get("rationale", "")),
        evidence_quote=str(payload.get("evidence_quote", "")),
        history_ref=payload.get("history_ref"),
        suggested_owner=payload.get("suggested_owner"),
        recommended_action=str(payload.get("recommended_action", "")),
    )


def _llm_classifier(failure: Failure, evidence: str) -> TriageResult:
    from openai import OpenAI

    client = OpenAI(
        base_url=os.getenv("TRIAGE_OPENAI_BASE_URL", os.getenv("COPILOT_GATEWAY_URL", "http://127.0.0.1:3030/v1")),
        api_key=os.getenv("TRIAGE_OPENAI_API_KEY", "anything"),
    )
    prompt = f"""Classify one CI failure using only the delimited evidence.
Categories: PRODUCT_BUG, TEST_FAILURE, ENVIRONMENT, KNOWN_FLAKE, INSUFFICIENT_EVIDENCE.
Return JSON only with category, confidence, rationale, evidence_quote, history_ref,
suggested_owner, recommended_action. KNOWN_FLAKE requires an explicit history citation.
<evidence>\n{evidence}\n</evidence>"""
    response = client.chat.completions.create(
        model=os.getenv("TRIAGE_MODEL", "gpt-4o-mini"),
        temperature=0,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_llm_result(response.choices[0].message.content or "{}")


def _classify(failure: Failure, evidence: str, classifier: Callable[[Failure, str], TriageResult] | None) -> TriageResult:
    if classifier:
        for attempt in range(3):
            try:
                return classifier(failure, evidence)
            except Exception:
                if attempt == 2:
                    return TriageResult(
                        category=Category.INSUFFICIENT_EVIDENCE,
                        confidence=0.0,
                        rationale="The classifier failed after three attempts; human analysis is required.",
                        evidence_quote="",
                        recommended_action="Use the manual triage workflow.",
                    )
    return _heuristic_classify(failure, [])


def triage_batch(
    failures: list[Failure],
    tools: TriageTools,
    classifier: Callable[[Failure, str], TriageResult] | None = None,
    threshold: float = CONFIDENCE_THRESHOLD,
) -> list[dict[str, Any]]:
    records = []
    for failure in failures:
        tools.get_test_artifacts(failure.run_id, failure.test_id)
        query = f"{failure.test_name} {failure.error_type} {failure.error_message}"
        history = tools.search_failure_history(query, failure.component)
        if not history or "flak" not in " ".join(item.get("text", "") for item in history).lower():
            tools.get_git_diff_since_last_green(failure.component, failure)
        if "timeout" in query.lower() or "flak" in query.lower():
            tools.get_flaky_status(failure.test_id)
        evidence = evidence_block(failure, history)
        result = _classify(failure, evidence, classifier)
        if classifier is None:
            result = _heuristic_classify(failure, history)
        validate_result(result, evidence, threshold)
        if result.category is Category.PRODUCT_BUG and not result.needs_human:
            result.ticket_draft = tools.draft_failure_ticket(failure, result.to_dict())
        records.append({"failure": failure, "result": result, "evidence": evidence})
    records.sort(key=lambda item: (item["result"].category is not Category.PRODUCT_BUG, item["result"].confidence))
    return records


def write_report(records: list[dict[str, Any]], output_dir: str | Path = "reports") -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = output / "triage_report.json", output / "triage_report.md"
    json_path.write_text(json.dumps([{"failure": vars(item["failure"]), "result": item["result"].to_dict()} for item in records], indent=2, default=str), encoding="utf-8")
    lines = ["# TriageMate Report", "", f"Records: {len(records)}", ""]
    for index, item in enumerate(records, 1):
        failure, result = item["failure"], item["result"]
        lines += [
            f"## {index}. {failure.test_name}",
            f"- Category: **{result.category.value}**",
            f"- Confidence: `{result.confidence:.2f}`",
            f"- Human review: `{result.needs_human}`",
            f"- Rationale: {result.rationale}",
            f"- Evidence: `{result.evidence_quote or 'missing'}`",
            f"- History: `{result.history_ref or 'none'}`",
            f"- Action: {result.recommended_action}",
            "",
        ]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return markdown_path, json_path