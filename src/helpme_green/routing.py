from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote

SessionOperation = Literal["read", "message", "message_stream"]


@dataclass(frozen=True)
class SessionRoute:
    operation: SessionOperation
    session_id: str


def path_parts(path: str) -> tuple[str, ...]:
    """Split and decode path segments without allowing a decoded slash to change routing."""
    return tuple(unquote(item) for item in path.split("/") if item)


def match_session_route(path: str) -> SessionRoute | None:
    parts = path_parts(path)
    if len(parts) == 3 and parts[:2] == ("api", "sessions"):
        return SessionRoute("read", parts[2])
    if len(parts) == 4 and parts[:2] == ("api", "sessions") and parts[3] == "message":
        return SessionRoute("message", parts[2])
    if len(parts) == 5 and parts[:2] == ("api", "sessions") and parts[3:] == ("message", "stream"):
        return SessionRoute("message_stream", parts[2])
    return None
