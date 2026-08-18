from datetime import UTC, datetime

from pydantic_ai.models import Model
from sqlmodel import Session, select

from app.agent.factory import run_tutor_turn
from app.config import Settings
from app.core.errors import NotFoundError, TutorUnavailableError
from app.models.chat import ChatMessage, ChatSession
from app.models.tutor import TutorStatus
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.tutor_service import get_tutor_for_embed


def _get_or_create_session(session: Session, tutor_id: str, session_id: str | None) -> ChatSession:
    if session_id:
        chat_session = session.get(ChatSession, session_id)
        if chat_session and chat_session.tutor_id == tutor_id:
            return chat_session
        raise NotFoundError("Sessão de conversa não encontrada para este tutor.")

    chat_session = ChatSession(tutor_id=tutor_id)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def _recent_history(session: Session, chat_session_id: str, limit: int) -> list[ChatMessage]:
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_session_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    messages = list(session.exec(query))
    messages.reverse()
    return messages


def _append_message(session: Session, chat_session: ChatSession, role: str, content: str) -> None:
    session.add(ChatMessage(session_id=chat_session.id, role=role, content=content))
    chat_session.last_active_at = datetime.now(UTC)
    session.add(chat_session)
    session.commit()


def _trim_history(session: Session, chat_session_id: str, keep: int) -> None:
    """Mantém só as últimas `keep` mensagens por sessão — sem isso a tabela de mensagens
    cresce sem limite, já que _recent_history só limita o que é *lido*, não o que é
    persistido."""
    if keep <= 0:
        return
    recent_ids = list(
        session.exec(
            select(ChatMessage.id)
            .where(ChatMessage.session_id == chat_session_id)
            .order_by(ChatMessage.id.desc())
            .limit(keep)
        )
    )
    if not recent_ids:
        return
    stale = session.exec(
        select(ChatMessage).where(
            ChatMessage.session_id == chat_session_id,
            ChatMessage.id.not_in(recent_ids),
        )
    )
    deleted = False
    for message in stale:
        session.delete(message)
        deleted = True
    if deleted:
        session.commit()


async def handle_chat_request(
    session: Session,
    data: ChatRequest,
    settings: Settings,
    model: Model | str | None = None,
) -> ChatResponse:
    tutor = get_tutor_for_embed(session, data.tutor_id, data.embed_token)
    if tutor.status != TutorStatus.ACTIVE:
        raise TutorUnavailableError()

    chat_session = _get_or_create_session(session, tutor.id, data.session_id)
    history = _recent_history(session, chat_session.id, settings.chat_history_limit)

    # A mensagem do usuário é persistida antes de chamar o LLM: se o turno falhar
    # (provedor fora do ar, timeout), a pergunta ainda fica registrada para depuração,
    # em vez de desaparecer junto com o erro.
    _append_message(session, chat_session, "user", data.message)

    reply = await run_tutor_turn(session, tutor, history, data.message, settings, model=model)

    _append_message(session, chat_session, "assistant", reply)
    _trim_history(session, chat_session.id, settings.chat_history_limit)

    return ChatResponse(session_id=chat_session.id, reply=reply)


def get_history(
    session: Session, tutor_id: str, embed_token: str, chat_session_id: str, limit: int
):
    get_tutor_for_embed(session, tutor_id, embed_token)
    chat_session = session.get(ChatSession, chat_session_id)
    if not chat_session or chat_session.tutor_id != tutor_id:
        raise NotFoundError("Sessão de conversa não encontrada para este tutor.")
    return _recent_history(session, chat_session_id, limit)
