from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session

from app.api.admin.deps import require_admin
from app.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db import get_session
from app.schemas.tutor import EmbedSnippetResponse, TutorCreate, TutorRead, TutorUpdate
from app.services import tutor_service

router = APIRouter(
    prefix="/api/admin/tutors", tags=["admin:tutors"], dependencies=[Depends(require_admin)]
)

_ADMIN_RATE_LIMIT = get_settings().admin_rate_limit


@router.post("", response_model=TutorRead, status_code=201)
@limiter.limit(_ADMIN_RATE_LIMIT)
def create_tutor(
    request: Request,
    response: Response,
    data: TutorCreate,
    session: Session = Depends(get_session),
):
    return tutor_service.create_tutor(session, data)


@router.get("", response_model=list[TutorRead])
@limiter.limit(_ADMIN_RATE_LIMIT)
def list_tutors(
    request: Request,
    response: Response,
    status: str | None = None,
    session: Session = Depends(get_session),
):
    return tutor_service.list_tutors(session, status_filter=status)


@router.get("/{tutor_id}", response_model=TutorRead)
@limiter.limit(_ADMIN_RATE_LIMIT)
def get_tutor(
    request: Request, response: Response, tutor_id: str, session: Session = Depends(get_session)
):
    return tutor_service.get_tutor(session, tutor_id)


@router.patch("/{tutor_id}", response_model=TutorRead)
@limiter.limit(_ADMIN_RATE_LIMIT)
def update_tutor(
    request: Request,
    response: Response,
    tutor_id: str,
    data: TutorUpdate,
    session: Session = Depends(get_session),
):
    return tutor_service.update_tutor(session, tutor_id, data)


@router.post("/{tutor_id}/deactivate", response_model=TutorRead)
@limiter.limit(_ADMIN_RATE_LIMIT)
def deactivate_tutor(
    request: Request, response: Response, tutor_id: str, session: Session = Depends(get_session)
):
    return tutor_service.deactivate_tutor(session, tutor_id)


@router.post("/{tutor_id}/rotate-embed-token", response_model=TutorRead)
@limiter.limit(_ADMIN_RATE_LIMIT)
def rotate_embed_token(
    request: Request, response: Response, tutor_id: str, session: Session = Depends(get_session)
):
    return tutor_service.regenerate_embed_token(session, tutor_id)


@router.get("/{tutor_id}/embed-snippet", response_model=EmbedSnippetResponse)
@limiter.limit(_ADMIN_RATE_LIMIT)
def get_embed_snippet(
    request: Request,
    response: Response,
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
