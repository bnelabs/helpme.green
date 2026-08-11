from __future__ import annotations

from pathlib import Path

from helpme_green.knowledge import KnowledgeBase
from helpme_green.verification import run_phase_a_verification


def test_phase_a_representative_and_cross_model_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    summary = run_phase_a_verification(KnowledgeBase.from_repository(root), count=100)

    assert summary.representative_count == 100
    assert summary.fabricated_source_references == 0
    assert summary.financial_outputs == 0
    assert summary.cross_model_equal
