from __future__ import annotations

import hashlib
import io
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

import yaml

from .knowledge_store import IngestResult, KnowledgeDatabase, SourceSpec


class SourceFetchError(ValueError):
    """Raised when a source cannot be fetched or extracted within policy."""


_ACCESS_CHALLENGE_MARKERS = (
    "checking your browser",
    "captcha",
    "access denied",
    "verify you are human",
    "enable javascript and cookies",
)


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]: ...


def _is_loopback_endpoint(endpoint: str) -> bool:
    parsed = urllib.parse.urlparse(endpoint)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class SourceManifest:
    sources: tuple[SourceSpec, ...]
    allowed_hosts: frozenset[str]

    @classmethod
    def from_path(cls, path: Path) -> SourceManifest:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping) or not isinstance(raw.get("sources"), list):
            raise SourceFetchError("Source manifest must contain a sources list.")
        sources: list[SourceSpec] = []
        hosts: set[str] = set()
        for item in raw["sources"]:
            if not isinstance(item, Mapping):
                raise SourceFetchError("Source manifest entries must be objects.")
            url = str(item.get("url", ""))
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise SourceFetchError("Every source manifest URL must be explicit HTTPS.")
            hosts.add(parsed.hostname.casefold())
            fallback_urls = item.get("fetch_urls", [])
            if not isinstance(fallback_urls, list):
                raise SourceFetchError("Source fetch_urls must be a list.")
            normalized_fallbacks: list[str] = []
            for fallback_url in fallback_urls:
                fallback = str(fallback_url)
                parsed_fallback = urllib.parse.urlparse(fallback)
                if parsed_fallback.scheme != "https" or not parsed_fallback.hostname:
                    raise SourceFetchError("Every source fallback URL must be explicit HTTPS.")
                hosts.add(parsed_fallback.hostname.casefold())
                normalized_fallbacks.append(fallback)
            families = item.get("material_families", [])
            if not isinstance(families, list):
                raise SourceFetchError("Source material_families must be a list.")
            sources.append(
                SourceSpec(
                    source_id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    url=url,
                    publisher=str(item.get("publisher", "")),
                    source_type=str(item.get("source_type", "OFFICIAL_GUIDANCE")),
                    material_families=tuple(str(value) for value in families),
                    jurisdiction=str(item.get("jurisdiction", "")),
                    license_note=str(item.get("license_note", "")),
                    limitations=str(item.get("limitations", "")),
                    authority_tier=str(item.get("authority_tier", "secondary")),
                    scale=str(item.get("scale", "")),
                    access_mode=str(item.get("access_mode", "web")),
                    fetch_urls=tuple(normalized_fallbacks),
                )
            )
        return cls(tuple(sources), frozenset(hosts))


