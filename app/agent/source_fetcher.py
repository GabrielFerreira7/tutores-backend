"""Agentic knowledge fetching: the LLM decides *when* to call this, no vector index involved.

Fetched content is cached on the Source row with a TTL so repeated questions about the same
tutor don't refetch the same URL on every turn.
"""

import ipaddress
import logging
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlmodel import Session

from app.config import Settings
from app.models.source import Source

logger = logging.getLogger(__name__)

_UNAVAILABLE = "[fonte indisponível: {reason}]"


def _is_blocked_host(hostname: str) -> bool:
    """Best-effort SSRF guard: block loopback/private/link-local targets."""
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True
    for _family, *_rest, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


def _is_fresh(source: Source, ttl_seconds: int) -> bool:
    if not source.cached_content or not source.cached_at:
        return False
    cached_at = source.cached_at
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=UTC)
    age = (datetime.now(UTC) - cached_at).total_seconds()
    return age < ttl_seconds


async def fetch_and_cache(session: Session, source: Source, settings: Settings) -> str:
    """Return the (possibly cached) textual content of a knowledge source.

    Never raises: any failure is turned into a short sentinel message so the agent can
    tell the end user the source is unavailable instead of crashing the whole turn.
    """
    if _is_fresh(source, settings.source_cache_ttl_seconds):
        return source.cached_content  # type: ignore[return-value]

    parsed = urlparse(source.url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return _UNAVAILABLE.format(reason="URL inválida")

    if _is_blocked_host(parsed.hostname):
        return _UNAVAILABLE.format(reason="host não permitido")

    try:
        async with httpx.AsyncClient(
            timeout=settings.source_fetch_timeout_seconds, follow_redirects=True
        ) as client:
            async with client.stream("GET", source.url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if content_type and not any(
                    hint in content_type for hint in ("text/", "json", "xml")
                ):
                    return _UNAVAILABLE.format(reason="tipo de conteúdo não suportado")

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= settings.max_source_fetch_bytes:
                        break
                raw = b"".join(chunks)[: settings.max_source_fetch_bytes]
    except httpx.TimeoutException:
        logger.warning("source_fetch_timeout", extra={"source_id": source.id, "url": source.url})
        return _UNAVAILABLE.format(reason="tempo de resposta excedido")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "source_fetch_http_error",
            extra={"source_id": source.id, "url": source.url, "status": exc.response.status_code},
        )
        return _UNAVAILABLE.format(reason=f"HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        logger.warning(
            "source_fetch_error",
            extra={"source_id": source.id, "url": source.url, "error": str(exc)},
        )
        return _UNAVAILABLE.format(reason="erro de rede")

    text = raw.decode("utf-8", errors="replace")
    source.cached_content = text
    source.cached_at = datetime.now(UTC)
    session.add(source)
    session.commit()
    return text
