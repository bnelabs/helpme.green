#!/usr/bin/env python3
"""Extract and smoke-test a native helpme.green bundle without calling a model."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def _extract(archive: Path, destination: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            destination_root = destination.resolve()
            for member in source.infolist():
                member_path = (destination / member.filename).resolve()
                if not member_path.is_relative_to(destination_root):
                    raise ValueError(f"Refusing archive path traversal: {member.filename}")
            source.extractall(destination)
        return
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as source:
            destination_root = destination.resolve()
            for member in source.getmembers():
                member_path = (destination / member.name).resolve()
                if not member_path.is_relative_to(destination_root):
                    raise ValueError(f"Refusing archive path traversal: {member.name}")
                if member.issym() or member.islnk():
                    link_path = (Path(member.name).parent / member.linkname).as_posix()
                    link_target = (destination / link_path).resolve()
                    if not link_target.is_relative_to(destination_root):
                        raise ValueError(f"Refusing archive link: {member.name}")
            if sys.version_info >= (3, 12):
                source.extractall(destination, filter="data")
            else:
                source.extractall(destination)
        return
    raise ValueError(f"Unsupported native archive: {archive}")


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _executable(root: Path) -> Path:
    names = {"helpme-green.exe", "helpme-green"}
    candidates = [path for path in root.rglob("helpme-green*") if path.is_file()]
    for candidate in candidates:
        if candidate.name in names:
            if os.name != "nt":
                candidate.chmod(candidate.stat().st_mode | 0o111)
            return candidate
    raise FileNotFoundError(f"Could not find helpme-green executable under {root}")


def verify_bundle(
    archive: Path, *, version: str = "", target: str = "", timeout: float = 60
) -> dict[str, object]:
    """Verify metadata and the health endpoint of an extracted native archive."""
    with tempfile.TemporaryDirectory(prefix="helpme-green-native-check-") as temporary:
        extraction_root = Path(temporary)
        _extract(archive, extraction_root)
        metadata_paths = list(extraction_root.rglob("RELEASE-METADATA.json"))
        if len(metadata_paths) != 1:
            raise RuntimeError(f"Expected one RELEASE-METADATA.json, found {len(metadata_paths)}")
        metadata = json.loads(metadata_paths[0].read_text(encoding="utf-8"))
        if version and metadata.get("version") != version:
            raise RuntimeError(
                f"Bundle version is {metadata.get('version')!r}, expected {version!r}"
            )
        if target and metadata.get("target") != target:
            raise RuntimeError(f"Bundle target is {metadata.get('target')!r}, expected {target!r}")
        executable = _executable(extraction_root)
        port = _available_port()
        environment = os.environ.copy()
        environment["HELPME_AI_ENABLED"] = "0"
        environment["HELPME_DATA_DIR"] = str(extraction_root / "runtime-data")
        process = subprocess.Popen(
            [str(executable), "--serve", "--host", "127.0.0.1", "--port", str(port)],
            cwd=executable.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        health: dict[str, object] | None = None
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    raise RuntimeError(f"Native bundle exited before health check:\n{output}")
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/healthz", timeout=2
                    ) as response:
                        health = json.loads(response.read().decode("utf-8"))
                    break
                except (OSError, urllib.error.URLError, json.JSONDecodeError):
                    time.sleep(0.5)
            if health is None:
                raise TimeoutError("Native bundle health check timed out.")
            if health.get("status") != "ok" or health.get("audit_chain_valid") is not True:
                raise RuntimeError(f"Native bundle health is not clean: {health}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        return {"archive": str(archive), "health": health, "target": metadata.get("target")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--version", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        result = verify_bundle(
            args.archive, version=args.version, target=args.target, timeout=args.timeout
        )
    except (
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
        zipfile.BadZipFile,
        tarfile.TarError,
    ) as exc:
        print(f"native bundle verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
