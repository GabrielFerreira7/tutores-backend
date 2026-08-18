from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic_ai.models import Model
from sqlmodel import Session

from app.api.public.deps import get_llm_model
from app.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db import get_session
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.schemas.tutor import PublicTutorInfo
from app.services import chat_service, tutor_service

router = APIRouter(prefix="/api/public", tags=["public:chat"])

_CHAT_RATE_LIMIT = get_settings().chat_rate_limit


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(_CHAT_RATE_LIMIT)
async def post_chat(
    request: Request,
    response: Response,
    data: ChatRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    model: Model | str = Depends(get_llm_model),
):
    return await chat_service.handle_chat_request(session, data, settings, model=model)


@router.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
@limiter.limit(_CHAT_RATE_LIMIT)
def get_chat_history(
    request: Request,
    response: Response,
    session_id: str,
    tutor_id: str,
    x_embed_token: str = Header(alias="X-Embed-Token"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    messages = chat_service.get_history(
        session, tutor_id, x_embed_token, session_id, settings.chat_history_limit
    )
    return ChatHistoryResponse(session_id=session_id, messages=messages)


@router.get("/tutors/{tutor_id}", response_model=PublicTutorInfo)
@limiter.limit(_CHAT_RATE_LIMIT)
def get_public_tutor_info(
    request: Request,
    response: Response,
    tutor_id: str,
    x_embed_token: str = Header(alias="X-Embed-Token"),
    session: Session = Depends(get_session),
):
    """Info mínima e segura (título + descrição curta) para o widget mostrar quem é
    o tutor — nunca inclui system_instructions nem o embed_token."""
    tutor = tutor_service.get_tutor_for_embed(session, tutor_id, x_embed_token)
    return PublicTutorInfo(
        id=tutor.id, title=tutor.title, short_description=tutor.short_description
    )
