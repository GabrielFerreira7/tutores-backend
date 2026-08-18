from fastapi import APIRouter, Depends, Request
from pydantic_ai.models import Model
from sqlmodel import Session

from app.api.public.deps import get_llm_model
from app.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db import get_session
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api/public", tags=["public:chat"])

_CHAT_RATE_LIMIT = get_settings().chat_rate_limit


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(_CHAT_RATE_LIMIT)
async def post_chat(
    request: Request,
    data: ChatRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    model: Model | str = Depends(get_llm_model),
):
    return await chat_service.handle_chat_request(session, data, settings, model=model)


@router.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str,
    tutor_id: str,
    embed_token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    messages = chat_service.get_history(
        session, tutor_id, embed_token, session_id, settings.chat_history_limit
    )
    return ChatHistoryResponse(session_id=session_id, messages=messages)
