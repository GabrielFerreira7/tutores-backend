import hmac

from fastapi import Header

from app.config import get_settings
from app.core.errors import UnauthorizedError


def require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_api_key or not hmac.compare_digest(x_admin_api_key, settings.admin_api_key):
        raise UnauthorizedError("Chave de administrador ausente ou inválida.")
