from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.admin.deps import require_admin
from app.config import Settings, get_settings
from app.db import get_session
from app.schemas.tutor import EmbedSnippetResponse, TutorCreate, TutorRead, TutorUpdate
from app.services import tutor_service

router = APIRouter(
    prefix="/api/admin/tutors", tags=["admin:tutors"], dependencies=[Depends(require_admin)]
)


@router.post("", response_model=TutorRead, status_code=201)
def create_tutor(data: TutorCreate, session: Session = Depends(get_session)):
    return tutor_service.create_tutor(session, data)


@router.get("", response_model=list[TutorRead])
def list_tutors(status: str | None = None, session: Session = Depends(get_session)):
    return tutor_service.list_tutors(session, status_filter=status)


@router.get("/{tutor_id}", response_model=TutorRead)
def get_tutor(tutor_id: str, session: Session = Depends(get_session)):
    return tutor_service.get_tutor(session, tutor_id)


@router.patch("/{tutor_id}", response_model=TutorRead)
def update_tutor(tutor_id: str, data: TutorUpdate, session: Session = Depends(get_session)):
    return tutor_service.update_tutor(session, tutor_id, data)


@router.post("/{tutor_id}/deactivate", response_model=TutorRead)
def deactivate_tutor(tutor_id: str, session: Session = Depends(get_session)):
    return tutor_service.deactivate_tutor(session, tutor_id)


@router.post("/{tutor_id}/rotate-embed-token", response_model=TutorRead)
def rotate_embed_token(tutor_id: str, session: Session = Depends(get_session)):
    return tutor_service.regenerate_embed_token(session, tutor_id)


@router.get("/{tutor_id}/embed-snippet", response_model=EmbedSnippetResponse)
def get_embed_snippet(
    tutor_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    tutor = tutor_service.get_tutor(session, tutor_id)
    embed_url = f"{settings.frontend_base_url}/widget?tutorId={tutor.id}&token={tutor.embed_token}"
    snippet = (
        f'<iframe src="{embed_url}" width="380" height="560" '
        'style="border:1px solid #e2e2e2;border-radius:12px" '
        'title="Chat do tutor"></iframe>'
    )
    return EmbedSnippetResponse(tutor_id=tutor.id, embed_url=embed_url, iframe_snippet=snippet)
