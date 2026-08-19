import asyncio

import pytest
from sqlmodel import Session

from app.agent import factory
from app.config import Settings
from app.core.errors import ServiceUnavailableError
from app.schemas.tutor import TutorCreate
from app.services import tutor_service


def _tutor(session: Session):
    return tutor_service.create_tutor(
        session,
        TutorCreate(title="Tutor de teste", system_instructions="Seja breve."),
    )


async def test_run_tutor_turn_maps_provider_error_to_service_unavailable(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    class _BoomAgent:
        async def run(self, **kwargs):
            raise RuntimeError("provedor de LLM explodiu")

    monkeypatch.setattr(factory, "get_agent", lambda: _BoomAgent())
    tutor = _tutor(session)

    with pytest.raises(ServiceUnavailableError):
        await factory.run_tutor_turn(session, tutor, [], "oi", Settings(llm_timeout_seconds=5))


async def test_run_tutor_turn_maps_timeout_to_service_unavailable(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    class _SlowAgent:
        async def run(self, **kwargs):
            await asyncio.sleep(10)

    monkeypatch.setattr(factory, "get_agent", lambda: _SlowAgent())
    tutor = _tutor(session)

    with pytest.raises(ServiceUnavailableError):
        await factory.run_tutor_turn(session, tutor, [], "oi", Settings(llm_timeout_seconds=0.05))
