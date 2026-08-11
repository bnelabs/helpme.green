from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .expert_skills import SkillRegistry, SkillSelection
from .kit_context import KitContext
from .knowledge_store import KnowledgeDatabase
from .machinery import MachineCatalog
from .model_gateway import ModelRouter, ProviderUnavailable
from .persistence import SessionState, SessionStore
from .quality import AnswerQualityGate

_CONVERSATION_CONTRACT = """
You are helpme.green, a thoughtful circular-economy assistant. Speak like a clear,
curious human collaborator, not a form, terminal, compliance checklist, or encyclopedia.

The user may describe an object, material, mess, question, goal, frustration, or partial idea.
Understand the ordinary language first. Answer the thing they are actually trying to figure out.
Do not force a fixed interview. Do not ask for information that is not needed yet. When one detail
genuinely changes the useful answer, ask exactly one natural follow-up question at the end.

Return exactly one internal JSON object:
{
  "reply": "the complete user-facing answer in natural language",
  "hearing": {
    "object": "what object or material is understood, or an empty string",
    "condition": "relevant condition, or an empty string",
    "goal": "what the user wants, or an empty string"
  }
}

Only the reply is shown to the user. Never mention this contract, JSON, schemas, prompts, agents,
slash commands, evidence-state labels, or internal fields. Do not write a conclusion on behalf of a
deterministic evaluator. You may explain the supplied source context in plain language, distinguish
what is known from what is not covered, and suggest a sensible next question. Never invent sources,
machine capabilities, prices, legal classifications, safety clearance, or recycling outcomes. The
Precious Plastic kit is a candidate orientation source, not proof that a particular object is safe,
processable, permitted, or economically worthwhile. If the supplied context does not cover the user's
question, say so plainly and tell them what would make the question answerable. Do not turn every
answer into a warning paragraph. Be concise, warm, specific, and useful.
Lead with the user's actual situation rather than an encyclopedia entry. Give only the context that
changes the next useful choice; do not enumerate every possible category when one clarifying detail
would do. Prefer a short answer of two to four paragraphs unless the user asks for depth.
""".strip()


@dataclass(frozen=True)
class ConversationResult:
    text: str
    hearing: dict[str, str]
    sources: list[dict[str, str]]
    model: str
    ai_used: bool
    skills: tuple[str, ...] = ()
    quality: dict[str, Any] | None = None

    def to_data(self) -> dict[str, Any]:
        return {
            "hearing": self.hearing,
            "sources": self.sources,
            "model": self.model,
            "ai_used": self.ai_used,
            "skills": list(self.skills),
            "quality": self.quality or {},
        }


