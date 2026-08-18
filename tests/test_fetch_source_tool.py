import httpx
import respx
from sqlmodel import Session

from app.agent.source_fetcher import fetch_and_cache
from app.config import Settings
from app.models.source import Source


def _settings(**overrides) -> Settings:
    base = {
        "max_source_fetch_bytes": 51_200,
        "source_fetch_timeout_seconds": 5,
        "source_cache_ttl_seconds": 3600,
    }
    base.update(overrides)
    return Settings(**base)


@respx.mock
async def test_fetch_and_cache_success(session: Session):
    respx.get("https://example.com/doc.txt").mock(
        return_value=httpx.Response(
            200, text="conteudo de teste", headers={"content-type": "text/plain"}
        )
    )
    source = Source(tutor_id="tutor-1", label="Doc", url="https://example.com/doc.txt")
    session.add(source)
    session.commit()

    content = await fetch_and_cache(session, source, _settings())

    assert content == "conteudo de teste"
    assert source.cached_content == "conteudo de teste"
    assert source.cached_at is not None


@respx.mock
async def test_fetch_and_cache_uses_fresh_cache_without_new_request(session: Session):
    route = respx.get("https://example.com/doc.txt").mock(
        return_value=httpx.Response(200, text="novo conteudo")
    )
    from datetime import UTC, datetime

    source = Source(
        tutor_id="tutor-1",
        label="Doc",
        url="https://example.com/doc.txt",
        cached_content="conteudo em cache",
        cached_at=datetime.now(UTC),
    )
    session.add(source)
    session.commit()

    content = await fetch_and_cache(session, source, _settings())

    assert content == "conteudo em cache"
    assert route.call_count == 0


@respx.mock
async def test_fetch_and_cache_timeout_returns_sentinel(session: Session):
    respx.get("https://example.com/slow.txt").mock(side_effect=httpx.TimeoutException("boom"))
    source = Source(tutor_id="tutor-1", label="Lento", url="https://example.com/slow.txt")
    session.add(source)
    session.commit()

    content = await fetch_and_cache(session, source, _settings())

    assert "indisponível" in content


async def test_fetch_and_cache_blocks_private_host(session: Session):
    source = Source(tutor_id="tutor-1", label="Interno", url="http://127.0.0.1:9999/segredo")
    session.add(source)
    session.commit()

    content = await fetch_and_cache(session, source, _settings())

    assert "não permitido" in content
