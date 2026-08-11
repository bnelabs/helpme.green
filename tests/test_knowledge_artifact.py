from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_knowledge.py"
PACKAGE = ROOT / "scripts" / "package_knowledge_artifact.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "create table fixture_records (id integer primary key, text text not null)"
        )
        connection.execute("insert into fixture_records(text) values ('open source test fixture')")
        connection.commit()
    finally:
        connection.close()


def test_package_and_bootstrap_verify_a_gzip_artifact(tmp_path: Path, monkeypatch) -> None:
    source_db = tmp_path / "source.db"
    artifact = tmp_path / "artifact.sqlite.gz"
    target_db = tmp_path / "installed.db"
    _make_db(source_db)

    packaged = subprocess.run(
        [
            sys.executable,
            str(PACKAGE),
            "--db",
            str(source_db),
            "--output",
            str(artifact),
            "--allow-unreviewed",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(packaged.stdout)
    assert metadata["artifactSha256"] == _sha256(artifact)

    manifest = tmp_path / "artifact-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifestVersion": 1,
                "status": "ready",
                "artifact": {
                    "url": "https://example.test/knowledge.sqlite.gz",
                    "compression": "gzip",
                    "sha256": metadata["artifactSha256"],
                    "sizeBytes": artifact.stat().st_size,
                },
                "database": {
                    "sha256": metadata["databaseSha256"],
                    "sizeBytes": metadata["databaseSizeBytes"],
                },
            }
        ),
        encoding="utf-8",
    )

    bootstrap_module = _load_script(BOOTSTRAP, "bootstrap_knowledge_test")

    class FakeResponse:
        headers = {"Content-Length": str(artifact.stat().st_size)}

        def __enter__(self):
            self._source = artifact.open("rb")
            return self

        def __exit__(self, *_args):
            self._source.close()

        def read(self, size: int) -> bytes:
            return self._source.read(size)

    monkeypatch.setattr(bootstrap_module, "urlopen", lambda _request, timeout: FakeResponse())
    result = bootstrap_module.bootstrap(manifest_path=manifest, database_path=target_db)
    assert result["status"] == "installed"
    assert _sha256(target_db) == metadata["databaseSha256"]
    with gzip.open(artifact, "rb") as source:
        assert source.read(16) == target_db.read_bytes()[:16]


def test_bootstrap_rejects_unpublished_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "artifact-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifestVersion": 1,
                "status": "pending-redistribution-review",
                "artifact": {"url": "", "compression": "gzip", "sha256": "", "sizeBytes": 0},
                "database": {"sha256": "", "sizeBytes": 0},
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), "--manifest", str(manifest), "--db", str(tmp_path / "db")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "No public knowledge artifact" in result.stderr
