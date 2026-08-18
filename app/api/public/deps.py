from fastapi import Depends
from pydantic_ai.models import Model

from app.config import Settings, get_settings


def get_llm_model(settings: Settings = Depends(get_settings)) -> Model | str:
    """Indirection point so tests can override the model with pydantic-ai's TestModel
    instead of hitting a real provider (see tests/conftest.py)."""
    return settings.llm_model
