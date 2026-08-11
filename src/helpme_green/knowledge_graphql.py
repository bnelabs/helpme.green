from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .expert_skills import SkillRegistry
from .knowledge_store import KnowledgeDatabase
from .machinery import MachineCatalog


class GraphQLQueryError(ValueError):
    """Raised for unsupported or mutating expert queries."""


@dataclass(frozen=True)
class _Field:
    name: str
    arguments: dict[str, str]
    selection: tuple[_Field, ...]


_TOKEN_RE = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<number>-?[0-9]+)|"
    r'(?P<string>"(?:\\.|[^"\\])*")|(?P<punct>[{}():,!$])'
)


class _Parser:
    def __init__(self, query: str) -> None:
        self.tokens = [match.group(0) for match in _TOKEN_RE.finditer(query)]
        self.position = 0

    def parse(self) -> tuple[_Field, ...]:
        if not self.tokens:
            raise GraphQLQueryError("GraphQL query is empty.")
        if self._peek() in {"query", "operation"}:
            self._take()
            if self._peek() not in {"{", None}:
                self._take()
        elif self._peek() == "mutation":
            raise GraphQLQueryError("Knowledge GraphQL is read-only; mutations are forbidden.")
        result = self._selection_set()
        if self._peek() is not None:
            raise GraphQLQueryError("Unexpected tokens after the GraphQL selection.")
        return result

    def _selection_set(self) -> tuple[_Field, ...]:
        self._expect("{")
        fields: list[_Field] = []
        while self._peek() not in {None, "}"}:
            fields.append(self._field())
        self._expect("}")
        return tuple(fields)

    def _field(self) -> _Field:
        name = self._take()
        if name in {"{", "}", "(", ")", ":", ","}:
            raise GraphQLQueryError("Invalid GraphQL field.")
        arguments: dict[str, str] = {}
        if self._peek() == "(":
            self._take()
            while self._peek() not in {None, ")"}:
                key = self._take()
                self._expect(":")
                value = self._take()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                arguments[key] = value
                if self._peek() == ",":
                    self._take()
            self._expect(")")
        selection: tuple[_Field, ...] = ()
        if self._peek() == "{":
            selection = self._selection_set()
        return _Field(name, arguments, selection)

    def _peek(self) -> str | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _take(self) -> str:
        token = self._peek()
        if token is None:
            raise GraphQLQueryError("Unexpected end of GraphQL query.")
        self.position += 1
        return token

    def _expect(self, value: str) -> None:
        if self._take() != value:
            raise GraphQLQueryError(f"Expected {value!r} in GraphQL query.")


def _limit(arguments: dict[str, str], default: int = 20) -> int:
    try:
        value = int(arguments.get("limit", default))
    except ValueError as exc:
        raise GraphQLQueryError("GraphQL limit must be an integer.") from exc
    return max(1, min(value, 100))


def _project(value: Any, selection: tuple[_Field, ...]) -> Any:
    if not selection:
        return value
    if isinstance(value, list):
        return [_project(item, selection) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for field in selection:
        if field.name not in value:
            raise GraphQLQueryError(f"Unknown field {field.name!r}.")
        result[field.name] = _project(value[field.name], field.selection)
    return result


def _skill_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": value["id"],
        "title": value["title"],
        "materialFamilies": value["material_families"],
        "sourceDomains": value["source_domains"],
    }


def execute_graphql(
    database: KnowledgeDatabase,
    registry: SkillRegistry,
    query: str,
    machine_catalog: MachineCatalog | None = None,
) -> dict[str, Any]:
    try:
        fields = _Parser(query).parse()
        data: dict[str, Any] = {}
        for field in fields:
            if field.name == "skills":
                data[field.name] = _project(
                    [_skill_dict(item) for item in registry.public_catalog()],
                    field.selection,
                )
            elif field.name == "machines":
                if machine_catalog is None:
                    raise GraphQLQueryError("Machine catalog is unavailable.")
                material_family = field.arguments.get("materialFamily")
                profiles = [
                    item
                    for item in machine_catalog.public_catalog()
                    if not material_family or material_family in item["materialFamilies"]
                ][: _limit(field.arguments)]
                data[field.name] = _project(profiles, field.selection)
            elif field.name == "sources":
                data[field.name] = _project(
                    [
                        {
                            "id": item["id"],
                            "title": item["title"],
                            "url": item["url"],
                            "publisher": item["publisher"],
                            "sourceType": item["sourceType"],
                            "materialFamilies": item["materialFamilies"],
                            "status": item["status"],
                            "authorityTier": item["authorityTier"],
                            "scale": item["scale"],
                            "fetchedAt": item["fetchedAt"],
                        }
                        for item in database.source_catalog(
                            field.arguments.get("materialFamily"), _limit(field.arguments)
                        )
                    ],
                    field.selection,
                )
            elif field.name == "search":
                query_text = field.arguments.get("query", "").strip()
                if not query_text:
                    raise GraphQLQueryError("search requires a query argument.")
                data[field.name] = _project(
                    [
                        {
                            "chunkId": item.chunk_id,
                            "documentId": item.document_id,
                            "sourceId": item.source_id,
                            "title": item.title,
                            "url": item.url,
                            "sourceStatus": item.source_status,
                            "authorityTier": item.authority_tier,
                            "scale": item.scale,
                            "text": item.text,
                            "score": item.score,
                        }
                        for item in database.search(
                            query_text,
                            material_family=field.arguments.get("materialFamily"),
                            limit=_limit(field.arguments, 6),
                        )
                    ],
                    field.selection,
                )
            elif field.name == "graph":
                node_id = field.arguments.get("nodeId", "").strip()
                if not node_id:
                    raise GraphQLQueryError("graph requires a nodeId argument.")
                data[field.name] = _project(
                    [
                        item.to_dict()
                        for item in database.graph_neighbors(node_id, _limit(field.arguments))
                    ],
                    field.selection,
                )
            elif field.name == "status":
                summary = database.ingestion_summary()
                data[field.name] = _project(
                    {
                        "schemaVersion": database.schema_version,
                        "digest": database.digest(),
                        "sourceCount": summary["sources"]["total"],
                        "documentCount": summary["documents"]["total"],
                        "searchableChunks": summary["chunks"]["searchable"],
                        "failedSources": len(summary["runs"]["failures"]),
                        "latestExtractedSources": summary["retrieval"]["latestExtractedSources"],
                    },
                    field.selection,
                )
            else:
                raise GraphQLQueryError(f"Unknown GraphQL field {field.name!r}.")
        return {"data": data}
    except GraphQLQueryError as exc:
        return {"errors": [{"message": str(exc)}]}
