from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

from .application import ApplicationProcessor
from .knowledge import KnowledgeBase
from .mcp import ReadOnlyMCP
from .persistence import SecretStore, SessionStore
from .server import serve


def _repository_root() -> Path:
    candidates = (
        Path(os.environ.get("HELPME_ROOT", Path.cwd())).resolve(),
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[3],
    )
    for candidate in candidates:
        if (candidate / "knowledge/source-manifest.yml").exists():
            return candidate
    raise FileNotFoundError("Cannot locate the helpme.green source manifest.")


def _empty_session_retention_days() -> float:
    raw = os.environ.get("HELPME_EMPTY_SESSION_TTL_DAYS", "7")
    try:
        days = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("HELPME_EMPTY_SESSION_TTL_DAYS must be positive.") from exc
    if not math.isfinite(days) or days <= 0:
        raise ValueError("HELPME_EMPTY_SESSION_TTL_DAYS must be positive.")
    return days


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="helpme.green local circular-economy assistant")
    parser.add_argument("--serve", action="store_true", help="serve the local web assistant")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument(
        "--mcp-root",
        action="append",
        type=Path,
        default=[],
        help="additional read-only local root for supported imports; may be repeated",
    )
    parser.add_argument(
        "--mcp-host",
        action="append",
        default=[],
        help="explicit HTTPS host allowed for supported imports; may be repeated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.serve:
        print("Run helpme-green --serve to start the local web assistant.")
        return 0

    root = _repository_root()
    knowledge = KnowledgeBase.from_repository(root)
    data_dir = args.data_dir or Path(os.environ.get("HELPME_DATA_DIR", root / ".data"))
    configured_roots = [root, data_dir, *args.mcp_root]
    configured_roots.extend(
        Path(item) for item in os.environ.get("HELPME_MCP_ROOTS", "").split(os.pathsep) if item
    )
    configured_hosts = list(args.mcp_host)
    configured_hosts.extend(
        item.strip() for item in os.environ.get("HELPME_MCP_HOSTS", "").split(",") if item.strip()
    )
    mcp = ReadOnlyMCP(
        file_roots=tuple(configured_roots),
        allowed_url_hosts=tuple(configured_hosts),
    )
    secret_store = None
    if os.environ.get("HELPME_MASTER_KEY"):
        secret_store = SecretStore(data_dir / "secrets")
    store = SessionStore(data_dir, knowledge_digest=knowledge.digest)
    store.prune_empty_sessions(max_age_seconds=_empty_session_retention_days() * 24 * 60 * 60)
    store.prune_snapshots()
    processor = ApplicationProcessor(knowledge, store, mcp=mcp, secret_store=secret_store)
    serve(processor, store, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
