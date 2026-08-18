"""PyInstaller entry point for target-native helpme.green bundles."""

from __future__ import annotations

from helpme_green.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
