from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    url: HttpUrl


class SourceRead(BaseModel):
    id: str
    label: str
    url: str


class TutorCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    short_description: str = Field(default="", max_length=500)
    system_instructions: str = Field(min_length=1, max_length=8000)
    sources: list[SourceCreate] = Field(default_factory=list)


class TutorUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    short_description: str | None = Field(default=None, max_length=500)
    system_instructions: str | None = Field(default=None, min_length=1, max_length=8000)
    status: Literal["active", "inactive"] | None = None
    sources: list[SourceCreate] | None = None


class TutorRead(BaseModel):
    id: str
    title: str
    short_description: str
    status: str
    system_instructions: str
    embed_token: str
    created_at: datetime
    updated_at: datetime
    sources: list[SourceRead]


class EmbedSnippetResponse(BaseModel):
    tutor_id: str
    embed_url: str
    iframe_snippet: str


class PublicTutorInfo(BaseModel):
    """Subconjunto seguro de campos do tutor exposto ao widget público — sem
    system_instructions nem embed_token, só o necessário para o cabeçalho do chat."""

    id: str
    title: str
    short_description: str
