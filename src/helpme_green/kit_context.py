from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KitContext:
    """A small, provenance-aware description of the locally mounted kit.

    The assistant receives the kit map, not an unbounded dump of user files. The
    actual PDFs remain available as a read-only local reference for a later
    reviewed extraction step.
    """

    source_id: str
    version: str
    available: bool
    root_label: str
    sections: tuple[str, ...]
    subsections: tuple[str, ...]
    reference_files: tuple[str, ...]
    readme_excerpt: str

    @classmethod
    def from_environment(cls) -> KitContext:
        configured = os.environ.get("HELPME_KIT_ROOT", "/app/precious-plastic-kit")
        root = Path(configured).expanduser()
        if not root.is_dir():
            return cls(
                source_id="precious-plastic-kit-v4.1",
                version="V4.1",
                available=False,
                root_label="local kit is not mounted",
                sections=(),
                subsections=(),
                reference_files=(),
                readme_excerpt="",
            )

        sections: list[str] = []
        subsections: list[str] = []
        reference_files: list[str] = []
        try:
            for child in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
                if child.name.startswith("."):
                    continue
                if child.is_dir():
                    sections.append(child.name)
                    for nested in sorted(child.iterdir(), key=lambda path: path.name.casefold()):
                        if nested.is_dir() and not nested.name.startswith("."):
                            subsections.append(f"{child.name}/{nested.name}")
            for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
                if len(reference_files) >= 120 or not path.is_file():
                    continue
                if path.suffix.casefold() in {".pdf", ".md", ".txt"}:
                    reference_files.append(path.relative_to(root).as_posix())
            readme_path = root / "README.txt"
            readme_excerpt = readme_path.read_text(encoding="utf-8", errors="replace")[:1200]
        except OSError:
            return cls(
                source_id="precious-plastic-kit-v4.1",
                version="V4.1",
                available=False,
                root_label="local kit could not be read",
                sections=(),
                subsections=(),
                reference_files=(),
                readme_excerpt="",
            )
        return cls(
            source_id="precious-plastic-kit-v4.1",
            version="V4.1",
            available=True,
            root_label="local Precious Plastic Download Kit",
            sections=tuple(sections),
            subsections=tuple(subsections),
            reference_files=tuple(reference_files),
            readme_excerpt=readme_excerpt,
        )

    def prompt_context(self) -> str:
        if not self.available:
            return (
                "The local Precious Plastic Download Kit V4.1 is not mounted in this runtime. "
                "Do not pretend to have searched it."
            )
        sections = ", ".join(self.sections[:12]) or "not enumerated"
        anchors: list[str] = []
        keywords = (
            "safety",
            "introduction",
            "plastic-types",
            "physical-properties",
            "action plan",
            "business plan",
            "workspace calculator",
        )
        for path in self.reference_files:
            lowered = path.casefold()
            if any(keyword in lowered for keyword in keywords):
                anchors.append(path)
            if len(anchors) >= 12:
                break
        if not anchors:
            anchors = list(self.reference_files[:8])
        anchor_text = ", ".join(anchors) or "not enumerated"
        return (
            "Local candidate reference available: Precious Plastic Download Kit V4.1. It is useful "
            "for orientation and discovery, not for deciding safety, engineering, permitting, "
            "performance, legal status, or financial value. The kit README says to begin with its "
            "introduction and safety material. This message contains only the map below; do not "
            "claim that a document was read or that it proves an answer.\n"
            f"Top-level areas: {sections}.\n"
            f"Potentially relevant reference names: {anchor_text}."
        )

    def source_cards(self) -> list[dict[str, str]]:
        if not self.available:
            return []
        return [
            {
                "label": "Precious Plastic Download Kit V4.1",
                "detail": "Background orientation only; it does not answer safety, permission, or business-worth questions.",
            }
        ]
