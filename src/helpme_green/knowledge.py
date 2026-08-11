from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml


class KnowledgeError(ValueError):
    """Raised when a knowledge pack cannot be safely used."""


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    url: str
    source_type: str = ""
    publisher: str = ""
    location_reference: str = ""
    limitations: str = ""
    confidence: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "source_type": self.source_type,
            "publisher": self.publisher,
            "location_reference": self.location_reference,
            "limitations": self.limitations,
            "confidence": self.confidence,
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
                f"Source ID {record.source_id!r} has conflicting title or URL in the copied pack."
            )


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key), child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _source_definitions(document: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(document, Mapping):
        for key, value in document.items():
            if key == "sources" and isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping) and item.get("id") and item.get("url"):
                        yield item
            yield from _source_definitions(value)
    elif isinstance(document, list):
        for item in document:
            yield from _source_definitions(item)


def _source_references(document: Any) -> set[str]:
    references: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                name = str(child_key)
                if name == "source_id" and isinstance(child, str):
                    references.add(child)
                elif name == "source_ids" and isinstance(child, list):
                    references.update(str(item) for item in child)
                elif name == "sources" and isinstance(child, list):
                    for item in child:
                        if isinstance(item, Mapping):
                            if item.get("id"):
                                references.add(str(item["id"]))
                            if item.get("source_id"):
                                references.add(str(item["source_id"]))
                        elif isinstance(item, str):
                            references.add(item)
                visit(child, name)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)

    visit(document)
    return references


def _pack_digest(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    title: str
    url: str
    location: str
    limitations: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "location": self.location,
            "limitations": self.limitations,
        }


