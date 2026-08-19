"""Agentic knowledge fetching: the LLM decides *when* to call this, no vector index involved.

Fetched content is cached on the Source row with a TTL so repeated questions about the same
tutor don't refetch the same URL on every turn.
"""

import asyncio
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
_MAX_REDIRECTS = 5


async def _is_blocked_host(hostname: str) -> bool:
    """Best-effort SSRF guard: block loopback/private/link-local targets.

    A resolução de DNS roda em thread separada (asyncio.to_thread) — socket.getaddrinfo
    é bloqueante e, sem isso, travaria o event loop inteiro durante a resolução.
    """
    try:
        addr_info = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        return True
    for _family, *_rest, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


async def _validate_url(url: str) -> str | None:
    """Retorna uma razão de bloqueio (str) se a URL não deve ser buscada, ou None se ok."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "URL inválida"
    if await _is_blocked_host(parsed.hostname):
        return "host não permitido"
    return None


async def _open_validated_stream(
    client: httpx.AsyncClient, url: str
) -> tuple[httpx.Response | None, str | None]:
    """Segue redirects manualmente, revalidando o SSRF guard em cada hop.

    O cliente é criado com follow_redirects=False: seguir redirects automaticamente sem
    revalidar cada destino permitiria que uma URL pública inicialmente aprovada
    redirecionasse (302) para um host interno/privado e contornasse o guard.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        block_reason = await _validate_url(current_url)
        if block_reason:
            return None, block_reason

        request = client.build_request("GET", current_url)
        response = await client.send(request, stream=True)

        if response.is_redirect:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                return None, "redirecionamento inválido"
            current_url = str(httpx.URL(current_url).join(location))
            continue

        return response, None

    return None, "excesso de redirecionamentos"


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

    try:
        async with httpx.AsyncClient(
            timeout=settings.source_fetch_timeout_seconds, follow_redirects=False
        ) as client:
            response, block_reason = await _open_validated_stream(client, source.url)
            if block_reason:
                return _UNAVAILABLE.format(reason=block_reason)

            assert response is not None
            try:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if content_type and not any(
                    hint in content_type for hint in ("text/", "json", "xml")
                ):
                    return _UNAVAILABLE.format(reason="tipo de conteúdo não suportado")

                chunks: list[bytes] = []
                total = 0
                truncated = False
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= settings.max_source_fetch_bytes:
                        truncated = True
                        break
                raw = b"".join(chunks)[: settings.max_source_fetch_bytes]
            finally:
                await response.aclose()
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
    if truncated:
        text += f"\n\n[conteúdo truncado em {settings.max_source_fetch_bytes} bytes]"

    source.cached_content = text
    source.cached_at = datetime.now(UTC)
    session.add(source)
    session.commit()
    return text
