from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .application import ApplicationProcessor
from .config import RuntimePaths, environment_secret
from .knowledge import KnowledgeBase
from .mcp import ReadOnlyMCP
from .persistence import SecretStore, SessionStore
from .server import serve


def _repository_root(paths: RuntimePaths | None = None) -> Path:
    configured_root = (paths or RuntimePaths.from_environment()).root
    candidates: list[Path] = []
    if configured_root:
        candidates.append(configured_root.resolve())
    else:
        candidates.append(Path.cwd().resolve())
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        frozen_path = Path(frozen_root).resolve()
        candidates.extend((frozen_path, frozen_path.parent))
    candidates.extend((Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[3]))
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "knowledge/source-manifest.yml").exists():
            return candidate
    raise FileNotFoundError("Cannot locate the helpme.green source manifest.")


def _default_data_dir(root: Path, paths: RuntimePaths | None = None) -> Path:
    """Choose a writable native data directory without changing repository/Docker defaults."""
    configured = (paths or RuntimePaths.from_environment()).data_dir
    if configured:
        return configured
    if not getattr(sys, "frozen", False):
        return root / ".data"
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "helpme.green"


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

    paths = RuntimePaths.from_environment()
    root = _repository_root(paths)
    knowledge = KnowledgeBase.from_repository(root)
    data_dir = args.data_dir or _default_data_dir(root, paths)
    configured_roots = [root, data_dir, *args.mcp_root]
    configured_roots.extend(paths.mcp_roots)
    configured_hosts = [*args.mcp_host, *paths.mcp_hosts]
    mcp = ReadOnlyMCP(
        file_roots=tuple(configured_roots),
        allowed_url_hosts=tuple(configured_hosts),
    )
    secret_store = None
    if environment_secret("HELPME_MASTER_KEY"):
        secret_store = SecretStore(data_dir / "secrets")
    store = SessionStore(data_dir, knowledge_digest=knowledge.digest)
    processor = ApplicationProcessor(knowledge, store, mcp=mcp, secret_store=secret_store)
    serve(processor, store, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
