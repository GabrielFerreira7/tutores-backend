from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    tutor_id: str
    embed_token: str
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class ChatMessageRead(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageRead]
