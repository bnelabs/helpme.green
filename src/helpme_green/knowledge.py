from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class KnowledgeError(ValueError):
    """Raised when the local source catalog cannot be loaded safely."""


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    url: str
    source_type: str = ""
    publisher: str = ""
    material_families: tuple[str, ...] = ()
    jurisdiction: str = ""
    license_note: str = ""
    limitations: str = ""
    authority_tier: str = ""
    scale: str = ""
    access_mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "source_type": self.source_type,
            "publisher": self.publisher,
            "material_families": list(self.material_families),
            "jurisdiction": self.jurisdiction,
            "license_note": self.license_note,
            "limitations": self.limitations,
            "authority_tier": self.authority_tier,
            "scale": self.scale,
            "access_mode": self.access_mode,
        }


class SourceRegistry(Mapping[str, SourceRecord]):
    def __init__(self) -> None:
        self._records: dict[str, SourceRecord] = {}

    def __getitem__(self, key: str) -> SourceRecord:
        return self._records[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def add(self, record: SourceRecord) -> None:
        previous = self._records.get(record.source_id)
        if previous is None:
            self._records[record.source_id] = record
            return
        if previous.url != record.url or previous.title != record.title:
            raise KnowledgeError(
                f"Source ID {record.source_id!r} has conflicting title or URL entries."
            )


def _pack_digest(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class KnowledgeBase:
    """Source-catalog identity used to initialise the retrieval services."""

    root: Path
    manifest: Mapping[str, Any]
    source_registry: SourceRegistry
    digest: str

    @classmethod
    def from_repository(cls, root: Path) -> KnowledgeBase:
        root = root.resolve()
        manifest_path = root / "knowledge/source-manifest.yml"
        if not manifest_path.exists():
            raise KnowledgeError(f"Missing source manifest: {manifest_path}")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, Mapping) or not isinstance(manifest.get("sources"), list):
            raise KnowledgeError("Source manifest must contain a sources list.")

        registry = SourceRegistry()
        for raw in manifest["sources"]:
            if not isinstance(raw, Mapping) or not raw.get("id") or not raw.get("url"):
                raise KnowledgeError("Every source entry needs an id and URL.")
            registry.add(
                SourceRecord(
                    source_id=str(raw["id"]),
                    title=str(raw.get("title", "")),
                    url=str(raw["url"]),
                    source_type=str(raw.get("source_type", "")),
                    publisher=str(raw.get("publisher", "")),
                    material_families=tuple(str(item) for item in raw.get("material_families", ())),
                    jurisdiction=str(raw.get("jurisdiction", "")),
                    license_note=str(raw.get("license_note", "")),
                    limitations=str(raw.get("limitations", "")),
                    authority_tier=str(raw.get("authority_tier", "")),
                    scale=str(raw.get("scale", "")),
                    access_mode=str(raw.get("access_mode", "")),
                )
            )

        digest_paths = [manifest_path]
        for relative in ("skills/material-skills.yml", "knowledge/machine-catalog.yml"):
            path = root / relative
            if path.exists():
                digest_paths.append(path)
        return cls(
            root=root,
            manifest=dict(manifest),
            source_registry=registry,
            digest=_pack_digest(digest_paths),
        )
