from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_release = _load_script("check_release")
generate_release_notes = _load_script("generate_release_notes")
create_release_manifest = _load_script("create_release_manifest")
package_native = _load_script("package_native")
verify_native_bundle = _load_script("verify_native_bundle")


def test_packaging_uses_one_version_source() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dynamic"] == ["version"]
    assert check_release.read_source_version() == "0.1.0"
    assert check_release.validate_tag("v0.1.0") == "0.1.0"


def test_release_tag_must_match_source_version() -> None:
    with pytest.raises(ValueError, match="does not match"):
        check_release.validate_tag("v0.1.1")
    with pytest.raises(ValueError, match="valid v-prefixed"):
        check_release.version_from_tag("release-0.1.0")


def test_release_notes_extract_the_versioned_changelog_section(tmp_path: Path) -> None:
    output = tmp_path / "notes.md"
    generate_release_notes.main(
        ["0.1.0", "--tag", "v0.1.0", "--commit", "a" * 40, "--output", str(output)]
    )
    text = output.read_text(encoding="utf-8")
    assert "helpme.green v0.1.0" in text
    assert "Exact commit: `" + "a" * 40 in text
    assert "Initial versioned release baseline" in text
    assert "## [Unreleased]" not in text
    assert "Initial versioned release baseline" in generate_release_notes.render(
        "0.1.0-rc.1", tag="v0.1.0-rc.1", commit="c" * 40
    )


def test_release_manifest_records_asset_checksums_and_knowledge_status(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    (asset_dir / "example.zip").write_bytes(b"release")
    (asset_dir / "example.zip.sha256").write_text("ignored\n", encoding="utf-8")
    output = tmp_path / "release-manifest.json"
    create_release_manifest.create_manifest(
        version="0.1.0",
        tag="v0.1.0",
        asset_dir=asset_dir,
        output=output,
        commit="b" * 40,
        container_image="ghcr.io/bnelabs/helpme.green",
        container_digest="sha256:" + "c" * 64,
    )
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["assets"][0]["name"] == "example.zip"
    assert manifest["container"]["digest"].startswith("sha256:")
    assert manifest["knowledgeArtifact"] == {
        "bundled": False,
        "status": "pending-redistribution-review",
    }


def test_native_artifact_names_cover_requested_targets() -> None:
    assert package_native.artifact_stem("0.1.0", "linux-amd64") == (
        "helpme-green-0.1.0-linux-amd64"
    )
    assert package_native.artifact_stem("0.1.0", "windows-arm64") == (
        "helpme-green-0.1.0-windows-arm64"
    )
    assert set(package_native.TARGETS) == {
        "linux-amd64",
        "macos-arm64",
        "macos-amd64",
        "windows-amd64",
        "windows-arm64",
    }


def test_bundle_metadata_is_explicit_about_data_boundaries(tmp_path: Path) -> None:
    bundle = tmp_path / "helpme-green"
    bundle.mkdir()
    package_native._write_bundle_metadata(bundle, version="0.1.0", target="linux-amd64")
    metadata = json.loads((bundle / "RELEASE-METADATA.json").read_text(encoding="utf-8"))
    assert metadata["version"] == "0.1.0"
    assert metadata["target"] == "linux-amd64"
    assert "not bundled" in metadata["knowledge"]
    assert "provider key" in (bundle / "RUN.md").read_text(encoding="utf-8")


def test_tar_extraction_rejects_links(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        link = tarfile.TarInfo("helpme-green/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        target.addfile(link)
    with pytest.raises(ValueError, match="archive link"):
        verify_native_bundle._extract(archive, tmp_path / "out")


def test_native_defaults_use_user_data_when_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    cli_path = ROOT / "src" / "helpme_green" / "cli.py"
    spec = importlib.util.spec_from_file_location("helpme_green.cli", cli_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["helpme_green.cli"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("HELPME_DATA_DIR", raising=False)
    assert module._default_data_dir(Path("/bundle")) == (
        Path.home() / "Library" / "Application Support" / "helpme.green"
    )
