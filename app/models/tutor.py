import secrets
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.source import Source


def _new_id() -> str:
    return uuid.uuid4().hex


def _new_embed_token() -> str:
    return secrets.token_urlsafe(24)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TutorStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"


class Tutor(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    title: str
    short_description: str = ""
    status: str = Field(default=TutorStatus.ACTIVE, index=True)
    system_instructions: str
    embed_token: str = Field(default_factory=_new_embed_token, unique=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    sources: list["Source"] = Relationship(
        back_populates="tutor", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    chat_sessions: list["ChatSession"] = Relationship(back_populates="tutor")
