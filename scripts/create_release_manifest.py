#!/usr/bin/env python3
"""Create a checksum-bearing manifest for a prepared release asset directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def create_manifest(
    *,
    version: str,
    tag: str,
    asset_dir: Path,
    output: Path,
    commit: str = "",
    container_image: str = "",
    container_digest: str = "",
) -> dict[str, object]:
    assets = []
    for path in sorted(asset_dir.iterdir()):
        if not path.is_file() or path.name.endswith(".sha256"):
            continue
        assets.append(
            {
                "name": path.name,
                "sizeBytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest: dict[str, object] = {
        "manifestVersion": 1,
        "name": "helpme.green",
        "version": version,
        "tag": tag,
        "commit": commit or current_commit(),
        "assets": assets,
        "container": {
            "image": container_image,
            "digest": container_digest,
        },
        "knowledgeArtifact": {
            "status": "pending-redistribution-review",
            "bundled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--asset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="")
    parser.add_argument("--container-image", default="")
    parser.add_argument("--container-digest", default="")
    args = parser.parse_args(argv)
    create_manifest(
        version=args.version,
        tag=args.tag,
        asset_dir=args.asset_dir,
        output=args.output,
        commit=args.commit,
        container_image=args.container_image,
        container_digest=args.container_digest,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
