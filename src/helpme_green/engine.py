from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .domain import CaseFact, EvidenceState, canonical_json
from .invariants import INVARIANT_IDS, global_invariant_blocks, user_label_state
from .knowledge import KnowledgeBase, SourceReference


class InvariantViolation(RuntimeError):
    """Raised when input or output would violate the honest-spine invariants."""


class LandscapeStatus(StrEnum):
    PRELIMINARY_CANDIDATE = "PRELIMINARY_CANDIDATE"
    CONDITIONAL = "CONDITIONAL"
    TECHNICALLY_SUPPORTED = "TECHNICALLY_SUPPORTED"
    FINANCIALLY_COMPARABLE = "FINANCIALLY_COMPARABLE"
    BLOCKED = "BLOCKED"
    NOT_RELEVANT = "NOT_RELEVANT"
    RESEARCH_STAGE = "RESEARCH_STAGE"


class RequirementState(StrEnum):
    SATISFIED = "SATISFIED"
    UNKNOWN = "UNKNOWN"
    WEAK_EVIDENCE = "WEAK_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RequirementEvaluation:
    key: str
    dimension: str
    fact_key: str
    fact_value: Any
    fact_evidence_state: EvidenceState
    state: RequirementState
    minimum_evidence_state: EvidenceState
    applied_policy: str | None
    blocking_scope: str
    claim_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "dimension": self.dimension,
            "fact_key": self.fact_key,
            "fact_value": self.fact_value,
            "fact_evidence_state": self.fact_evidence_state.value,
            "state": self.state.value,
            "minimum_evidence_state": self.minimum_evidence_state.value,
            "applied_policy": self.applied_policy,
            "blocking_scope": self.blocking_scope,
            "claim_key": self.claim_key,
        }


@dataclass(frozen=True)
class ReadinessResult:
    dimension: str
    satisfied: int
    required: int
    complete: bool
    remaining_requirement_keys: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "satisfied": self.satisfied,
            "required": self.required,
            "complete": self.complete,
            "remaining_requirement_keys": list(self.remaining_requirement_keys),
        }


@dataclass(frozen=True)
class ClaimView:
    key: str
    claim_type: str
    statement: str
    evidence_state: str
    confidence: str
    applicability: str
    limitations: str
    source_references: tuple[SourceReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "claim_type": self.claim_type,
            "statement": self.statement,
            "evidence_state": self.evidence_state,
            "confidence": self.confidence,
            "applicability": self.applicability,
            "limitations": self.limitations,
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True)
class ActionView:
    key: str
    title: str
    description: str
    route_keys: tuple[str, ...]
    requirement_keys: tuple[str, ...]
    priority: str
    acquisition_cost_class: str
    source_references: tuple[SourceReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "route_keys": list(self.route_keys),
            "requirement_keys": list(self.requirement_keys),
            "priority": self.priority,
            "acquisition_cost_class": self.acquisition_cost_class,
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True)
class RouteEvaluation:
    key: str
    business_id: str
    title: str
    status: LandscapeStatus
    maturity: str
    evidence_class: str
    readiness: Mapping[str, ReadinessResult]
    requirement_results: tuple[RequirementEvaluation, ...]
    claims: tuple[ClaimView, ...]
    source_references: tuple[SourceReference, ...]

    @property
    def decision_ready(self) -> bool:
        return self.status is LandscapeStatus.FINANCIALLY_COMPARABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "business_id": self.business_id,
            "title": self.title,
            "status": self.status.value,
            "maturity": self.maturity,
            "evidence_class": self.evidence_class,
            "decision_ready": self.decision_ready,
            "readiness": {key: value.to_dict() for key, value in sorted(self.readiness.items())},
            "requirement_results": [item.to_dict() for item in self.requirement_results],
            "claims": [item.to_dict() for item in self.claims],
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True)
class EvaluationResult:
    tier: str
    advisory_only: bool
    geography: str
    knowledge_digest: str
    knowledge_pack_versions: tuple[str, ...]
    routes: tuple[RouteEvaluation, ...]
    next_actions: tuple[ActionView, ...]
    source_references: tuple[SourceReference, ...]
    value_blockers: tuple[str, ...]
    invariant_ids: tuple[str, ...] = INVARIANT_IDS
    invariant_blocks: tuple[str, ...] = ()
    value: None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "advisory_only": self.advisory_only,
            "geography": self.geography,
            "knowledge_digest": self.knowledge_digest,
            "knowledge_pack_versions": list(self.knowledge_pack_versions),
            "routes": [item.to_dict() for item in self.routes],
            "next_actions": [item.to_dict() for item in self.next_actions],
            "source_references": [item.to_dict() for item in self.source_references],
            "value_blockers": list(self.value_blockers),
            "invariant_ids": list(self.invariant_ids),
            "invariant_blocks": list(self.invariant_blocks),
            "value": self.value,
        }

    def canonical(self) -> str:
        return canonical_json(self.to_dict())


