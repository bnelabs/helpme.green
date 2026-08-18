#!/usr/bin/env python3
"""Sign a staged native bundle and re-archive it for stable publication."""

from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from package_native import TARGETS, sha256
from verify_native_bundle import _extract


def _required_environment(*names: str) -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = os.environ.get(name, "")
        if value:
            values[name] = value
        else:
            missing.append(name)
    if missing:
        raise RuntimeError("Missing signing environment: " + ", ".join(missing))
    return values


def _bundle_root(extraction_root: Path) -> Path:
    metadata_paths = list(extraction_root.rglob("RELEASE-METADATA.json"))
    if len(metadata_paths) != 1:
        raise RuntimeError(f"Expected one RELEASE-METADATA.json, found {len(metadata_paths)}")
    return metadata_paths[0].parent


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _sign_macos(bundle: Path) -> None:
    values = _required_environment(
        "MACOS_CERTIFICATE_BASE64",
        "MACOS_CERTIFICATE_PASSWORD",
        "MACOS_SIGNING_IDENTITY",
        "APPLE_ID",
        "APPLE_APP_PASSWORD",
        "APPLE_TEAM_ID",
    )
    with tempfile.TemporaryDirectory(prefix="helpme-green-macos-sign-") as temporary:
        temporary_root = Path(temporary)
        certificate = temporary_root / "certificate.p12"
        certificate.write_bytes(base64.b64decode(values["MACOS_CERTIFICATE_BASE64"]))
        keychain = temporary_root / "release.keychain-db"
        keychain_password = values["MACOS_CERTIFICATE_PASSWORD"]
        try:
            _run(["security", "create-keychain", "-p", keychain_password, str(keychain)])
            _run(["security", "set-keychain-settings", "-lut", "21600", str(keychain)])
            _run(["security", "unlock-keychain", "-p", keychain_password, str(keychain)])
            _run(
                [
                    "security",
                    "import",
                    str(certificate),
                    "-P",
                    values["MACOS_CERTIFICATE_PASSWORD"],
                    "-A",
                    "-t",
                    "cert",
                    "-f",
                    "pkcs12",
                    "-k",
                    str(keychain),
                ]
            )
            signable = [
                path
                for path in bundle.rglob("*")
                if path.is_file() and path.suffix in {".dylib", ".so"}
            ]
            executable = bundle / "helpme-green"
            if executable.is_file():
                signable.append(executable)
            for path in sorted(signable, key=lambda item: len(item.parts)):
                _run(
                    [
                        "codesign",
                        "--force",
                        "--options",
                        "runtime",
                        "--timestamp",
                        "--sign",
                        values["MACOS_SIGNING_IDENTITY"],
                        "--keychain",
                        str(keychain),
                        str(path),
                    ]
                )
            _run(
                [
                    "codesign",
                    "--verify",
                    "--deep",
                    "--strict",
                    "--verbose=2",
                    str(executable),
                ]
            )
        finally:
            subprocess.run(["security", "delete-keychain", str(keychain)], check=False)


def _sign_windows(bundle: Path) -> None:
    values = _required_environment("WINDOWS_CERTIFICATE_BASE64", "WINDOWS_CERTIFICATE_PASSWORD")
    with tempfile.TemporaryDirectory(prefix="helpme-green-windows-sign-") as temporary:
        certificate = Path(temporary) / "certificate.pfx"
        certificate.write_bytes(base64.b64decode(values["WINDOWS_CERTIFICATE_BASE64"]))
        signable = [
            path
            for path in bundle.rglob("*")
            if path.is_file() and path.suffix.lower() in {".exe", ".dll", ".pyd"}
        ]
        if not signable:
            raise RuntimeError(f"No Windows executables found under {bundle}")
        for path in signable:
            _run(
                [
                    "signtool",
                    "sign",
                    "/fd",
                    "SHA256",
                    "/td",
                    "SHA256",
                    "/tr",
                    "http://timestamp.digicert.com",
                    "/f",
                    str(certificate),
                    "/p",
                    values["WINDOWS_CERTIFICATE_PASSWORD"],
                    str(path),
                ]
            )
            _run(["signtool", "verify", "/pa", "/all", str(path)])


def _notarize_macos(archive: Path) -> None:
    values = _required_environment("APPLE_ID", "APPLE_APP_PASSWORD", "APPLE_TEAM_ID")
    _run(
        [
            "xcrun",
            "notarytool",
            "submit",
            str(archive),
            "--apple-id",
            values["APPLE_ID"],
            "--password",
            values["APPLE_APP_PASSWORD"],
            "--team-id",
            values["APPLE_TEAM_ID"],
            "--wait",
        ]
    )


def sign_archive(archive: Path, *, platform: str, output: Path) -> dict[str, str | int]:
    if platform not in TARGETS:
        raise ValueError(f"Unsupported native target {platform!r}.")
    if output.exists() or Path(f"{output}.sha256").exists():
        raise FileExistsError(f"Signed output already exists: {output}")
    if platform.startswith("linux-"):
        raise ValueError(
            "Linux native bundles use checksum and provenance verification, not this signer."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="helpme-green-signed-") as temporary:
        extraction_root = Path(temporary)
        _extract(archive, extraction_root)
        bundle = _bundle_root(extraction_root)
        if platform.startswith("macos-"):
            _sign_macos(bundle)
        else:
            _sign_windows(bundle)
        archive_format = TARGETS[platform]
        if output.name.endswith(".tar.gz"):
            archive_base = output.with_name(output.name[: -len(".tar.gz")])
        else:
            archive_base = output.with_suffix("")
        created = Path(
            shutil.make_archive(
                str(archive_base),
                archive_format,
                root_dir=extraction_root,
                base_dir=bundle.name,
            )
        )
        if created != output:
            raise RuntimeError(f"Unexpected signed archive path: {created}")
        if platform.startswith("macos-"):
            _notarize_macos(output)
    checksum = sha256(output)
    Path(f"{output}.sha256").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    return {"archive": str(output), "sha256": checksum, "sizeBytes": output.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--platform", choices=sorted(TARGETS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = sign_archive(args.archive, platform=args.platform, output=args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"native signing failed: {exc}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
