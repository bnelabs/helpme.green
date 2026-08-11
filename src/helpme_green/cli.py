from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from .console import CommandProcessor
from .knowledge import KnowledgeBase
from .mcp import ReadOnlyMCP
from .persistence import SecretStore, SessionState, SessionStore
from .server import serve


def _repository_root() -> Path:
    candidates = (
        Path(os.environ.get("HELPME_ROOT", Path.cwd())).resolve(),
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[3],
    )
    for candidate in candidates:
        if (candidate / "vendor/reference/knowledge-manifest.json").exists():
            return candidate
    raise FileNotFoundError("Cannot locate the helpme.green knowledge manifest.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="helpme.green advisory Pro Console")
    parser.add_argument(
        "--serve", action="store_true", help="serve the terminal-like console over HTTP"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--material", default="copper cable")
    parser.add_argument("--geography", default="Bulgaria / EU")
    parser.add_argument("--session-id", default=None, help="resume an existing session")
    parser.add_argument(
        "--mcp-root",
        action="append",
        type=Path,
        default=[],
        help="additional read-only local root for /load; may be repeated",
    )
    parser.add_argument(
        "--mcp-host",
        action="append",
        default=[],
        help="explicit HTTPS host allowed for /load; may be repeated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = _repository_root()
    knowledge = KnowledgeBase.from_repository(root)
    data_dir = args.data_dir or Path(os.environ.get("HELPME_DATA_DIR", root / ".data"))
    store = SessionStore(data_dir, knowledge_digest=knowledge.digest)
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
    processor = CommandProcessor(knowledge, store, mcp=mcp, secret_store=secret_store)
    if args.serve:
        serve(processor, store, host=args.host, port=args.port)
        return 0
    if args.session_id:
        session = store.load_session(args.session_id)
    else:
        session = SessionState.new(material=args.material, geography=args.geography)
        store.save_session(session)
    print("helpme.green Pro Console — DECISION TIER — ADVISORY ONLY")
    print(f"Session: {session.session_id}. Type /help for commands.")
    while not session.exited:
        try:
            command = input("helpme.green> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if (
            command.strip().startswith("/key ")
            and len(command.split()) == 2
            and secret_store is not None
        ):
            name = command.split(maxsplit=1)[1].strip()
            secret = getpass.getpass("Secret (hidden; never logged): ")
            response = processor.set_key(session, name, secret)
        else:
            response = processor.execute(session, command)
        print(response.text)
        if response.error:
            print(f"ERROR: {response.error}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
