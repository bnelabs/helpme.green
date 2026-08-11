from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .domain import CaseFact, ConfirmationLabel


@dataclass(frozen=True)
class IntakeQuestion:
    key: str
    prompt: str
    answer_hint: str
    why_it_matters: str
    verification_hint: str


INTAKE_AGENDA: tuple[IntakeQuestion, ...] = (
    IntakeQuestion(
        "suspected_material",
        "What material stream are you describing?",
        "a short name, such as “electric wire”",
        "This sets the starting material family for the assessment.",
        "A label, specification, photo, or qualified review can strengthen this later.",
    ),
    IntakeQuestion(
        "composition",
        "What do you know about what it is made of?",
        "the conductor, insulation, or mixture — or “I don’t know”",
        "Composition determines which processing routes can even be considered.",
        "Use a product label/specification, representative inspection, or screening/test result.",
    ),
    IntakeQuestion(
        "contamination",
        "Are there oils, liquids, attachments, or hazardous parts that you know about?",
        "what you observed, or “I don’t know”",
        "A user statement is not clearance; condition and contamination can block a route.",
        "Describe what was observed and obtain appropriate screening before acting on a route.",
    ),
    IntakeQuestion(
        "physical_state",
        "What form is the material in right now?",
        "loose, baled, shredded, attached, or another simple description",
        "Form affects handling, preparation, and which routes are practical.",
        "A representative visual inspection or measured description can strengthen this.",
    ),
    IntakeQuestion(
        "volume",
        "What is the approximate lot size?",
        "a number with a unit, such as “500 kg”, or “I don’t know”",
        "Scale affects whether a route is practically comparable.",
        "Use a weighbridge, scale, invoice, or other dated quantity record.",
    ),
    IntakeQuestion(
        "humidity",
        "What is known about moisture and free liquids?",
        "dry, damp, free liquid, or “I don’t know”",
        "Moisture changes received mass, handling, and contamination risk.",
        "Record the observed condition or use a suitable measurement if it affects the decision.",
    ),
    IntakeQuestion(
        "origin",
        "Where did the stream come from?",
        "country, site, or supply chain — or “I don’t know”",
        "Geography controls which regulatory and source coverage can apply.",
        "Provide a supported origin and jurisdiction-specific review where required.",
    ),
)


class IntakeAgent:
    """Bounded interviewer: it labels facts and never evaluates a route."""

    mission = "Interview the user and produce explicitly labelled CaseFact records."
    inputs = "User answers and the deterministic intake agenda."
    outputs = "One confirmed CaseFact labelled declared, estimate, or unknown."
    autonomy_scope = "Ask agenda questions and preserve the user's stated evidence label."
    forbidden_actions = (
        "write a conclusion",
        "upgrade evidence",
        "skip fact confirmation",
        "promote dialogue into knowledge",
    )
    escalation = "Surface contradictions or malformed model output as an intake error."
    anti_myopia = (
        "If a shortcut would weaken evidence or coverage honesty, stop and preserve UNKNOWN."
    )
    model_system_contract = (
        "You are the helpme.green intake interviewer. Return one JSON object with only a fact key, "
        "the user's value, and label declared, estimate, or unknown. Never return a route, status, "
        "recommendation, source, or financial figure. The deterministic engine evaluates later."
    )

    def confirm(
        self,
        key: str,
        value: Any,
        label: str | ConfirmationLabel,
    ) -> CaseFact:
        return CaseFact.user(key, value, label)

    def from_model_response(self, response: Mapping[str, Any]) -> CaseFact:
        """Convert a bounded model proposal without allowing it to set evidence."""
        key = response.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Model intake response requires a non-empty fact key.")
        if "label" not in response:
            raise ValueError("Model intake response requires a confirmation label.")
        fact = self.confirm(str(key), response.get("value"), response["label"])
        proposed_state = response.get("evidence_state")
        if proposed_state is not None and str(proposed_state).upper() != fact.evidence_state.value:
            raise ValueError(
                "Model intake response attempted to set an inconsistent evidence state."
            )
        return fact

    def next_question(self, facts: Mapping[str, CaseFact]) -> IntakeQuestion | None:
        for question in INTAKE_AGENDA:
            fact = facts.get(question.key)
            if fact is None:
                return question
        return None

    def agenda(self) -> tuple[IntakeQuestion, ...]:
        return INTAKE_AGENDA
