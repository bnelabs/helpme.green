from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

Message = dict[str, str]


class ContextCompactionError(RuntimeError):
    """The request cannot be reduced safely to the configured context ceiling."""


@dataclass(frozen=True)
class CompactionPass:
    messages: tuple[Message, ...]
    before_tokens: int
    after_tokens: int
    source_messages: int
    summary: str
    state_hash: str


def estimate_request_tokens(system_contract: str, messages: Sequence[Mapping[str, str]]) -> int:
    """Conservatively estimate a request when a provider tokenizer is unavailable."""
    characters = len(system_contract)
    for item in messages:
        characters += len(str(item.get("role", ""))) + len(str(item.get("content", ""))) + 8
    return max(1, math.ceil(characters / 4) + 4 * max(1, len(messages)))


def compact_until_fit(
    messages: Sequence[Mapping[str, str]],
    current_message: str,
    *,
    system_contract: str,
    ceiling: int,
    understanding: Mapping[str, str] | None = None,
    measure: Callable[[str, Sequence[Mapping[str, str]]], int] = estimate_request_tokens,
    minimum_tail_messages: int = 4,
    force_one_pass: bool = False,
) -> tuple[list[Message], tuple[CompactionPass, ...]]:
    """Compact only the derived working context until it fits the hard ceiling.

    The original session events are retained by the caller. This function never caps the
    number of passes; it stops only on fit or an explicit no-safe-progress condition.
    """
    if ceiling <= 0:
        raise ContextCompactionError("Model context ceiling must be positive.")
    if minimum_tail_messages < 2:
        raise ContextCompactionError("Compaction must preserve at least two recent messages.")

    working: list[Message] = [
        {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
        for item in messages
    ]
    current = {"role": "user", "content": current_message}
    passes: list[CompactionPass] = []
    seen: set[str] = set()
    forced = force_one_pass

    while True:
        before = measure(system_contract, [*working, current])
        if before <= ceiling and not forced:
            return working, tuple(passes)
        forced = False
        state_hash = _state_hash(working, current)
        if state_hash in seen:
            raise ContextCompactionError("Compaction repeated the same working-context state.")
        seen.add(state_hash)

        max_end = len(working) - max(2, minimum_tail_messages)
        max_end -= max_end % 2
        if max_end < 2:
            raise ContextCompactionError(
                "The request exceeds the context ceiling before a safe history range is available."
            )

        options: list[tuple[int, int, list[Message], str]] = []
        for end in range(2, max_end + 1, 2):
            source = working[:end]
            # Reserve room for the trusted contract and the preserved recent tail on small
            # context windows; large models still receive the fuller summary.
            summary = _summarize(
                source,
                understanding or {},
                max_chars=max(240, min(720, ceiling // 3)),
            )
            candidate = [{"role": "assistant", "content": summary}, *working[end:]]
            after = measure(system_contract, [*candidate, current])
            if after < before:
                options.append((end, after, candidate, summary))

        if not options:
            raise ContextCompactionError("No compaction candidate makes measurable progress.")

        fitting = [option for option in options if option[1] <= ceiling]
        end, after, candidate, summary = fitting[0] if fitting else options[0]
        passes.append(
            CompactionPass(
                messages=tuple(candidate),
                before_tokens=before,
                after_tokens=after,
                source_messages=end,
                summary=summary,
                state_hash=state_hash,
            )
        )
        working = candidate


def _state_hash(messages: Sequence[Mapping[str, str]], current: Mapping[str, str]) -> str:
    body = json.dumps(
        {"messages": list(messages), "current": dict(current)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _summarize(
    messages: Sequence[Mapping[str, str]],
    understanding: Mapping[str, str],
    *,
    max_chars: int,
) -> str:
    lines = ["Earlier conversation (abridged; original turns remain in local session history):"]
    facts = [
        f"{key}: {value.strip()}"
        for key, value in sorted(understanding.items())
        if isinstance(value, str) and value.strip()
    ]
    if facts:
        lines.append("Previously recorded understanding (not new evidence): " + "; ".join(facts))
    for item in messages:
        role = item.get("role", "message")
        content = _clip(item.get("content", ""), 240)
        if content:
            lines.append(f"{role}: {content}")
    result = "\n".join(lines)
    return _clip(result, max_chars)


def _clip(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    left = max(1, (limit - 5) // 2)
    right = max(1, limit - left - 5)
    return f"{cleaned[:left].rstrip()} … {cleaned[-right:].lstrip()}"