class _VisibleTextParser(HTMLParser):
    _ignored = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in self._ignored:
            self._ignored_depth += 1
        elif self._ignored_depth == 0 and tag.casefold() in {"p", "li", "h1", "h2", "h3", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._ignored and self._ignored_depth:
            self._ignored_depth -= 1
        elif self._ignored_depth == 0 and tag.casefold() in {"p", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self.parts.append(data)


def _extract_content(data: bytes, content_type: str, url: str) -> tuple[str, str]:
    normalized_type = content_type.casefold().split(";", 1)[0].strip()
    if normalized_type == "application/pdf" or url.casefold().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise SourceFetchError(
                "PDF extraction requires the optional pypdf runtime dependency."
            ) from exc
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pypdf exposes several parser-specific exceptions.
            raise SourceFetchError("PDF extraction failed safely.") from exc
        return text, "application/pdf"
    if normalized_type in {
        "text/html",
        "application/xhtml+xml",
        "application/xml",
        "text/xml",
    } or url.casefold().endswith((".html", ".htm", ".xml")):
        parser = _VisibleTextParser()
        parser.feed(data.decode("utf-8", errors="replace"))
        return "\n".join(parser.parts), normalized_type or "text/html"
    if normalized_type in {"text/plain", "text/csv", "application/json"}:
        text = data.decode("utf-8", errors="replace")
        if normalized_type == "application/json":
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        return text, normalized_type
    raise SourceFetchError(
        f"Unsupported source content type {normalized_type or 'unknown'}; "
        "use a text page or add a reviewed extractor."
    )


def _is_access_challenge(text: str) -> bool:
    sample = text.casefold()[:6000]
    return any(marker in sample for marker in _ACCESS_CHALLENGE_MARKERS)


class OfficialSourceFetcher:
    """Bounded HTTPS fetcher; every host must come from the explicit manifest allowlist."""

    def __init__(
        self,
        *,
        allowed_hosts: Iterable[str],
        max_bytes: int = 32_000_000,
        download_dir: Path | None = None,
    ) -> None:
        self.allowed_hosts = frozenset(host.casefold() for host in allowed_hosts)
        if max_bytes <= 0:
            raise ValueError("Source fetch limit must be positive.")
        self.max_bytes = max_bytes
        self.download_dir = download_dir.expanduser().resolve() if download_dir else None
        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            try:
                self.download_dir.chmod(0o700)
            except OSError:
                pass

    def fetch(self, source: SourceSpec) -> tuple[str, str, str]:
        opener = urllib.request.build_opener(_AllowlistRedirectHandler(self.allowed_hosts))
        last_error: SourceFetchError | None = None
        for candidate_url in (source.url, *source.fetch_urls):
            parsed = urllib.parse.urlparse(candidate_url)
            host = (parsed.hostname or "").casefold()
            if parsed.scheme != "https" or host not in self.allowed_hosts:
                last_error = SourceFetchError("Source host is not in the explicit HTTPS allowlist.")
                continue
            request = urllib.request.Request(
                candidate_url,
                headers={
                    "User-Agent": "helpme.green/0.2 source-catalog fetcher",
                    "Accept": "text/html, text/plain, application/json;q=0.8, */*;q=0.1",
                },
            )
            for attempt in range(3):
                try:
                    with opener.open(request, timeout=25) as response:
                        data = response.read(self.max_bytes + 1)
                        content_type = response.headers.get_content_type()
                except (OSError, urllib.error.URLError):
                    last_error = SourceFetchError("Source fetch failed safely.")
                    if attempt < 2:
                        time.sleep(0.4)
                        continue
                    break
                try:
                    if len(data) > self.max_bytes:
                        raise SourceFetchError("Source exceeds the configured fetch limit.")
                    text, extracted_type = _extract_content(data, content_type, candidate_url)
                    if not text.strip():
                        raise SourceFetchError("Source extraction produced no readable text.")
                    if _is_access_challenge(text):
                        raise SourceFetchError(
                            "Source returned an access challenge instead of its content."
                        )
                except SourceFetchError as exc:
                    last_error = exc
                    if "access challenge" in str(exc) and attempt < 2:
                        time.sleep(0.8)
                        continue
                    break
                if self.download_dir is not None:
                    self._save_download(source, data, content_type, fetched_url=candidate_url)
                fetched_at = datetime.now(UTC).isoformat()
                return text, extracted_type, fetched_at
        raise last_error or SourceFetchError("Source fetch exhausted its retry attempts.")

    def _save_download(
        self, source: SourceSpec, data: bytes, content_type: str, *, fetched_url: str
    ) -> None:
        assert self.download_dir is not None
        digest = hashlib.sha256(data).hexdigest()
        safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", source.source_id).strip("._") or "source"
        normalized_type = content_type.casefold().split(";", 1)[0].strip()
        suffix = {
            "application/pdf": ".pdf",
            "text/html": ".html",
            "application/xhtml+xml": ".html",
            "application/json": ".json",
            "text/csv": ".csv",
            "text/plain": ".txt",
        }.get(normalized_type, ".bin")
        artifact = self.download_dir / f"{safe_id}-{digest[:16]}{suffix}"
        if not artifact.exists():
            artifact.write_bytes(data)
        metadata = artifact.with_suffix(artifact.suffix + ".json")
        if not metadata.exists():
            metadata.write_text(
                json.dumps(
                    {
                        "sourceId": source.source_id,
                        "title": source.title,
                        "url": source.url,
                        "fetchedUrl": fetched_url,
                        "publisher": source.publisher,
                        "contentType": normalized_type,
                        "contentSha256": digest,
                        "downloadedAt": datetime.now(UTC).isoformat(),
                        "note": "Local reference copy; do not commit or redistribute without checking source terms.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: frozenset[str]) -> None:
        self.allowed_hosts = allowed_hosts

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        del fp, code, msg, headers
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or (parsed.hostname or "").casefold() not in self.allowed_hosts:
            raise SourceFetchError("Redirect target is outside the explicit HTTPS allowlist.")
        return urllib.request.Request(newurl, headers=dict(req.headers), method=req.get_method())


class OpenAICompatibleEmbeddingProvider:
    """Optional OpenAI-compatible embedding client, including OpenRouter endpoints."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str,
        tls_verify: bool = True,
        timeout: int = 45,
    ) -> None:
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Embedding endpoint must use HTTP(S) with a hostname.")
        if parsed.scheme == "http" and not _is_loopback_endpoint(endpoint):
            raise ValueError("Non-local embedding endpoints must use HTTPS.")
        if not model.strip() or (not api_key.strip() and not _is_loopback_endpoint(endpoint)):
            raise ValueError("Embedding model and API key are required for external providers.")
        self.endpoint = endpoint.rstrip("/")
        if not self.endpoint.endswith("/embeddings"):
            self.endpoint += "/embeddings"
        self.model = model
        self.api_key = api_key
        self.tls_verify = tls_verify
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "helpme.green/0.2",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        context = None
        if not self.tls_verify:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        try:
            if context is None:
                response_context = urllib.request.urlopen(request, timeout=self.timeout)
            else:
                response_context = urllib.request.urlopen(
                    request, timeout=self.timeout, context=context
                )
            with response_context as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise SourceFetchError("Embedding provider request failed safely.") from exc
        if not isinstance(raw, Mapping) or not isinstance(raw.get("data"), list):
            raise SourceFetchError("Embedding provider returned an invalid response.")
        ordered = sorted(
            (item for item in raw["data"] if isinstance(item, Mapping)),
            key=lambda item: int(item.get("index", 0)),
        )
        vectors: list[list[float]] = []
        for item in ordered:
            value = item.get("embedding")
            if not isinstance(value, list) or any(
                not isinstance(number, (int, float)) for number in value
            ):
                raise SourceFetchError("Embedding provider returned an invalid vector.")
            vectors.append([float(number) for number in value])
        if len(vectors) != len(texts):
            raise SourceFetchError("Embedding provider returned the wrong number of vectors.")
        return vectors


class OpenAICompatibleReranker:
    """Optional second-stage reranker for OpenRouter-compatible /rerank endpoints."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str,
        tls_verify: bool = True,
        timeout: int = 45,
    ) -> None:
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Reranker endpoint must use HTTP(S) with a hostname.")
        if parsed.scheme == "http" and not _is_loopback_endpoint(endpoint):
            raise ValueError("Non-local reranker endpoints must use HTTPS.")
        if not model.strip() or (not api_key.strip() and not _is_loopback_endpoint(endpoint)):
            raise ValueError("Reranker model and API key are required for external providers.")
        self.endpoint = endpoint.rstrip("/")
        if not self.endpoint.endswith("/rerank"):
            self.endpoint += "/rerank"
        self.model = model
        self.api_key = api_key
        self.tls_verify = tls_verify
        self.timeout = timeout

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        if not query.strip() or not documents:
            return []
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "helpme.green/0.2",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(
                {
                    "model": self.model,
                    "query": query,
                    "documents": documents,
                    "top_n": max(1, min(top_n, len(documents))),
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        context = None
        if not self.tls_verify:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        try:
            if context is None:
                response_context = urllib.request.urlopen(request, timeout=self.timeout)
            else:
                response_context = urllib.request.urlopen(
                    request, timeout=self.timeout, context=context
                )
            with response_context as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise SourceFetchError("Reranker request failed safely.") from exc
        if not isinstance(raw, Mapping) or not isinstance(raw.get("results"), list):
            raise SourceFetchError("Reranker returned an invalid response.")
        result: list[tuple[int, float]] = []
        for item in raw["results"]:
            if not isinstance(item, Mapping):
                continue
            try:
                result.append((int(item["index"]), float(item["relevance_score"])))
            except (KeyError, TypeError, ValueError) as exc:
                raise SourceFetchError("Reranker returned an invalid result.") from exc
        return result


def embedding_provider_from_environment() -> EmbeddingProvider | None:
    endpoint = os.environ.get("HELPME_EMBEDDING_BASE_URL", "").strip()
    model = os.environ.get("HELPME_EMBEDDING_MODEL", "").strip()
    api_key = os.environ.get("HELPME_EMBEDDING_API_KEY", "").strip()
    if not endpoint or not model:
        return None
    if not api_key and not _is_loopback_endpoint(endpoint):
        return None
    return OpenAICompatibleEmbeddingProvider(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        tls_verify=os.environ.get("HELPME_EMBEDDING_TLS_VERIFY", "1").casefold()
        not in {"", "0", "false", "no", "off"},
    )


def reranker_from_environment() -> Reranker | None:
    enabled = os.environ.get("HELPME_RERANK_ENABLED", "1").casefold()
    if enabled in {"", "0", "false", "no", "off"}:
        return None
    endpoint = os.environ.get("HELPME_RERANK_BASE_URL", "").strip()
    model = os.environ.get("HELPME_RERANK_MODEL", "").strip()
    api_key = os.environ.get("HELPME_RERANK_API_KEY", "").strip()
    if not endpoint or not model:
        return None
    if not api_key and not _is_loopback_endpoint(endpoint):
        return None
    return OpenAICompatibleReranker(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        tls_verify=os.environ.get("HELPME_RERANK_TLS_VERIFY", "1").casefold()
        not in {"", "0", "false", "no", "off"},
    )


def embed_missing_documents(
    database: KnowledgeDatabase,
    embedding_provider: EmbeddingProvider,
    *,
    embedding_batch_size: int = 32,
) -> int:
    """Repair latest extracted documents even when their source cannot be fetched again."""
    if embedding_batch_size <= 0:
        raise ValueError("Embedding batch size must be positive.")
    embedded_count = 0
    for document_id, source_id in database.documents_missing_embeddings(embedding_provider.model):
        started = datetime.now(UTC).isoformat()
        try:
            pending = database.chunks_missing_embeddings(document_id, embedding_provider.model)
            for offset in range(0, len(pending), embedding_batch_size):
                batch = pending[offset : offset + embedding_batch_size]
                vectors = embedding_provider.embed([text for _, text in batch])
                database.set_chunk_embeddings(
                    [chunk_id for chunk_id, _ in batch], vectors, embedding_provider.model
                )
                embedded_count += len(batch)
        except (OSError, SourceFetchError, ValueError) as exc:
            database.record_run(source_id, "embedding_failed", str(exc), started, _now())
    return embedded_count


def ingest_manifest(
    manifest: SourceManifest,
    database: KnowledgeDatabase,
    *,
    fetcher: OfficialSourceFetcher | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    download_dir: Path | None = None,
    embedding_batch_size: int = 32,
) -> list[IngestResult]:
    if embedding_batch_size <= 0:
        raise ValueError("Embedding batch size must be positive.")
    fetcher = fetcher or OfficialSourceFetcher(
        allowed_hosts=manifest.allowed_hosts,
        download_dir=download_dir,
    )
    results: list[IngestResult] = []
    for source in manifest.sources:
        started = datetime.now(UTC).isoformat()
        try:
            text, content_type, fetched_at = fetcher.fetch(source)
            result = database.ingest_document(
                source,
                text,
                content_type=content_type,
                fetched_at=fetched_at,
            )
            if embedding_provider:
                pending = database.chunks_missing_embeddings(
                    result.document_id, embedding_provider.model
                )
                for offset in range(0, len(pending), embedding_batch_size):
                    batch = pending[offset : offset + embedding_batch_size]
                    vectors = embedding_provider.embed([text for _, text in batch])
                    database.set_chunk_embeddings(
                        [chunk_id for chunk_id, _ in batch], vectors, embedding_provider.model
                    )
            results.append(result)
            database.record_run(
                source.source_id, "ingested", result.content_sha256, started, _now()
            )
        except (OSError, SourceFetchError, ValueError) as exc:
            database.record_run(source.source_id, "failed", str(exc), started, _now())
    if embedding_provider:
        embed_missing_documents(
            database,
            embedding_provider,
            embedding_batch_size=embedding_batch_size,
        )
    return results


def _now() -> str:
    return datetime.now(UTC).isoformat()
