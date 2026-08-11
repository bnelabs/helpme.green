from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from .model_gateway import ModelRouter, ProviderUnavailable

_ABSOLUTE_PATTERNS = (
    r"\bwill destroy\b",
    r"\bdestroys\b",
    r"\balways\b",
    r"\bnever\b",
    r"\bunrecyclable\b",
    r"\blegally non-compliant\b",
    r"\bis illegal\b",
    r"\bguaranteed\b",
)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+./-]*", re.IGNORECASE)


@dataclass(frozen=True)
class QualityReport:
    accepted: bool
    score: int
    flags: tuple[str, ...]
    calibrated_reply: str
    critic_scores: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "score": self.score,
            "flags": list(self.flags),
            "critic_scores": list(self.critic_scores),
        }


class AnswerQualityGate:
    """Provider-neutral answer guard with optional independent model critics.

    Critics may flag a draft, but they never write knowledge or replace the main answer. The local
    checks remain active when no critic model is available.
    """

    def __init__(self, *, router: ModelRouter | None = None) -> None:
        self.router = router

    def assess(
        self,
        *,
        user_message: str,
        reply: str,
        skill_id: str,
        focused_context: str,
        next_step: str = "",
    ) -> QualityReport:
        del skill_id
        text = reply.strip()
        lowered = text.casefold()
        flags: set[str] = set()
        user_tokens = {item.casefold() for item in _TOKEN_RE.findall(user_message)}
        reply_tokens = {item.casefold() for item in _TOKEN_RE.findall(text)}
        if any(re.search(pattern, lowered) for pattern in _ABSOLUTE_PATTERNS):
            flags.add("absolute_claim")
        if text.count("?") > 1:
            flags.add("too_many_questions")
        if (
            "according to" in lowered or "source:" in lowered or "http" in lowered
        ) and not focused_context.strip():
            flags.add("unlinked_source_language")
        if len(text.split()) > 180 and len(user_tokens.intersection(reply_tokens)) < 2:
            flags.add("generic_encyclopedia")
        if len(user_message.split()) >= 8 and len(text.split()) >= 35 and not next_step.strip():
            if not any(
                marker in lowered
                for marker in ("next", "check", "test", "ask", "find out", "before")
            ):
                flags.add("missing_next_step")

        calibrated = self._calibrate(text)
        score = max(1, 5 - len(flags))
        critic_scores: tuple[int, ...] = ()
        if (
            self.router is not None
            and self._env_flag("HELPME_AI_ENABLED", default=False)
            and self._env_flag("HELPME_QUALITY_JUDGES", default=False)
        ):
            critic_scores, critic_flags = self._run_critics(
                user_message=user_message,
                reply=calibrated,
                focused_context=focused_context,
            )
            flags.update(critic_flags)
            score = max(1, min(5, round((score + sum(critic_scores)) / (1 + len(critic_scores)))))
        critical = {"absolute_claim", "unlinked_source_language", "generic_encyclopedia"}
        accepted = not bool(flags.intersection(critical)) and score >= 3
        return QualityReport(accepted, score, tuple(sorted(flags)), calibrated, critic_scores)

    @staticmethod
    def _calibrate(reply: str) -> str:
        replacements = (
            (r"\bwill destroy\b", "could damage"),
            (r"\bdestroys\b", "can damage"),
            (r"\bunrecyclable\b", "not usually suitable for a standard recycling route"),
            (r"\blegally non-compliant\b", "may require a jurisdiction-specific compliance review"),
            (r"\bis illegal\b", "may be restricted"),
            (r"\bguaranteed\b", "supported only when the stated conditions are met"),
        )
        result = reply
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _run_critics(
        self,
        *,
        user_message: str,
        reply: str,
        focused_context: str,
    ) -> tuple[tuple[int, ...], set[str]]:
        router = self.router
        if router is None:
            return (), {"critics_unavailable"}
        contracts = (
            (
                "factuality",
                "Judge only factual calibration and whether the reply stays within the supplied context.",
            ),
            (
                "usefulness",
                "Judge whether the reply addresses the user's actual situation and offers a concrete next step without sounding encyclopedic.",
            ),
        )

        def run(item: tuple[str, str]) -> tuple[int, set[str]]:
            role, mission = item
            prompt = (
                "You are an independent answer critic. You do not rewrite the answer, make a decision, "
                "or write knowledge. Return JSON with score (0-5), flags (array of short strings), "
                "and reason (short string). "
                + mission
                + "\nUser message:\n"
                + user_message[:3000]
                + "\nDraft reply:\n"
                + reply[:6000]
                + "\nFocused context:\n"
                + focused_context[:5000]
            )
            try:
                result = router.complete_json(
                    [{"role": "user", "content": prompt}],
                    system_contract=(
                        "Return only the requested critic JSON. Never invent a source and never "
                        "include internal application fields."
                    ),
                    max_tokens=300,
                )
            except (ProviderUnavailable, ValueError, TypeError):
                return 0, {f"{role}_unavailable"}
            raw_score = result.get("score")
            if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float, str)):
                return 0, {f"{role}_invalid"}
            try:
                score = max(0, min(5, int(raw_score)))
            except (TypeError, ValueError):
                return 0, {f"{role}_invalid"}
            raw_flags = result.get("flags", [])
            flags = {f"{role}_concern"} if score < 3 else set()
            if isinstance(raw_flags, list):
                flags.update(f"{role}:{str(item)[:60]}" for item in raw_flags[:3])
            return score, flags

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(run, contracts))
        scores = tuple(score for score, _flags in results if score > 0)
        flags: set[str] = set()
        for _score, item_flags in results:
            flags.update(item_flags)
        return scores, flags

    @staticmethod
    def _env_flag(name: str, *, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().casefold() not in {"", "0", "false", "no", "off"}
