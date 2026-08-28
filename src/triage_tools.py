"""Read-only fixture-backed tools used by the triage orchestrator."""

import json
from pathlib import Path
from typing import Any

from .triage_models import Failure


class TriageTools:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self._failures = self._load_json("failures.json", [])
        self._history = self._load_json("history.json", [])
        self._flaky = self._load_json("flaky_register.json", [])
        self.calls: list[dict[str, Any]] = []

    def _load_json(self, name: str, default: Any) -> Any:
        path = self.data_dir / name
        if not path.exists():
            return default
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def load_failures(self) -> list[Failure]:
        return [Failure.from_dict(item) for item in self._failures]

    def get_test_artifacts(self, run_id: str, test_id: str) -> dict[str, str]:
        self.calls.append({"tool": "get_test_artifacts", "run_id": run_id, "test_id": test_id})
        for item in self._failures:
            if item.get("run_id") == run_id and item.get("test_id") == test_id:
                return {
                    "stack_trace": item.get("stack_trace", ""),
                    "service_log": item.get("service_log", ""),
                    "expected": item.get("expected", ""),
                    "actual": item.get("actual", ""),
                    "environment": item.get("environment", ""),
                }
        raise KeyError(f"Failure not found: {run_id}/{test_id}")

    def get_git_diff_since_last_green(self, component: str, failure: Failure) -> str:
        self.calls.append({"tool": "get_git_diff_since_last_green", "component": component})
        return failure.git_diff_summary

    def search_failure_history(self, query: str, component: str, top_k: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"tool": "search_failure_history", "query": query, "component": component})
        terms = {term.lower() for term in query.split() if len(term) > 2}
        matches = []
        for item in self._history:
            if item.get("component") not in (None, "", component):
                continue
            text = item.get("text", "")
            score = sum(term in text.lower() for term in terms)
            if score:
                matches.append((score, item))
        return [item for _, item in sorted(matches, key=lambda pair: pair[0], reverse=True)[:top_k]]

    def get_flaky_status(self, test_id: str) -> dict[str, Any] | None:
        self.calls.append({"tool": "get_flaky_status", "test_id": test_id})
        return next((item for item in self._flaky if item.get("test_id") == test_id), None)

    def draft_failure_ticket(self, failure: Failure, result: dict[str, Any]) -> dict[str, Any]:
        """Create a draft only; this function has no external write capability."""
        self.calls.append({"tool": "draft_failure_ticket", "test_id": failure.test_id, "write": False})
        return {
            "title": f"Regression failure: {failure.test_name}",
            "component": failure.component,
            "steps": [f"Run CI test {failure.test_id} in {failure.suite}"],
            "expected": failure.expected or "Test passes",
            "actual": failure.actual or failure.error_message,
            "environment": failure.environment or "Not supplied",
            "evidence_links": [failure.failure_url] if failure.failure_url else [],
            "rationale": result.get("rationale", ""),
        }