def _normalized_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).casefold()


def _contains(container: Any, expected: Any) -> bool:
    if isinstance(container, str) and isinstance(expected, str):
        return expected.casefold() in container.casefold()
    if isinstance(container, (list, tuple, set, frozenset)):
        return expected in container
    if isinstance(container, Mapping):
        return expected in container
    return False


def _predicate_matches(predicate: Mapping[str, Any], value: Any) -> bool:
    operator = str(predicate.get("operator", "EQUALS")).upper()
    expected = predicate.get("value")
    if operator == "EQUALS":
        return bool(value == expected)
    if operator == "NOT_EQUALS":
        return bool(value != expected)
    if operator in {"IN", "NORMALIZED_IN"}:
        if not isinstance(expected, (list, tuple, set, frozenset)):
            return False
        if operator == "IN":
            return value in expected
        normalized = _normalized_text(value)
        return normalized is not None and normalized in {
            _normalized_text(item) for item in expected
        }
    if operator == "NOT_IN":
        return isinstance(expected, (list, tuple, set, frozenset)) and value not in expected
    if operator == "CONTAINS":
        return _contains(value, expected)
    if operator == "EXISTS":
        return value is not None
    return False


def _dimension_for(key: str) -> str:
    normalized = key.casefold()
    if any(token in normalized for token in ("material", "composition", "conductor")):
        return "MATERIAL_IDENTIFICATION"
    if any(token in normalized for token in ("safety", "legal", "authorization", "hazard")):
        return "SAFETY_LEGAL"
    if any(token in normalized for token in ("output", "buyer", "receiver", "destination")):
        return "OUTPUT_BUYER"
    if any(
        token in normalized for token in ("commercial", "financial", "cost", "value", "liability")
    ):
        return "FINANCIAL"
    return "TECHNICAL"


def _policy(value: Any, default: str = "CONDITIONAL") -> str:
    text = str(value or default).upper()
    if text == "INELIGIBLE":
        return "BLOCK"
    return text


def _requirement(route: Mapping[str, Any], raw: Mapping[str, Any]) -> dict[str, Any]:
    predicate = raw.get("predicate")
    if not isinstance(predicate, Mapping):
        predicate = {
            "fact_key": raw.get("key", ""),
            "operator": raw.get("operator", "EQUALS"),
            "value": raw.get("value"),
        }
    key = str(raw.get("key", ""))
    return {
        "key": key,
        "dimension": str(raw.get("dimension") or _dimension_for(key)),
        "predicate": predicate,
        "minimum": EvidenceState.from_pack_level(
            str(raw.get("minimum_evidence_state") or raw.get("minimum_evidence_level", "E0"))
        ),
        "unknown_policy": _policy(raw.get("unknown_policy") or raw.get("unknown_action")),
        "failed_policy": _policy(raw.get("failed_policy") or raw.get("unknown_action")),
        "blocking_scope": str(raw.get("blocking_scope", "Affected conclusion")),
        "claim_key": str(raw.get("claim_key", "")),
    }


def _fact_map(facts: Mapping[str, CaseFact | Any]) -> dict[str, CaseFact]:
    normalized: dict[str, CaseFact] = {}
    for key, value in facts.items():
        normalized[str(key)] = (
            value if isinstance(value, CaseFact) else CaseFact.user(str(key), value, "declared")
        )
    return normalized


