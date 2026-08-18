import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.tutor import Tutor


def _new_id() -> str:
    return uuid.uuid4().hex


class Source(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    tutor_id: str = Field(foreign_key="tutor.id", index=True)
    label: str
    url: str

    # Simple fetch cache (agentic knowledge strategy, not a vector index).
    cached_content: str | None = None
    cached_at: datetime | None = None

    tutor: Optional["Tutor"] = Relationship(back_populates="sources")
