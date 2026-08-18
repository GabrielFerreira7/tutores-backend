from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.errors import ForbiddenError, NotFoundError
from app.models.source import Source
from app.models.tutor import Tutor, TutorStatus, _new_embed_token
from app.schemas.tutor import TutorCreate, TutorUpdate


def create_tutor(session: Session, data: TutorCreate) -> Tutor:
    tutor = Tutor(
        title=data.title,
        short_description=data.short_description,
        system_instructions=data.system_instructions,
    )
    tutor.sources = [Source(label=s.label, url=str(s.url)) for s in data.sources]
    session.add(tutor)
    session.commit()
    session.refresh(tutor)
    return tutor


def list_tutors(session: Session, status_filter: str | None = None) -> list[Tutor]:
    query = select(Tutor).order_by(Tutor.created_at.desc())
    if status_filter:
        query = query.where(Tutor.status == status_filter)
    return list(session.exec(query))


def get_tutor(session: Session, tutor_id: str) -> Tutor:
    tutor = session.get(Tutor, tutor_id)
    if not tutor:
        raise NotFoundError("Tutor não encontrado.")
    return tutor


def update_tutor(session: Session, tutor_id: str, data: TutorUpdate) -> Tutor:
    tutor = get_tutor(session, tutor_id)

    if data.title is not None:
        tutor.title = data.title
    if data.short_description is not None:
        tutor.short_description = data.short_description
    if data.system_instructions is not None:
        tutor.system_instructions = data.system_instructions
    if data.status is not None:
        if data.status not in (TutorStatus.ACTIVE, TutorStatus.INACTIVE):
            raise ValueError("status inválido")
        tutor.status = data.status
    if data.sources is not None:
        for source in list(tutor.sources):
            session.delete(source)
        tutor.sources = [Source(label=s.label, url=str(s.url)) for s in data.sources]

    tutor.updated_at = datetime.now(UTC)
    session.add(tutor)
    session.commit()
    session.refresh(tutor)
    return tutor


def deactivate_tutor(session: Session, tutor_id: str) -> Tutor:
    return update_tutor(session, tutor_id, TutorUpdate(status=TutorStatus.INACTIVE))


def regenerate_embed_token(session: Session, tutor_id: str) -> Tutor:
    tutor = get_tutor(session, tutor_id)
    tutor.embed_token = _new_embed_token()
    tutor.updated_at = datetime.now(UTC)
    session.add(tutor)
    session.commit()
    session.refresh(tutor)
    return tutor


def get_tutor_for_embed(session: Session, tutor_id: str, embed_token: str) -> Tutor:
    tutor = session.get(Tutor, tutor_id)
    if not tutor:
        raise NotFoundError("Tutor não encontrado.")
    if tutor.embed_token != embed_token:
        raise ForbiddenError("Token de embed inválido para este tutor.")
    return tutor