class DeterministicEngine:
    """Evaluate pack requirements; no model output enters this class."""

    def __init__(self, knowledge: KnowledgeBase) -> None:
        self.knowledge = knowledge

    def evaluate(
        self,
        facts: Mapping[str, CaseFact | Any],
        *,
        geography: str = "Bulgaria / EU",
    ) -> EvaluationResult:
        fact_map = _fact_map(facts)
        self._validate_fact_provenance(fact_map)
        invariant_blocks = global_invariant_blocks(fact_map, geography)
        routes = tuple(
            self._evaluate_route(route, fact_map, invariant_blocks)
            for route in self.knowledge.copper_routes_v03
        )
        actions = self._invariant_actions(self._next_actions(routes), routes, invariant_blocks)
        refs_by_id = {ref.source_id: ref for route in routes for ref in route.source_references}
        blockers = self._value_blockers(routes, invariant_blocks)
        return EvaluationResult(
            tier="DECISION",
            advisory_only=True,
            geography=geography,
            knowledge_digest=self.knowledge.digest,
            knowledge_pack_versions=("copper-cable-v0.2", "discovery-v0.3"),
            routes=routes,
            next_actions=actions,
            source_references=tuple(refs_by_id[key] for key in sorted(refs_by_id)),
            value_blockers=blockers,
            invariant_blocks=invariant_blocks,
        )

    def _validate_fact_provenance(self, facts: Mapping[str, CaseFact]) -> None:
        for fact in facts.values():
            missing = sorted(
                set(fact.provenance.source_ids).difference(self.knowledge.source_registry)
            )
            if missing:
                raise InvariantViolation(
                    f"Fact {fact.key!r} references unregistered source(s): {', '.join(missing)}"
                )
            if (
                fact.provenance.untrusted
                and fact.evidence_state.rank >= EvidenceState.OBSERVED.rank
            ):
                raise InvariantViolation(
                    f"Untrusted MCP fact {fact.key!r} attempted an evidence-state upgrade."
                )
            if fact.provenance.kind in {"user", "mcp"}:
                expected = user_label_state(fact.label)
                if fact.evidence_state is not expected:
                    raise InvariantViolation(
                        f"Fact {fact.key!r} has an evidence state inconsistent with its label."
                    )
            if fact.evidence_state.rank >= EvidenceState.OBSERVED.rank:
                if fact.provenance.kind != "qualified-review":
                    raise InvariantViolation(
                        f"Fact {fact.key!r} has elevated evidence without qualified review."
                    )
                if not fact.provenance.source_ids:
                    raise InvariantViolation(
                        f"Fact {fact.key!r} has elevated evidence without source IDs."
                    )

    def _evaluate_route(
        self,
        route: Mapping[str, Any],
        facts: Mapping[str, CaseFact],
        invariant_blocks: tuple[str, ...],
    ) -> RouteEvaluation:
        requirements = tuple(
            _requirement(route, raw)
            for raw in route.get("requirements", []) or []
            if isinstance(raw, Mapping)
        )
        evaluations = tuple(self._evaluate_requirement(item, facts) for item in requirements)
        readiness = self._readiness(evaluations)
        status = self._route_status(route, evaluations, readiness, invariant_blocks)
        claims = self._claims(route)
        source_ids = self.knowledge.route_source_ids(route)
        refs = self.knowledge.source_references_for(source_ids, route)
        if not claims and not refs:
            raise InvariantViolation(f"Route {route.get('id')} has no registered source basis.")
        return RouteEvaluation(
            key=str(route.get("id", "")),
            business_id=str(route.get("business_id", route.get("id", ""))),
            title=str(route.get("title", "")),
            status=status,
            maturity=str(route.get("maturity", "")),
            evidence_class=str(route.get("evidence_class", "")),
            readiness=readiness,
            requirement_results=evaluations,
            claims=claims,
            source_references=refs,
        )

    def _evaluate_requirement(
        self,
        requirement: Mapping[str, Any],
        facts: Mapping[str, CaseFact],
    ) -> RequirementEvaluation:
        predicate = requirement["predicate"]
        fact_key = str(predicate.get("fact_key", ""))
        fact = facts.get(fact_key)
        value = fact.value if fact is not None else None
        evidence = fact.evidence_state if fact is not None else EvidenceState.UNKNOWN
        if fact is None or fact.is_unknown:
            state = RequirementState.UNKNOWN
            policy = str(requirement["unknown_policy"])
        elif fact.conflict_note:
            state = RequirementState.CONFLICTING_EVIDENCE
            policy = "BLOCK"
        elif evidence.rank < requirement["minimum"].rank:
            state = RequirementState.WEAK_EVIDENCE
            policy = str(requirement["unknown_policy"])
        elif not _predicate_matches(predicate, value):
            state = RequirementState.FAILED
            policy = str(requirement["failed_policy"])
        else:
            state = RequirementState.SATISFIED
            policy = None
        return RequirementEvaluation(
            key=str(requirement["key"]),
            dimension=str(requirement["dimension"]),
            fact_key=fact_key,
            fact_value=value,
            fact_evidence_state=evidence,
            state=state,
            minimum_evidence_state=requirement["minimum"],
            applied_policy=policy,
            blocking_scope=str(requirement["blocking_scope"]),
            claim_key=str(requirement["claim_key"]),
        )

    def _readiness(
        self, evaluations: tuple[RequirementEvaluation, ...]
    ) -> dict[str, ReadinessResult]:
        dimensions = {item.dimension for item in evaluations}
        output: dict[str, ReadinessResult] = {}
        for dimension in sorted(dimensions):
            relevant = tuple(item for item in evaluations if item.dimension == dimension)
            remaining = tuple(
                item.key for item in relevant if item.state is not RequirementState.SATISFIED
            )
            output[dimension] = ReadinessResult(
                dimension=dimension,
                satisfied=len(relevant) - len(remaining),
                required=len(relevant),
                complete=not remaining,
                remaining_requirement_keys=remaining,
            )
        return output

    def _route_status(
        self,
        route: Mapping[str, Any],
        evaluations: tuple[RequirementEvaluation, ...],
        readiness: Mapping[str, ReadinessResult],
        invariant_blocks: tuple[str, ...],
    ) -> LandscapeStatus:
        material = next(
            (
                item
                for item in evaluations
                if item.dimension == "MATERIAL_IDENTIFICATION"
                and item.key in {"material-family-match", "material_family_match"}
            ),
            None,
        )
        if material is not None and material.state is RequirementState.FAILED:
            return LandscapeStatus.NOT_RELEVANT
        if "R6_JURISDICTION_NOT_COVERED" in invariant_blocks:
            return LandscapeStatus.BLOCKED
        if any(block.startswith("R10_") for block in invariant_blocks):
            return LandscapeStatus.BLOCKED
        if material is not None and material.state is not RequirementState.SATISFIED:
            return LandscapeStatus.PRELIMINARY_CANDIDATE
        if any(item.state is RequirementState.CONFLICTING_EVIDENCE for item in evaluations):
            return LandscapeStatus.BLOCKED
        if any(
            item.state is not RequirementState.SATISFIED and item.applied_policy == "BLOCK"
            for item in evaluations
        ):
            return LandscapeStatus.BLOCKED
        evidence_class = str(route.get("evidence_class", ""))
        all_complete = all(item.state is RequirementState.SATISFIED for item in evaluations)
        if (
            all_complete
            and evidence_class == "ESTABLISHED"
            and str(route.get("cost_model_coverage", "UNKNOWN")) == "COMPLETE"
        ):
            return LandscapeStatus.FINANCIALLY_COMPARABLE
        if evidence_class in {"RESEARCH_STAGE", "RESEARCH_SUPPORTED"}:
            return LandscapeStatus.RESEARCH_STAGE
        if any(item.applied_policy == "CONDITIONAL" for item in evaluations):
            return LandscapeStatus.CONDITIONAL
        if all(
            readiness.get(dimension, ReadinessResult(dimension, 0, 0, False, ())).complete
            for dimension in ("MATERIAL_IDENTIFICATION", "SAFETY_LEGAL", "TECHNICAL")
        ):
            return LandscapeStatus.TECHNICALLY_SUPPORTED
        return LandscapeStatus.PRELIMINARY_CANDIDATE

    def _claims(self, route: Mapping[str, Any]) -> tuple[ClaimView, ...]:
        claims: list[ClaimView] = []
        for raw in route.get("claims", []) or []:
            if not isinstance(raw, Mapping):
                continue
            links = raw.get("sources", []) or []
            source_ids = tuple(
                str(link["source_id"])
                for link in links
                if isinstance(link, Mapping) and link.get("source_id")
            )
            refs = self.knowledge.source_references_for(source_ids, route)
            if not refs:
                raise InvariantViolation(
                    f"Claim {raw.get('key')} in route {route.get('id')} has no source reference."
                )
            claims.append(
                ClaimView(
                    key=str(raw.get("key", "")),
                    claim_type=str(raw.get("claim_type", "")),
                    statement=str(raw.get("statement", "")),
                    evidence_state=str(raw.get("evidence_state", "")),
                    confidence=str(raw.get("confidence", "")),
                    applicability=str(raw.get("applicability", "")),
                    limitations=str(raw.get("limitations", "")),
                    source_references=refs,
                )
            )
        return tuple(claims)

    def _next_actions(self, routes: tuple[RouteEvaluation, ...]) -> tuple[ActionView, ...]:
        route_cards = {str(route.get("id")): route for route in self.knowledge.copper_routes_v03}
        actions: dict[str, ActionView] = {}
        for evaluated in routes:
            card = route_cards[evaluated.key]
            missing = {
                item.key
                for item in evaluated.requirement_results
                if item.state is not RequirementState.SATISFIED
            }
            business_id = str(card.get("business_id", evaluated.key))
            for gap in card.get("knowledge_gaps", []) or []:
                if not isinstance(gap, Mapping):
                    continue
                affected = {str(item) for item in gap.get("affected_route_keys", []) or []}
                if affected and not ({evaluated.key, business_id} & affected):
                    continue
                key = str(gap.get("key", ""))
                if not key or not missing:
                    continue
                actions[key] = ActionView(
                    key=key,
                    title=str(gap.get("description", key)),
                    description=str(gap.get("acquisition_action", "Evidence action required.")),
                    route_keys=(evaluated.key,),
                    requirement_keys=tuple(sorted(missing)),
                    priority=str(gap.get("priority", "MEDIUM")),
                    acquisition_cost_class=str(gap.get("acquisition_cost_class", "UNKNOWN")),
                    source_references=evaluated.source_references,
                )
            for question in card.get("guided_questions", []) or []:
                if not isinstance(question, Mapping):
                    continue
                req_keys = tuple(str(item) for item in question.get("requirement_keys", []) or [])
                relevant = tuple(item for item in req_keys if item in missing)
                if not relevant:
                    continue
                key = str(question.get("key", ""))
                actions.setdefault(
                    key,
                    ActionView(
                        key=key,
                        title=str(question.get("prompt", key)),
                        description="Answer this governed question and retain the stated evidence label.",
                        route_keys=(evaluated.key,),
                        requirement_keys=relevant,
                        priority="HIGH",
                        acquisition_cost_class=str(
                            question.get("acquisition_cost_class", "UNKNOWN")
                        ),
                        source_references=evaluated.source_references,
                    ),
                )
        priority = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
        return tuple(
            sorted(actions.values(), key=lambda item: (-priority.get(item.priority, 0), item.key))
        )

    def _invariant_actions(
        self,
        actions: tuple[ActionView, ...],
        routes: tuple[RouteEvaluation, ...],
        invariant_blocks: tuple[str, ...],
    ) -> tuple[ActionView, ...]:
        """Expose blocked safety/coverage gates as next actions without inventing claims."""
        by_key = {item.key: item for item in actions}
        route_keys = tuple(route.key for route in routes)
        if any(block.startswith("R10_") for block in invariant_blocks):
            by_key.setdefault(
                "screen-contamination",
                ActionView(
                    key="screen-contamination",
                    title="Screen contamination and condition",
                    description=(
                        "Obtain screened evidence for contamination, attachments, liquids, and condition; "
                        "a user assertion is not clearance."
                    ),
                    route_keys=route_keys,
                    requirement_keys=("contamination",),
                    priority="CRITICAL",
                    acquisition_cost_class="UNKNOWN",
                    source_references=(),
                ),
            )
        if "R6_JURISDICTION_NOT_COVERED" in invariant_blocks:
            by_key.setdefault(
                "confirm-jurisdiction",
                ActionView(
                    key="confirm-jurisdiction",
                    title="Confirm a covered jurisdiction",
                    description="Provide a supported geography or obtain jurisdiction-specific reviewed coverage.",
                    route_keys=route_keys,
                    requirement_keys=("geography",),
                    priority="CRITICAL",
                    acquisition_cost_class="UNKNOWN",
                    source_references=(),
                ),
            )
        priority = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
        return tuple(
            sorted(by_key.values(), key=lambda item: (-priority.get(item.priority, 0), item.key))
        )

    def _value_blockers(
        self, routes: tuple[RouteEvaluation, ...], invariant_blocks: tuple[str, ...]
    ) -> tuple[str, ...]:
        del routes
        return tuple(invariant_blocks) + (
            "PHASE_A_VALUE_PIPELINE_NOT_IMPLEMENTED: no economics or market-data pipeline is active.",
            "INCOMPLETE_ECONOMIC_BASIS: no imported route has a complete cost and performance basis.",
            "UNKNOWN_COSTS_AND_YIELDS: the vetted packs deliberately contain no source-backed numeric cost or yield estimates.",
            "VALUE_BLOCKED: unknown is not converted into zero, an assumption, or a financial figure.",
        )
