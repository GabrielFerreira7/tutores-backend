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
def client_fixture(session: Session):
    def get_session_override():
        return session

    def get_llm_model_override():
        return TestModel(custom_output_text="Resposta de teste do tutor.")

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_llm_model] = get_llm_model_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="admin_headers")
def admin_headers_fixture():
    return {"X-Admin-Api-Key": get_settings().admin_api_key}
