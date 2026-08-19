from sqlmodel import Session, select

from app.models.chat import ChatMessage
from app.schemas.tutor import TutorCreate
from app.services import tutor_service
from app.services.chat_service import _append_message, _get_or_create_session, _trim_history


def _tutor(session: Session):
    return tutor_service.create_tutor(
        session, TutorCreate(title="Tutor de teste", system_instructions="Seja breve.")
    )


def test_trim_history_keeps_only_the_most_recent_messages(session: Session):
    tutor = _tutor(session)
    chat_session = _get_or_create_session(session, tutor.id, None)

    for i in range(10):
        _append_message(session, chat_session, "user", f"pergunta {i}")
        _append_message(session, chat_session, "assistant", f"resposta {i}")

    _trim_history(session, chat_session.id, keep=4)

    remaining = list(
        session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.id)
        )
    )
    assert len(remaining) == 4
    assert [m.content for m in remaining] == [
        "pergunta 8",
        "resposta 8",
        "pergunta 9",
        "resposta 9",
    ]


def test_trim_history_noop_when_under_the_limit(session: Session):
    tutor = _tutor(session)
    chat_session = _get_or_create_session(session, tutor.id, None)
    _append_message(session, chat_session, "user", "oi")

    _trim_history(session, chat_session.id, keep=20)

    remaining = list(
        session.exec(select(ChatMessage).where(ChatMessage.session_id == chat_session.id))
    )
    assert len(remaining) == 1
