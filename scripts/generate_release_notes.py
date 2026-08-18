#!/usr/bin/env python3
"""Render a deterministic GitHub release note from the checked-in changelog."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def changelog_section(version: str, changelog: Path = CHANGELOG) -> str:
    """Extract the section whose heading starts with the requested version."""
    lines = changelog.read_text(encoding="utf-8").splitlines()
    start: int | None = None
    lookup_versions = [version]
    if "-" in version:
        lookup_versions.append(version.split("-", 1)[0])
    for lookup_version in lookup_versions:
        heading = re.compile(rf"^## \[{re.escape(lookup_version)}\](?:\s|$)")
        for index, line in enumerate(lines):
            if heading.match(line):
                start = index
                break
        if start is not None:
            break
    if start is None:
        raise ValueError(f"No changelog section exists for {version}.")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    section = "\n".join(lines[start:end]).strip()
    if not section:
        raise ValueError(f"Changelog section for {version} is empty.")
    return section


def current_commit() -> str:
    """Return the exact checked-out commit, or a deterministic CI fallback."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def render(
    version: str,
    *,
    tag: str,
    commit: str | None = None,
    container_image: str = "",
    container_digest: str = "",
) -> str:
    """Render release metadata and the matching changelog section."""
    exact_commit = commit or current_commit()
    container_line = (
        f"- Container: `{container_image}@{container_digest}`.\n"
        if container_image and container_digest
        else "- Container: inspect the published GHCR image digest before deployment.\n"
    )
    return (
        f"# helpme.green v{version}\n\n"
        f"- Tag: `{tag}`\n"
        f"- Exact commit: `{exact_commit}`\n"
        "- Native assets: inspect `SHA256SUMS`; attached provenance attestations are included when the repository supports them.\n"
        + container_line
        + "\n"
        f"{changelog_section(version)}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--tag", default="")
    parser.add_argument("--commit", default="")
    parser.add_argument("--container-image", default="")
    parser.add_argument("--container-digest", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    tag = args.tag or f"v{args.version}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render(
            args.version,
            tag=tag,
            commit=args.commit or None,
            container_image=args.container_image,
            container_digest=args.container_digest,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
