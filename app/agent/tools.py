"""Knowledge tools exposed to the tutor agent.

These implement the "agentic knowledge" strategy required by the challenge: the LLM
decides, via tool calling, whether and when it needs to pull in a source's content.
There is no vector index / embedding step anywhere in this flow.
"""

from pydantic_ai import Agent, RunContext

from app.agent.source_fetcher import fetch_and_cache


def register_tools(agent: Agent) -> None:
    @agent.tool
    async def list_sources(ctx: RunContext) -> str:
        """Lista as fontes de conhecimento cadastradas para este tutor (id e rótulo).

        Use esta ferramenta primeiro quando não souber quais fontes estão disponíveis.
        """
        sources = ctx.deps.tutor.sources
        if not sources:
            return "Nenhuma fonte de conhecimento cadastrada para este tutor."
        return "\n".join(f"id={s.id} label={s.label!r}" for s in sources)

    @agent.tool
    async def fetch_source(ctx: RunContext, source_id: str) -> str:
        """Busca o conteúdo textual de uma fonte de conhecimento pelo seu id.

        Use list_sources antes se não tiver certeza do id. O conteúdo retornado pode
        estar truncado; se não for suficiente para responder, diga isso ao usuário
        em vez de inventar informação.
        """
        source = next((s for s in ctx.deps.tutor.sources if s.id == source_id), None)
        if not source:
            return f"[fonte '{source_id}' não encontrada para este tutor]"
        return await fetch_and_cache(ctx.deps.session, source, ctx.deps.settings)
