import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.test import TestModel
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api.public.deps import get_llm_model
from app.config import get_settings
from app.db import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, monkeypatch: pytest.MonkeyPatch):
    def get_session_override():
        return session

    def get_llm_model_override():
        return TestModel(custom_output_text="Resposta de teste do tutor.")

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_llm_model] = get_llm_model_override

    # O lifespan do FastAPI chama create_db_and_tables(), que usa o `engine` em nível
    # de módulo de app.db (não a dependência get_session, que já foi sobrescrita acima).
    # Sem isto, o startup do TestClient criaria tabelas no banco real configurado via
    # .env do desenvolvedor em vez do engine SQLite em memória deste fixture.
    monkeypatch.setattr("app.db.engine", session.get_bind())

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="admin_headers")
def admin_headers_fixture():
    return {"X-Admin-Api-Key": get_settings().admin_api_key}
