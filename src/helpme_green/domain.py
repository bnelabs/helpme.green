from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EvidenceState(StrEnum):
    """Evidence ladder used by the deterministic evaluator."""

    UNKNOWN = "UNKNOWN"
    HEARSAY = "HEARSAY"
    EDUCATED_ESTIMATE = "EDUCATED_ESTIMATE"
    OBSERVED = "OBSERVED"
    SCREENED = "SCREENED"
    VERIFIED = "VERIFIED"

    @property
    def rank(self) -> int:
        return {
            EvidenceState.UNKNOWN: -1,
            EvidenceState.HEARSAY: 0,
            EvidenceState.EDUCATED_ESTIMATE: 1,
            EvidenceState.OBSERVED: 2,
            EvidenceState.SCREENED: 3,
            EvidenceState.VERIFIED: 4,
        }[self]

    @classmethod
    def from_pack_level(cls, value: str | None) -> EvidenceState:
        if value is None:
            return cls.UNKNOWN
        level = str(value).upper()
        if level.startswith("E") and level[1:].isdigit():
            return {
                "E0": cls.HEARSAY,
                "E1": cls.EDUCATED_ESTIMATE,
                "E2": cls.OBSERVED,
                "E3": cls.SCREENED,
                "E4": cls.VERIFIED,
            }.get(level, cls.UNKNOWN)
        try:
            return cls[level]
        except KeyError:
            return cls.UNKNOWN


class ConfirmationLabel(StrEnum):
    """The only labels the Intake boundary may assign to user answers."""

    DECLARED = "declared"
    ESTIMATE = "estimate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Provenance:
    kind: str
    source_ids: tuple[str, ...] = ()
    source_locations: tuple[str, ...] = ()
    note: str = ""
    untrusted: bool = False
    reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source_ids": list(self.source_ids),
            "source_locations": list(self.source_locations),
            "note": self.note,
            "untrusted": self.untrusted,
            "reference": self.reference,
        }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


@dataclass(frozen=True)
class CaseFact:
    """A fact entering the evaluator with explicit epistemic status."""

    key: str
    value: Any
    label: ConfirmationLabel
    evidence_state: EvidenceState
    provenance: Provenance
    conflict_note: str = ""

    @property
    def is_unknown(self) -> bool:
        return self.label is ConfirmationLabel.UNKNOWN or self.value is None

    @classmethod
    def user(
        cls,
        key: str,
        value: Any,
        label: str | ConfirmationLabel,
        *,
        note: str = "",
        untrusted: bool = False,
        reference: str = "",
    ) -> CaseFact:
        try:
            resolved = (
                label if isinstance(label, ConfirmationLabel) else ConfirmationLabel(label.lower())
            )
        except (AttributeError, ValueError) as exc:
            raise ValueError(
                "Intake facts must be labelled declared, estimate, or unknown."
            ) from exc
        if resolved is ConfirmationLabel.UNKNOWN:
            return cls(
                key=key,
                value=None,
                label=resolved,
                evidence_state=EvidenceState.UNKNOWN,
                provenance=Provenance(
                    kind="mcp" if untrusted else "user",
                    note=note,
                    untrusted=untrusted,
                    reference=reference,
                ),
            )
        evidence = (
            EvidenceState.HEARSAY
            if resolved is ConfirmationLabel.DECLARED
            else EvidenceState.EDUCATED_ESTIMATE
        )
        return cls(
            key=key,
            value=value,
            label=resolved,
            evidence_state=evidence,
            provenance=Provenance(
                kind="mcp" if untrusted else "user",
                note=note,
                untrusted=untrusted,
                reference=reference,
            ),
        )

    @classmethod
    def reviewed(
        cls,
        key: str,
        value: Any,
        evidence_state: EvidenceState,
        *,
        source_ids: Collection[str],
        source_registry: Collection[str] | None = None,
        source_locations: Collection[str] = (),
        note: str = "",
    ) -> CaseFact:
        if evidence_state.rank < EvidenceState.OBSERVED.rank:
            raise ValueError("Reviewed facts must be observed, screened, or verified.")
        ids = tuple(str(item) for item in source_ids)
        if not ids:
            raise ValueError("Reviewed facts require at least one registered source ID.")
        if source_registry is not None:
            missing = sorted(set(ids).difference(source_registry))
            if missing:
                raise ValueError(
                    f"Reviewed fact references unregistered source(s): {', '.join(missing)}"
                )
        return cls(
            key=key,
            value=value,
            label=ConfirmationLabel.DECLARED,
            evidence_state=evidence_state,
            provenance=Provenance(
                kind="qualified-review",
                source_ids=ids,
                source_locations=tuple(str(item) for item in source_locations),
                note=note,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": _json_safe(self.value),
            "label": self.label.value,
            "evidence_state": self.evidence_state.value,
            "provenance": self.provenance.to_dict(),
            "conflict_note": self.conflict_note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CaseFact:
        provenance_data = data.get("provenance", {})
        if not isinstance(provenance_data, Mapping):
            raise ValueError("Fact provenance must be an object.")
        label = ConfirmationLabel(str(data.get("label", "unknown")))
        evidence_state = EvidenceState(str(data.get("evidence_state", "UNKNOWN")))
        kind = str(provenance_data.get("kind", "user"))
        untrusted = bool(provenance_data.get("untrusted", False))
        if kind in {"user", "mcp"}:
            expected = {
                ConfirmationLabel.DECLARED: EvidenceState.HEARSAY,
                ConfirmationLabel.ESTIMATE: EvidenceState.EDUCATED_ESTIMATE,
                ConfirmationLabel.UNKNOWN: EvidenceState.UNKNOWN,
            }[label]
            if evidence_state is not expected:
                raise ValueError("User or MCP provenance cannot upgrade its evidence state.")
        if evidence_state.rank >= EvidenceState.OBSERVED.rank and kind != "qualified-review":
            raise ValueError("Elevated evidence state requires qualified-review provenance.")
        if untrusted and evidence_state.rank >= EvidenceState.OBSERVED.rank:
            raise ValueError("Untrusted provenance cannot carry an elevated evidence state.")
        source_ids = tuple(str(item) for item in provenance_data.get("source_ids", []))
        if evidence_state.rank >= EvidenceState.OBSERVED.rank and not source_ids:
            raise ValueError("Elevated evidence state requires source IDs.")
        return cls(
            key=str(data["key"]),
            value=data.get("value"),
            label=label,
            evidence_state=evidence_state,
            provenance=Provenance(
                kind=kind,
                source_ids=source_ids,
                source_locations=tuple(
                    str(item) for item in provenance_data.get("source_locations", [])
                ),
                note=str(provenance_data.get("note", "")),
                untrusted=untrusted,
                reference=str(provenance_data.get("reference", "")),
            ),
            conflict_note=str(data.get("conflict_note", "")),
        )


def canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
