#!/usr/bin/env python3
"""Validate a release tag against the checked-in application version."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "helpme_green" / "__init__.py"
SEMVER_PATTERN = re.compile(
    r"^(?P<core>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def read_source_version(path: Path = VERSION_FILE) -> str:
    """Read and validate the single source-of-truth application version."""
    match = re.search(
        r"^__version__\s*=\s*[\"']([^\"']+)[\"']\s*$",
        path.read_text(),
        flags=re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"Could not find __version__ in {path}.")
    version = match.group(1)
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise ValueError(f"Invalid semantic version {version!r} in {path}.")
    return version


def version_from_tag(tag: str) -> str:
    """Return the SemVer value represented by a v-prefixed Git tag."""
    version = tag[1:] if tag.startswith("v") else tag
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise ValueError(f"Tag {tag!r} is not a valid v-prefixed SemVer tag.")
    return version


def validate_tag(tag: str, source_version: str | None = None) -> str:
    """Validate a tag and return its normalized version."""
    tag_version = version_from_tag(tag)
    expected = source_version or read_source_version()
    if tag_version != expected:
        raise ValueError(f"Release tag {tag!r} does not match source version {expected!r}.")
    return tag_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="the v-prefixed Git tag to validate")
    args = parser.parse_args(argv)
    try:
        version = validate_tag(args.tag)
    except ValueError as exc:
        print(f"release check failed: {exc}", file=sys.stderr)
        return 2
    print(version)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
