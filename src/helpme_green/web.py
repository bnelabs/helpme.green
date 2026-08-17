from __future__ import annotations

import os
from pathlib import Path

_FALLBACK_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f4f0e7">
<meta name="description" content="A calm, source-aware material investigation notebook.">
<title>helpme.green — Lab Notebook</title>
</head>
<body>
<main>
<h1>helpme.green</h1>
<p>The notebook interface is unavailable from the configured static root.</p>
</main>
</body>
</html>
"""


def _static_roots() -> tuple[Path, ...]:
    candidates: list[Path] = []
    configured_root = os.environ.get("HELPME_ROOT", "").strip()
    if configured_root:
        candidates.append(Path(configured_root).expanduser().resolve() / "static")
    candidates.extend(
        (
            Path(__file__).resolve().parents[2] / "static",
            Path.cwd().resolve() / "static",
        )
    )
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def get_index_html() -> str:
    for root in _static_roots():
        candidate = root / "index.html"
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return _FALLBACK_INDEX_HTML


def get_static_root() -> Path | None:
    for root in _static_roots():
        try:
            if root.is_dir():
                return root
        except OSError:
            continue
    return None


# Kept as a compatibility export for callers that imported the old constant.
INDEX_HTML = get_index_html()
