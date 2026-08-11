from __future__ import annotations

from .engine import ActionView, EvaluationResult
from .knowledge import SourceReference


class ExplainerAgent:
    """Render engine output; it cannot add claims or change statuses."""

    mission = (
        "Translate deterministic EvaluationResult into plain language with sources and tier labels."
    )
    inputs = "Only a deterministic EvaluationResult produced by the evaluator core."
    outputs = "A faithful explanation of statuses, blocks, evidence, sources, and next actions."
    autonomy_scope = "Format and translate existing engine fields without changing their meaning."
    forbidden_actions = (
        "add a claim",
        "soften a block",
        "omit an unknown",
        "compute a value",
    )
    escalation = (
        "Preserve the block and surface missing evidence when an explanation field is absent."
    )
    anti_myopia = "If readability conflicts with an engine guarantee, retain the guarantee and the UNKNOWN state."

    def render(self, result: EvaluationResult) -> str:
        lines = [
            "helpme.green — advisory assessment",
            "This is a decision aid. It does not approve, execute, or conclude.",
            f"Location used: {result.geography}",
            "",
            "What I can say now",
        ]
        if result.invariant_blocks:
            lines.append("Important limits:")
            for block in result.invariant_blocks:
                lines.append(f"- {self._friendly_block(block)}")
        else:
            lines.append("No global safety or coverage gate is currently blocking the assessment.")
        lines.extend(["", "Possible routes"])
        if any("copper-cable" in version for version in result.knowledge_pack_versions):
            lines.append(
                "Coverage note: the current route pack covers copper cable. A different description is kept separate until it is matched; the console will not silently assume it is copper."
            )
        for route in result.routes:
            open_checks = sum(item.state.value != "SATISFIED" for item in route.requirement_results)
            lines.append(f"- {route.title}: {self._friendly_route_status(route.status.value)}")
            if open_checks:
                lines.append(
                    f"  {open_checks} check(s) still open before this route is decision-ready."
                )
            else:
                lines.append("  All listed checks are satisfied at the current evidence level.")
        lines.extend(["", self.render_actions(result.next_actions)])
        lines.extend(
            [
                "",
                "Value",
                "Not calculated: there is no complete source-backed economic basis yet.",
                "Use /sources to see the route sources. Use /evidence to see what the console can rely on from your inputs.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _friendly_route_status(status: str) -> str:
        return {
            "PRELIMINARY_CANDIDATE": "Possible — early candidate",
            "CONDITIONAL": "Conditional — depends on open checks",
            "TECHNICALLY_SUPPORTED": "Technically supported — commercial checks remain",
            "FINANCIALLY_COMPARABLE": "Comparable — still advisory",
            "BLOCKED": "Blocked — do not act on this route yet",
            "NOT_RELEVANT": "Not matched by the current description",
            "RESEARCH_STAGE": "Research stage",
        }.get(status, status.replace("_", " ").title())

    @staticmethod
    def _friendly_block(block: str) -> str:
        if block.startswith("R10_CONTAMINATION"):
            return "Condition and contamination have not been checked to the required level."
        if block == "R6_JURISDICTION_NOT_COVERED":
            return "The requested location does not have the required coverage for this assessment."
        return "A required safety or coverage check is still open."

    def render_actions(self, actions: tuple[ActionView, ...]) -> str:
        """Show next actions as decisions the user can take, not as a data dump."""
        lines = [
            "What to do next",
            "These are the practical checks that could change the assessment. They are not tasks you must complete before asking a basic question.",
        ]
        if not actions:
            lines.append("No additional action is currently listed.")
            return "\n".join(lines)
        for index, action in enumerate(actions[:8], start=1):
            description = self._friendly_action_description(action)
            lines.extend(
                [
                    "",
                    f"{index}. {action.title} ({action.priority.title()} priority)",
                    f"   {description}",
                ]
            )
            if action.acquisition_cost_class != "UNKNOWN":
                lines.append(f"   Effort/cost signal: {action.acquisition_cost_class.lower()}.")
        return "\n".join(lines)

    @staticmethod
    def _friendly_action_description(action: ActionView) -> str:
        if action.key == "screen-contamination":
            return (
                "Provide an inspection or appropriate screening record describing oils, liquids, "
                "attachments, and hazardous concerns. If you have no record, leave this unknown; "
                "your statement alone is not clearance."
            )
        if action.key == "confirm-jurisdiction":
            return (
                "Provide the country/site and, where needed, a jurisdiction-specific review. "
                "This is only needed for conclusions that depend on local rules."
            )
        if (
            action.description
            == "Answer this governed question and retain the stated evidence label."
        ):
            return "Answer the question in ordinary language. The console will tell you if a stronger check is needed."
        return action.description

    def render_sources(self, sources: tuple[SourceReference, ...]) -> str:
        if not sources:
            return "Sources behind this assessment\nNo source references are attached to the current result."
        lines = [
            "Sources behind this assessment",
            "These sources support the route knowledge; they do not verify the user's specific material.",
        ]
        for source in sources:
            location = f" ({source.location})" if source.location else ""
            lines.extend(["", f"- {source.title}{location}", f"  {source.url}"])
            if source.limitations:
                lines.append(f"  Limitation: {source.limitations}")
        return "\n".join(lines)
