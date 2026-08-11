from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from helpme_green.knowledge import KnowledgeBase  # noqa: E402
from helpme_green.verification import run_phase_a_verification  # noqa: E402


def main() -> int:
    knowledge = KnowledgeBase.from_repository(ROOT)
    summary = run_phase_a_verification(knowledge, count=100)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    if summary.representative_count != 100:
        return 1
    if summary.fabricated_source_references != 0:
        return 1
    if summary.financial_outputs != 0:
        return 1
    if not summary.cross_model_equal:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
