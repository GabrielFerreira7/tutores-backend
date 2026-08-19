import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model
from sqlmodel import Session

from app.agent.tools import register_tools
from app.config import Settings
from app.core.errors import ServiceUnavailableError
from app.models.chat import ChatMessage
from app.models.tutor import Tutor

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = 0.2

GLOBAL_GUARDRAILS = (
    "Você é um tutor virtual incorporado como um widget de chat em um site "
    "por meio de um iframe. Seja objetivo, educado e responda no idioma do usuário. "
    "Se a resposta depender de conhecimento específico do tutor, use as ferramentas "
    "list_sources e fetch_source para consultar as fontes cadastradas antes de responder. "
    "Se, mesmo após consultar as fontes disponíveis, você não souber a resposta, diga "
    "isso claramente em vez de inventar uma informação."
)


@dataclass
class TutorAgentDeps:
    session: Session
    tutor: Tutor
    settings: Settings


@lru_cache
def get_agent() -> Agent:
    agent = Agent(deps_type=TutorAgentDeps, output_type=str, system_prompt=GLOBAL_GUARDRAILS)
    register_tools(agent)
    return agent


def _to_message_history(history: list[ChatMessage]) -> list[ModelRequest | ModelResponse]:
    """Reconstrói o histórico como mensagens estruturadas do pydantic-ai (message_history),
    em vez de um transcript de texto solto prefixado ao prompt.

    Papéis viram estruturais e aplicados pelo próprio provedor — o usuário não consegue
    forjar uma fala do tutor digitando "Tutor: ..." no meio da mensagem, como acontecia
    com o transcript em texto puro.
    """
    messages: list[ModelRequest | ModelResponse] = []
    for msg in history:
        if msg.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=msg.content)]))
    return messages


async def run_tutor_turn(
    session: Session,
    tutor: Tutor,
    history: list[ChatMessage],
    message: str,
    settings: Settings,
    model: Model | str | None = None,
) -> str:
    """Run one conversation turn for a tutor and return the assistant's reply text.

    Faz um retry único e simples em caso de falha (timeout, chave inválida, sem quota,
    erro de rede) antes de desistir — muitas falhas de provedor de LLM são transitórias.
    Se as duas tentativas falharem, a falha vira ServiceUnavailableError (503 amigável)
    em vez de vazar como 500 cru — ver app/core/errors.py.
    """
    agent = get_agent()
    deps = TutorAgentDeps(session=session, tutor=tutor, settings=settings)
    message_history = _to_message_history(history)
    resolved_model = model or settings.llm_model

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            result = await asyncio.wait_for(
                agent.run(
                    user_prompt=message,
                    instructions=tutor.system_instructions,
                    deps=deps,
                    model=resolved_model,
                    message_history=message_history,
                ),
                timeout=settings.llm_timeout_seconds,
            )
            return result.output
        except Exception as exc:
            # Fronteira intencional: qualquer falha do provedor vira 503 amigável.
            last_error = exc
            if attempt < _MAX_ATTEMPTS:
                logger.warning("llm_turn_retry", extra={"tutor_id": tutor.id, "attempt": attempt})
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS)

    logger.exception("llm_turn_failed", extra={"tutor_id": tutor.id}, exc_info=last_error)
    raise ServiceUnavailableError() from last_error
