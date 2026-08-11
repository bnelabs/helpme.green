from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class MachineCatalogError(ValueError):
    """Raised when a machine reference record is incomplete or unsafe."""


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+./-]*", re.IGNORECASE)


def _strings(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise MachineCatalogError(f"Machine field {field!r} must be a list.")
    return tuple(str(item).strip() for item in value if str(item).strip())


@dataclass(frozen=True)
class MachineProfile:
    machine_id: str
    brand: str
    product: str
    category: str
    material_families: tuple[str, ...]
    process_stages: tuple[str, ...]
    input_forms: tuple[str, ...]
    outputs: tuple[str, ...]
    capabilities: tuple[str, ...]
    published_specifications: tuple[str, ...]
    scale: str
    official_source_ids: tuple[str, ...]
    techsheet_urls: tuple[str, ...]
    hse_topics: tuple[str, ...]
    limitations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> MachineProfile:
        required = (
            "id",
            "brand",
            "product",
            "category",
            "material_families",
            "process_stages",
            "capabilities",
            "official_source_ids",
            "techsheet_urls",
            "limitations",
        )
        missing = [key for key in required if not raw.get(key)]
        if missing:
            raise MachineCatalogError(
                "Machine profile is missing required fields: " + ", ".join(missing)
            )
        urls = _strings(raw["techsheet_urls"], field="techsheet_urls")
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise MachineCatalogError("Machine techsheet URLs must use explicit HTTPS.")
        return cls(
            machine_id=str(raw["id"]),
            brand=str(raw["brand"]),
            product=str(raw["product"]),
            category=str(raw["category"]),
            material_families=_strings(raw["material_families"], field="material_families"),
            process_stages=_strings(raw["process_stages"], field="process_stages"),
            input_forms=_strings(raw.get("input_forms", []), field="input_forms"),
            outputs=_strings(raw.get("outputs", []), field="outputs"),
            capabilities=_strings(raw["capabilities"], field="capabilities"),
            published_specifications=_strings(
                raw.get("published_specifications", []), field="published_specifications"
            ),
            scale=str(raw.get("scale", "industrial")),
            official_source_ids=_strings(raw["official_source_ids"], field="official_source_ids"),
            techsheet_urls=urls,
            hse_topics=_strings(raw.get("hse_topics", []), field="hse_topics"),
            limitations=_strings(raw["limitations"], field="limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.machine_id,
            "brand": self.brand,
            "product": self.product,
            "category": self.category,
            "materialFamilies": list(self.material_families),
            "processStages": list(self.process_stages),
            "inputForms": list(self.input_forms),
            "outputs": list(self.outputs),
            "capabilities": list(self.capabilities),
            "publishedSpecifications": list(self.published_specifications),
            "scale": self.scale,
            "officialSourceIds": list(self.official_source_ids),
            "techsheetUrls": list(self.techsheet_urls),
            "hseTopics": list(self.hse_topics),
            "limitations": list(self.limitations),
            "referenceStatus": "vendor-reported; requires application testing and HSE review",
        }

    def _search_text(self) -> str:
        return " ".join(
            (
                self.brand,
                self.product,
                self.category,
                *self.material_families,
                *self.process_stages,
                *self.input_forms,
                *self.outputs,
                *self.capabilities,
            )
        ).casefold()


class MachineCatalog:
    """Structured vendor reference records; this catalog never asserts fitness for a case."""

    def __init__(self, profiles: tuple[MachineProfile, ...]) -> None:
        if not profiles:
            raise MachineCatalogError("At least one machine profile is required.")
        seen: set[str] = set()
        for profile in profiles:
            if profile.machine_id in seen:
                raise MachineCatalogError(f"Duplicate machine profile: {profile.machine_id}")
            seen.add(profile.machine_id)
        self.profiles = profiles

    @classmethod
    def from_path(cls, path: Path) -> MachineCatalog:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping) or not isinstance(raw.get("machines"), list):
            raise MachineCatalogError("Machine catalog must contain a machines list.")
        profiles = tuple(
            MachineProfile.from_mapping(item)
            for item in raw["machines"]
            if isinstance(item, Mapping)
        )
        return cls(profiles)

    def public_catalog(self) -> list[dict[str, Any]]:
        return [profile.to_dict() for profile in self.profiles]

    def missing_source_ids(self, source_ids: Iterable[str]) -> tuple[str, ...]:
        available = set(source_ids)
        missing = {
            source_id
            for profile in self.profiles
            for source_id in profile.official_source_ids
            if source_id not in available
        }
        return tuple(sorted(missing))

    def search(
        self, query: str, *, material_family: str | None = None, limit: int = 6
    ) -> list[MachineProfile]:
        query_tokens = {item.casefold() for item in _TOKEN_RE.findall(query)}
        scored: list[tuple[int, int, MachineProfile]] = []
        for order, profile in enumerate(self.profiles):
            if material_family and material_family not in profile.material_families:
                continue
            searchable = profile._search_text()
            score = sum(2 if token in searchable else 0 for token in query_tokens)
            if profile.brand.casefold() in query.casefold():
                score += 5
            if profile.product.casefold() in query.casefold():
                score += 7
            scored.append((score, -order, profile))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [profile for score, _order, profile in scored[: max(1, min(limit, 20))] if score > 0]

    def context_for_query(
        self, query: str, *, material_family: str | None = None, limit: int = 4
    ) -> tuple[str, list[dict[str, str]]]:
        matches = self.search(query, material_family=material_family, limit=limit)
        if not matches:
            return "No machinery reference profile matched this question.", []
        sections: list[str] = []
        cards: list[dict[str, str]] = []
        for profile in matches:
            sections.append(
                "\n".join(
                    (
                        f"[{profile.brand} {profile.product}; vendor-reported reference]",
                        f"Category: {profile.category}; scale: {profile.scale}",
                        "Process stages: " + ", ".join(profile.process_stages),
                        "Input forms: " + ", ".join(profile.input_forms),
                        "Materials: " + ", ".join(profile.material_families),
                        "Published capabilities: " + "; ".join(profile.capabilities),
                        "Published specifications: "
                        + ("; ".join(profile.published_specifications) or "not summarized"),
                        "HSE topics to review: " + ", ".join(profile.hse_topics),
                        "Limitations: " + "; ".join(profile.limitations),
                        "Official technical references: " + ", ".join(profile.techsheet_urls),
                    )
                )
            )
            cards.append(
                {
                    "label": f"{profile.brand} {profile.product}",
                    "detail": "Vendor reference · verify with trials, specifications, and HSE review",
                }
            )
        return (
            "Machinery reference profiles (vendor-reported; not a recommendation or fitness guarantee):\n"
            + "\n\n".join(sections),
            cards,
        )
