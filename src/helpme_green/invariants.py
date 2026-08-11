from __future__ import annotations

import re
from collections.abc import Mapping

from .domain import CaseFact, ConfirmationLabel, EvidenceState

INVARIANT_IDS: tuple[str, ...] = tuple(f"R{index}" for index in range(1, 13))


def user_label_state(label: ConfirmationLabel) -> EvidenceState:
    if label is ConfirmationLabel.DECLARED:
        return EvidenceState.HEARSAY
    if label is ConfirmationLabel.ESTIMATE:
        return EvidenceState.EDUCATED_ESTIMATE
    return EvidenceState.UNKNOWN


def geography_is_covered(geography: str) -> bool:
    normalized = " ".join(geography.casefold().split())
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    return "bulgaria" in tokens or "european union" in normalized or "eu" in tokens


def contamination_gate(facts: Mapping[str, CaseFact]) -> str:
    fact = facts.get("contamination")
    if fact is None or fact.is_unknown:
        return "R10_CONTAMINATION_UNKNOWN"
    if fact.evidence_state.rank < EvidenceState.SCREENED.rank:
        return "R10_CONTAMINATION_NOT_SCREENED"
    return ""


def global_invariant_blocks(facts: Mapping[str, CaseFact], geography: str) -> tuple[str, ...]:
    blocks: list[str] = []
    if not geography_is_covered(geography):
        blocks.append("R6_JURISDICTION_NOT_COVERED")
    contamination_block = contamination_gate(facts)
    if contamination_block:
        blocks.append(contamination_block)
    return tuple(blocks)