class KnowledgeBase:
    def __init__(
        self,
        *,
        root: Path,
        manifest: Mapping[str, Any],
        documents: Mapping[str, Mapping[str, Any]],
        source_registry: SourceRegistry,
        register_texts: tuple[str, ...],
    ) -> None:
        self.root = root
        self.manifest = dict(manifest)
        self.documents = dict(documents)
        self.source_registry = source_registry
        self.register_texts = register_texts
        self.reference_commit = str(manifest["reference_commit"])
        manifest_paths = [root / path for path in manifest["files"]]
        self.digest = _pack_digest(manifest_paths)
        self.copper_routes_v02 = tuple(
            self.documents["knowledge/routes/copper-cable-v0.2.yml"].get("cards", [])
        )
        all_routes_v03 = tuple(
            self.documents["knowledge/routes/discovery-v0.3.yml"].get("cards", [])
        )
        self.discovery_routes_v03 = all_routes_v03
        self.copper_routes_v03 = tuple(
            card for card in all_routes_v03 if str(card.get("id", "")).startswith("copper-cable-")
        )
        self.copper_material_v02 = self.documents["knowledge/materials/copper-cable-v0.2.yml"][
            "cards"
        ][0]
        self.copper_material_v03 = self.documents["knowledge/materials/discovery-v0.3.yml"][
            "cards"
        ][0]

    @classmethod
    def from_repository(cls, root: Path) -> KnowledgeBase:
        root = root.resolve()
        manifest_path = root / "vendor/reference/knowledge-manifest.json"
        if not manifest_path.exists():
            raise KnowledgeError(f"Missing reference manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest.get("files", {})
        if not isinstance(files, Mapping) or not files:
            raise KnowledgeError("Reference manifest has no files.")
        for raw_path, expected in files.items():
            path = root / str(raw_path)
            if not path.exists():
                raise KnowledgeError(f"Manifest file is missing: {raw_path}")
            algorithm, expected_hash = str(expected).split(":", 1)
            if algorithm != "sha256":
                raise KnowledgeError(f"Unsupported manifest digest for {raw_path}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected_hash:
                raise KnowledgeError(f"Reference pack digest mismatch: {raw_path}")

        documents: dict[str, Mapping[str, Any]] = {}
        registry = SourceRegistry()
        references: set[str] = set()
        for raw_path in files:
            path = root / str(raw_path)
            if path.suffix in {".yml", ".yaml"}:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, Mapping):
                    raise KnowledgeError(f"Pack is not a mapping: {raw_path}")
                documents[str(raw_path)] = data
                references.update(_source_references(data))
                for source in _source_definitions(data):
                    registry.add(
                        SourceRecord(
                            source_id=str(source["id"]),
                            title=str(source.get("title", "")),
                            url=str(source.get("url", "")),
                            source_type=str(source.get("source_type", "")),
                            publisher=str(source.get("publisher", "")),
                            location_reference=str(source.get("location_reference", "")),
                            limitations=str(source.get("limitations", "")),
                            confidence=str(source.get("confidence", "")),
                        )
                    )
        register_texts = (
            (root / "knowledge/research/copper-cable-source-register.md").read_text(
                encoding="utf-8"
            ),
            (root / "knowledge/research/discovery-v0.3-source-register.md").read_text(
                encoding="utf-8"
            ),
        )
        missing_registry = sorted(references.difference(registry))
        if missing_registry:
            raise KnowledgeError(
                "Pack references source IDs without a full source definition: "
                + ", ".join(missing_registry)
            )
        base = cls(
            root=root,
            manifest=manifest,
            documents=documents,
            source_registry=registry,
            register_texts=register_texts,
        )
        errors = base.validate_provenance()
        if errors:
            raise KnowledgeError("; ".join(errors))
        return base

    def validate_provenance(self) -> tuple[str, ...]:
        errors: list[str] = []
        for path, document in self.documents.items():
            if path.startswith("knowledge/compliance/"):
                continue
            references = _source_references(document)
            for source_id in sorted(references):
                if source_id not in self.source_registry:
                    errors.append(f"{path}: source {source_id} is not defined")
                elif not any(f"`{source_id}`" in text for text in self.register_texts):
                    errors.append(f"{path}: source {source_id} is absent from source registers")
            if not document.get("cards"):
                errors.append(f"{path}: no cards")
        return tuple(errors)

    def route_by_key(self, key: str) -> Mapping[str, Any] | None:
        for route in self.copper_routes_v03:
            if str(route.get("id")) == key or str(route.get("business_id")) == key:
                return cast(Mapping[str, Any], route)
        for route in self.copper_routes_v02:
            if str(route.get("id")) == key or str(route.get("business_id")) == key:
                return cast(Mapping[str, Any], route)
        return None

    def route_source_ids(self, route: Mapping[str, Any]) -> tuple[str, ...]:
        ids: set[str] = set()
        for source in route.get("sources", []) or []:
            if isinstance(source, Mapping):
                if source.get("id"):
                    ids.add(str(source["id"]))
                if source.get("source_id"):
                    ids.add(str(source["source_id"]))
            elif isinstance(source, str):
                ids.add(source)
        for claim in route.get("claims", []) or []:
            if isinstance(claim, Mapping):
                for source in claim.get("sources", []) or []:
                    if isinstance(source, Mapping) and source.get("source_id"):
                        ids.add(str(source["source_id"]))
        return tuple(sorted(ids))

    def source_references_for(
        self, source_ids: Iterable[str], route: Mapping[str, Any] | None = None
    ) -> tuple[SourceReference, ...]:
        locations: dict[str, str] = {}
        limitations: dict[str, str] = {}
        if route is not None:
            for claim in route.get("claims", []) or []:
                if not isinstance(claim, Mapping):
                    continue
                for link in claim.get("sources", []) or []:
                    if isinstance(link, Mapping) and link.get("source_id"):
                        source_id = str(link["source_id"])
                        locations[source_id] = str(link.get("source_location", ""))
                        limitations[source_id] = str(link.get("limitations", ""))
        refs: list[SourceReference] = []
        for source_id in sorted(set(str(item) for item in source_ids)):
            record = self.source_registry[source_id]
            refs.append(
                SourceReference(
                    source_id=source_id,
                    title=record.title,
                    url=record.url,
                    location=locations.get(source_id, record.location_reference),
                    limitations=limitations.get(source_id, record.limitations),
                )
            )
        return tuple(refs)
