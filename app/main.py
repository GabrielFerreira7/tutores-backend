import logging

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.admin.tutors import router as admin_tutors_router
from app.api.public.chat import router as public_chat_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.db import create_db_and_tables

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plataforma de Tutores Personalizados — API")

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc: RateLimitExceeded):
    response = _rate_limit_exceeded_handler(request, exc)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Muitas requisições. Tente novamente em instantes."},
        headers=dict(response.headers),
    )


app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(admin_tutors_router)
app.include_router(public_chat_router)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    logger.info("startup_complete")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
