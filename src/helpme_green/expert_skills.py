from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SkillConfigurationError(ValueError):
    """Raised when an expert skill pack is incomplete or unsafe to load."""


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+./-]*", re.IGNORECASE)


def _strings(value: Any, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise SkillConfigurationError(f"Skill field {field!r} must be a list.")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _tokens(value: str) -> set[str]:
    return {item.casefold() for item in _TOKEN_RE.findall(value)}


@dataclass(frozen=True)
class ExpertSkill:
    skill_id: str
    title: str
    material_families: tuple[str, ...]
    triggers: tuple[str, ...]
    concepts: tuple[str, ...]
    tests: tuple[str, ...]
    confirm_before_advising: tuple[str, ...]
    avoid_overclaims: tuple[str, ...]
    followups: tuple[str, ...]
    next_step: str
    source_domains: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ExpertSkill:
        required = ("id", "title", "material_families", "concepts", "tests")
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise SkillConfigurationError(
                "Expert skill is missing required fields: " + ", ".join(missing)
            )
        return cls(
            skill_id=str(raw["id"]),
            title=str(raw["title"]),
            material_families=_strings(raw.get("material_families"), field="material_families"),
            triggers=_strings(raw.get("triggers"), field="triggers"),
            concepts=_strings(raw.get("concepts"), field="concepts"),
            tests=_strings(raw.get("tests"), field="tests"),
            confirm_before_advising=_strings(
                raw.get("confirm_before_advising"), field="confirm_before_advising"
            ),
            avoid_overclaims=_strings(raw.get("avoid_overclaims"), field="avoid_overclaims"),
            followups=_strings(raw.get("followups"), field="followups"),
            next_step=str(
                raw.get("next_step", "Clarify the smallest missing fact that changes the route.")
            ),
            source_domains=_strings(raw.get("source_domains"), field="source_domains"),
        )

    def prompt_context(self) -> str:
        return "\n".join(
            (
                f"Expert lens: {self.title} ({self.skill_id}).",
                "Use these concepts when they change the user's next decision: "
                + "; ".join(self.concepts),
                "Useful tests or observations to consider: " + "; ".join(self.tests),
                "Confirm these before giving specific advice: "
                + "; ".join(self.confirm_before_advising or ("route suitability",)),
                "Avoid these overstatements: "
                + "; ".join(self.avoid_overclaims or ("absolute outcomes",)),
                "Highest-value follow-ups, if one is genuinely needed: "
                + "; ".join(self.followups or ("what would change the next route",)),
                "Useful next step: " + self.next_step,
                "Treat this as an internal reasoning lens. Do not show the list or its labels to the user.",
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.skill_id,
            "title": self.title,
            "material_families": list(self.material_families),
            "source_domains": list(self.source_domains),
        }


@dataclass(frozen=True)
class SkillSelection:
    primary: ExpertSkill
    supporting: tuple[ExpertSkill, ...] = ()

    @property
    def ids(self) -> tuple[str, ...]:
        return (self.primary.skill_id, *(item.skill_id for item in self.supporting))

    @property
    def prompt_context(self) -> str:
        sections = [self.primary.prompt_context()]
        sections.extend(item.prompt_context() for item in self.supporting)
        return "\n\n".join(sections)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary.to_dict(),
            "supporting": [item.to_dict() for item in self.supporting],
        }


class SkillRegistry:
    """Loadable, provider-neutral expert lenses used to focus model context."""

    def __init__(self, skills: Iterable[ExpertSkill]):
        values = tuple(skills)
        if not values:
            raise SkillConfigurationError("At least one expert skill is required.")
        by_id: dict[str, ExpertSkill] = {}
        for skill in values:
            if skill.skill_id in by_id:
                raise SkillConfigurationError(f"Duplicate expert skill: {skill.skill_id}")
            by_id[skill.skill_id] = skill
        self._skills = by_id

    @classmethod
    def from_repository(cls, root: Path) -> SkillRegistry:
        directory = root / "skills"
        skill_documents: list[Mapping[str, Any]] = []
        if directory.is_dir():
            for path in sorted(directory.glob("*.y*ml")):
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(raw, Mapping):
                    raise SkillConfigurationError(f"Skill document is not an object: {path}")
                if isinstance(raw.get("skills"), list):
                    skill_documents.extend(
                        item for item in raw["skills"] if isinstance(item, Mapping)
                    )
        return cls(ExpertSkill.from_mapping(item) for item in skill_documents)

    def get(self, skill_id: str) -> ExpertSkill:
        return self._skills[skill_id]

    def select(self, message: str, topic_hint: str = "") -> SkillSelection:
        query = f"{topic_hint} {message}".strip().casefold()
        query_tokens = _tokens(query)
        scored: list[tuple[int, int, ExpertSkill]] = []
        for order, skill in enumerate(self._skills.values()):
            score = 0
            for trigger in skill.triggers:
                trigger_text = trigger.casefold()
                if trigger_text in query:
                    score += 4 if " " in trigger_text else 2
                score += len(query_tokens.intersection(_tokens(trigger)))
            for family in skill.material_families:
                if family.casefold() in query:
                    score += 3
            scored.append((score, -order, skill))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        primary = scored[0][2]
        if scored[0][0] <= 0:
            primary = self._skills.get("general-conversation", primary)
        supporting = tuple(
            skill
            for score, _order, skill in scored[1:]
            if score >= 4 and skill.skill_id != primary.skill_id
        )[:2]
        return SkillSelection(primary=primary, supporting=supporting)

    def public_catalog(self) -> list[dict[str, Any]]:
        return [skill.to_dict() for skill in self._skills.values()]
