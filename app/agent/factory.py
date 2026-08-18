from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.models import Model
from sqlmodel import Session

from app.agent.tools import register_tools
from app.config import Settings
from app.models.chat import ChatMessage
from app.models.tutor import Tutor

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


def _render_transcript(history: list[ChatMessage]) -> str:
    if not history:
        return ""
    lines = []
    for msg in history:
        speaker = "Usuário" if msg.role == "user" else "Tutor"
        lines.append(f"{speaker}: {msg.content}")
    return "\n".join(lines)


async def run_tutor_turn(
    session: Session,
    tutor: Tutor,
    history: list[ChatMessage],
    message: str,
    settings: Settings,
    model: Model | str | None = None,
) -> str:
    """Run one conversation turn for a tutor and return the assistant's reply text.

    Conversation history is rendered as a plain transcript prefixed to the prompt
    rather than reconstructed as internal pydantic-ai message objects — a deliberate
    simplification for the MVP that avoids coupling to the library's internal message
    schema (see README "Decisões de arquitetura").
    """
    agent = get_agent()
    transcript = _render_transcript(history)
    user_prompt = f"{transcript}\n\nUsuário: {message}".strip() if transcript else message

    deps = TutorAgentDeps(session=session, tutor=tutor, settings=settings)
    result = await agent.run(
        user_prompt=user_prompt,
        instructions=tutor.system_instructions,
        deps=deps,
        model=model or settings.llm_model,
    )
    return result.output