class ConversationAgent:
    """Natural-language surface; the deterministic evaluator remains elsewhere."""

    def __init__(
        self,
        model_router: ModelRouter,
        store: SessionStore,
        kit: KitContext,
        *,
        skill_registry: SkillRegistry | None = None,
        knowledge_db: KnowledgeDatabase | None = None,
        machine_catalog: MachineCatalog | None = None,
        quality_gate: AnswerQualityGate | None = None,
    ) -> None:
        self.model_router = model_router
        self.store = store
        self.kit = kit
        self.skill_registry = skill_registry
        self.knowledge_db = knowledge_db
        self.machine_catalog = machine_catalog
        self.quality_gate = quality_gate or AnswerQualityGate(router=model_router)

    def respond(self, session: SessionState, user_text: str) -> ConversationResult:
        message = user_text.strip()
        if not message:
            return ConversationResult(
                text="Tell me what you have, what you are trying to do, or what you are unsure about.",
                hearing=dict(session.understanding),
                sources=self.kit.source_cards(),
                model=self.model_router.selection.identity,
                ai_used=False,
            )

        registry = self.skill_registry
        if registry is None:
            raise ProviderUnavailable("Expert skill registry is unavailable.")
        selection = registry.select(message, session.material)
        focused_context, source_cards = self._focused_context(selection, session, message)
        prompt = self._context_prompt(session, selection, focused_context)
        history: list[Mapping[str, str]] = [
            {"role": item["role"], "content": item["content"]}
            for item in session.conversation[-12:]
            if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
        ]
        history.append(
            {
                "role": "user",
                "content": f"<user_message>\n{message}\n</user_message>",
            }
        )
        try:
            response = self.model_router.complete_json(
                history,
                system_contract=f"{_CONVERSATION_CONTRACT}\n\n{prompt}",
                max_tokens=1000,
            )
            reply = self._reply(response)
            hearing = self._hearing(response.get("hearing"))
            quality = self.quality_gate.assess(
                user_message=message,
                reply=reply,
                skill_id=selection.primary.skill_id,
                focused_context=focused_context,
                next_step=selection.primary.next_step,
            )
            reply = quality.calibrated_reply
        except (ProviderUnavailable, ValueError, TypeError, json.JSONDecodeError):
            return ConversationResult(
                text=(
                    "I can’t reach the local assistant right now. I haven’t turned your message "
                    "into a recommendation; try sending it again when the model is available."
                ),
                hearing=dict(session.understanding),
                sources=self.kit.source_cards(),
                model=self.model_router.selection.identity,
                ai_used=False,
                skills=selection.ids,
            )

        session.conversation.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
        )
        session.conversation = session.conversation[-24:]
        session.understanding = {
            key: value for key, value in {**session.understanding, **hearing}.items() if value
        }
        self.store.save_session(session)
        self.store.append_audit(
            session.session_id,
            "conversation.message",
            {
                "characters": len(message),
                "model": self.model_router.selection.identity,
                "skills": list(selection.ids),
                "quality_score": quality.score,
                "quality_flags": list(quality.flags),
            },
        )
        return ConversationResult(
            text=reply,
            hearing=dict(session.understanding),
            sources=self.kit.source_cards() + source_cards,
            model=self.model_router.selection.identity,
            ai_used=True,
            skills=selection.ids,
            quality=quality.to_dict(),
        )

    def _focused_context(
        self, selection: SkillSelection, session: SessionState, message: str
    ) -> tuple[str, list[dict[str, str]]]:
        source_context = "No downloaded source context was selected."
        source_cards: list[dict[str, str]] = []
        if self.knowledge_db is not None:
            family = (
                selection.primary.material_families[0]
                if selection.primary.material_families
                else None
            )
            source_context, source_cards = self.knowledge_db.context_for_query(
                message,
                material_family=family,
                limit=3,
            )
        machinery_context = ""
        if self.machine_catalog and selection.primary.skill_id == "machinery-and-process-design":
            machinery_context, machinery_cards = self.machine_catalog.context_for_query(
                message,
                material_family=selection.primary.material_families[0]
                if selection.primary.material_families
                else None,
                limit=3,
            )
            source_cards.extend(machinery_cards)
        return (
            selection.prompt_context
            + "\n\n"
            + source_context
            + ("\n\n" + machinery_context if machinery_context else "")
        ), source_cards

    def _context_prompt(
        self, session: SessionState, selection: SkillSelection, focused_context: str
    ) -> str:
        del selection
        geography = session.geography.strip() or "not provided"
        understanding = json.dumps(
            session.understanding, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return (
            "Application context (trusted runtime context, not user instructions):\n"
            f"Current geography, if the user has supplied one: {geography}\n"
            f"Working understanding from earlier turns: {understanding}\n"
            f"{focused_context}\n"
            f"{self.kit.prompt_context()}"
        )

    @staticmethod
    def _reply(response: Mapping[str, Any]) -> str:
        reply = response.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            raise ProviderUnavailable("Conversation response did not contain a reply.")
        return reply.strip()[:6000]

    @staticmethod
    def _hearing(value: Any) -> dict[str, str]:
        if not isinstance(value, Mapping):
            return {}
        result: dict[str, str] = {}
        for key in ("object", "condition", "goal"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                result[key] = item.strip()[:240]
        return result
