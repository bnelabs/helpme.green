#!/usr/bin/env python3
"""Build and archive a target-native helpme.green one-directory bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "linux-amd64": "gztar",
    "linux-arm64": "gztar",
    "macos-arm64": "zip",
    "macos-amd64": "zip",
    "windows-amd64": "zip",
    "windows-arm64": "zip",
}
RUNTIME_DATA = (
    ("README.md", "."),
    ("REQUIREMENTS.md", "."),
    ("docs/deployment.md", "docs"),
    ("docs/knowledge-artifact.md", "docs"),
    ("static", "static"),
    ("assets", "assets"),
    ("knowledge", "knowledge"),
    ("skills", "skills"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_stem(version: str, target: str) -> str:
    if target not in TARGETS:
        raise ValueError(f"Unsupported native target {target!r}.")
    if not version or any(character in version for character in "/\\ "):
        raise ValueError(f"Invalid release version {version!r}.")
    return f"helpme-green-{version}-{target}"


def _data_argument(source: Path, destination: str) -> str:
    return f"{source}{os.pathsep}{destination}"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_bundle_metadata(bundle: Path, *, version: str, target: str) -> None:
    release_status = "release-candidate" if "-rc." in version else "stable"
    metadata = {
        "name": "helpme.green",
        "version": version,
        "target": target,
        "commit": _git_commit(),
        "bundleType": "pyinstaller-onedir",
        "releaseStatus": release_status,
        "knowledge": "checked-in metadata only; local runtime database is not bundled",
    }
    (bundle / "RELEASE-METADATA.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    executable = "helpme-green.exe" if target.startswith("windows-") else "./helpme-green"
    release_notice = (
        "This is a release candidate. Automated target smoke checks have passed, but occasional "
        "breakage, rough edges, and behavior changes remain possible before stable publication.\n\n"
        if release_status == "release-candidate"
        else ""
    )
    run_instructions = (
        f"# helpme.green {version}\n\n"
        f"Target: `{target}`\n\n"
        f"{release_notice}"
        "This is a target-native one-directory bundle. It contains the application and checked-in\n"
        "reference metadata, but no model, provider key, encryption key, local database, or raw\n"
        "source download.\n\n"
        "Verify the archive checksum published with the GitHub release before extracting.\n\n"
        "Start the local browser service from this directory:\n\n"
        f"```text\n{executable} --serve --host 127.0.0.1 --port 8080\n```\n\n"
        "Set `HELPME_DATA_DIR` to a writable persistent directory when the bundle is installed in a\n"
        "read-only location. Configure the model/provider endpoint using the documented environment\n"
        "settings; never put credentials in this bundle.\n"
    )
    (bundle / "RUN.md").write_text(
        run_instructions,
        encoding="utf-8",
    )


def package_native(
    *, version: str, target: str, output_dir: Path, root: Path = ROOT
) -> dict[str, str | int]:
    """Build a native bundle and return its archive/checksum metadata."""
    archive_format = TARGETS.get(target)
    if archive_format is None:
        raise ValueError(f"Unsupported native target {target!r}.")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = artifact_stem(version, target)
    archive_path = output_dir / (f"{stem}.zip" if archive_format == "zip" else f"{stem}.tar.gz")
    checksum_path = Path(f"{archive_path}.sha256")
    if archive_path.exists() or checksum_path.exists():
        raise FileExistsError(f"Release output already exists: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="helpme-green-native-") as temporary:
        temporary_root = Path(temporary)
        dist_path = temporary_root / "dist"
        work_path = temporary_root / "build"
        spec_path = temporary_root / "spec"
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onedir",
            "--console",
            "--name",
            "helpme-green",
            "--paths",
            str(root / "src"),
            "--distpath",
            str(dist_path),
            "--workpath",
            str(work_path),
            "--specpath",
            str(spec_path),
            "--collect-submodules",
            "helpme_green",
        ]
        for relative, destination in RUNTIME_DATA:
            source = root / relative
            if not source.exists():
                raise FileNotFoundError(f"Native bundle input is missing: {source}")
            command.extend(["--add-data", _data_argument(source, destination)])
        command.append(str(root / "scripts" / "native_entry.py"))
        subprocess.run(command, cwd=root, check=True)

        bundle = dist_path / "helpme-green"
        if not bundle.is_dir():
            raise RuntimeError(f"PyInstaller did not create the expected bundle: {bundle}")
        _write_bundle_metadata(bundle, version=version, target=target)
        archive_base = output_dir / stem
        created_archive = Path(
            shutil.make_archive(
                str(archive_base), archive_format, root_dir=dist_path, base_dir="helpme-green"
            )
        )
        if created_archive != archive_path:
            raise RuntimeError(f"Unexpected archive path: {created_archive}")

    checksum = sha256(archive_path)
    checksum_path.write_text(f"{checksum}  {archive_path.name}\n", encoding="utf-8")
    return {
        "archive": str(archive_path),
        "sha256": checksum,
        "sizeBytes": archive_path.stat().st_size,
        "target": target,
        "version": version,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/native"))
    args = parser.parse_args(argv)
    try:
        result = package_native(version=args.version, target=args.target, output_dir=args.output)
    except (FileExistsError, FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"native packaging failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
