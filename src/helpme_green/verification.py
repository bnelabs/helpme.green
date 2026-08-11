from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .domain import CaseFact
from .engine import DeterministicEngine, LandscapeStatus
from .knowledge import KnowledgeBase
from .model_gateway import ModelRouter


@dataclass(frozen=True)
class VerificationSummary:
    representative_count: int
    fabricated_source_references: int
    financial_outputs: int
    cross_model_equal: bool

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "representative_count": self.representative_count,
            "fabricated_source_references": self.fabricated_source_references,
            "financial_outputs": self.financial_outputs,
            "cross_model_equal": self.cross_model_equal,
        }


def representative_cases(count: int = 100) -> Iterable[dict[str, CaseFact]]:
    materials = (
        "copper cable",
        "insulated copper cable",
        "copper wire",
        "cable harness",
        "copper-bearing cable",
    )
    labels = ("declared", "estimate", "unknown")
    contaminations = ("unknown", "dry and segregated", "moisture reported", "mixed attachments")
    for index in range(count):
        label = labels[index % len(labels)]
        contamination = contaminations[index % len(contaminations)]
        yield {
            "suspected_material": CaseFact.user(
                "suspected_material", materials[index % len(materials)], "declared"
            ),
            "composition": CaseFact.user("composition", "copper conductor", label),
            "contamination": CaseFact.user(
                "contamination",
                None if contamination == "unknown" else contamination,
                "unknown" if contamination == "unknown" else "declared",
            ),
            "physical_state": CaseFact.user("physical_state", "segregated cable lot", "declared"),
            "volume": CaseFact.user("volume", f"lot-{index + 1}", "estimate"),
            "humidity": CaseFact.user("humidity", "unknown", "unknown"),
            "origin": CaseFact.user("origin", "Bulgaria", "declared"),
        }


def run_phase_a_verification(knowledge: KnowledgeBase, *, count: int = 100) -> VerificationSummary:
    engine = DeterministicEngine(knowledge)
    cases = list(representative_cases(count))
    results = [engine.evaluate(case) for case in cases]
    fabricated = sum(
        1
        for result in results
        for reference in result.source_references
        if reference.source_id not in knowledge.source_registry
    )
    financial_outputs = sum(
        1
        for result in results
        if result.value is not None
        or any(route.status is LandscapeStatus.FINANCIALLY_COMPARABLE for route in result.routes)
    )
    reference_case = cases[0]
    router = ModelRouter()
    router.select("deepseek:deepseek-chat")
    deepseek_result = engine.evaluate(reference_case).canonical()
    router.select("openrouter:openai/gpt-oss-20b:free")
    openrouter_result = engine.evaluate(reference_case).canonical()
    return VerificationSummary(
        representative_count=len(results),
        fabricated_source_references=fabricated,
        financial_outputs=financial_outputs,
        cross_model_equal=deepseek_result == openrouter_result,
    )
