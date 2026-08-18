import pytest
from sqlmodel import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models.tutor import TutorStatus
from app.schemas.tutor import SourceCreate, TutorCreate, TutorUpdate
from app.services import tutor_service


def _tutor_payload(**overrides) -> TutorCreate:
    data = {
        "title": "Tutor de Matemática",
        "short_description": "Ajuda com álgebra básica",
        "system_instructions": "Seja didático e use exemplos simples.",
        "sources": [SourceCreate(label="Apostila", url="https://example.com/apostila.txt")],
    }
    data.update(overrides)
    return TutorCreate(**data)


def test_create_and_get_tutor(session: Session):
    tutor = tutor_service.create_tutor(session, _tutor_payload())

    assert tutor.id
    assert tutor.status == TutorStatus.ACTIVE
    assert len(tutor.sources) == 1
    assert tutor.embed_token

    fetched = tutor_service.get_tutor(session, tutor.id)
    assert fetched.title == "Tutor de Matemática"


def test_get_tutor_not_found_raises(session: Session):
    with pytest.raises(NotFoundError):
        tutor_service.get_tutor(session, "does-not-exist")


def test_list_tutors_filters_by_status(session: Session):
    active = tutor_service.create_tutor(session, _tutor_payload(title="Ativo"))
    inactive = tutor_service.create_tutor(session, _tutor_payload(title="Inativo"))
    tutor_service.deactivate_tutor(session, inactive.id)

    active_only = tutor_service.list_tutors(session, status_filter=TutorStatus.ACTIVE)

    assert [t.id for t in active_only] == [active.id]


def test_update_tutor_replaces_sources(session: Session):
    tutor = tutor_service.create_tutor(session, _tutor_payload())

    updated = tutor_service.update_tutor(
        session,
        tutor.id,
        TutorUpdate(sources=[SourceCreate(label="Nova fonte", url="https://example.com/nova.txt")]),
    )

    assert len(updated.sources) == 1
    assert updated.sources[0].label == "Nova fonte"


def test_deactivate_tutor(session: Session):
    tutor = tutor_service.create_tutor(session, _tutor_payload())

    deactivated = tutor_service.deactivate_tutor(session, tutor.id)

    assert deactivated.status == TutorStatus.INACTIVE


def test_get_tutor_for_embed_wrong_token_raises_forbidden(session: Session):
    tutor = tutor_service.create_tutor(session, _tutor_payload())

    with pytest.raises(ForbiddenError):
        tutor_service.get_tutor_for_embed(session, tutor.id, "token-errado")


def test_regenerate_embed_token_changes_value(session: Session):
    tutor = tutor_service.create_tutor(session, _tutor_payload())
    old_token = tutor.embed_token

    rotated = tutor_service.regenerate_embed_token(session, tutor.id)

    assert rotated.embed_token != old_token
