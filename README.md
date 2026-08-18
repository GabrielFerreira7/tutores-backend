# Tutores — Backend

API do MVP da **Plataforma de Tutores Personalizados** (desafio técnico DOT Digital Group).
FastAPI + Pydantic AI + SQLModel/SQLite. Ver o repositório irmão `../frontend` para o
dashboard admin e o widget de embed.

> **Aviso de processo**: este código foi construído com o auxílio de um agente de codificação
> (Claude Code) sob supervisão humana, conforme exigido pelo enunciado do desafio — não foi
> escrito manualmente arquivo a arquivo sem esse fluxo assistido.

## Como rodar localmente

### Opção 1 — Python direto

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
cp .env.example .env          # edite ADMIN_API_KEY e a chave do provedor de LLM

uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000` (docs interativas em `/docs`).

### Opção 2 — Docker

```bash
cp .env.example .env
docker compose up --build
```

### Testes e lint

```bash
pytest
ruff check app tests
```

Os testes **não fazem chamadas reais a nenhum provedor de LLM** — a rota de chat usa
`pydantic_ai.models.test.TestModel` injetado via *dependency override* (`tests/conftest.py`),
e o fetch de fontes é mockado com `respx`. Isso mantém a suíte determinística, rápida e sem custo.

## Variáveis de ambiente

Veja `.env.example` para a lista completa e comentada. Principais:

| Variável | Uso |
|---|---|
| `ADMIN_API_KEY` | Chave exigida no header `X-Admin-Api-Key` para todas as rotas `/api/admin/*` |
| `DATABASE_URL` | String de conexão SQLAlchemy (default: SQLite local em `./data/tutors.db`) |
| `LLM_MODEL` | Modelo no formato `provider:model` do pydantic-ai (ex.: `anthropic:claude-haiku-4-5-20251001`) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Lida diretamente pelo SDK do provedor (nunca pela aplicação) |
| `MAX_SOURCE_FETCH_BYTES`, `SOURCE_FETCH_TIMEOUT_SECONDS`, `SOURCE_CACHE_TTL_SECONDS` | Limites do fetch de fontes de conhecimento |
| `CHAT_HISTORY_LIMIT` | Quantas últimas mensagens por sessão são carregadas/persistidas |
| `CORS_ALLOWED_ORIGINS` | Lista separada por vírgula, ou `*` |
| `CHAT_RATE_LIMIT` | Limite da rota pública de chat, sintaxe do `slowapi` (ex. `20/minute`) |
| `FRONTEND_BASE_URL` | Usada só para montar o snippet `<iframe>` retornado ao admin |

## Decisões de arquitetura

| Decisão | Escolha | Por quê |
|---|---|---|
| Orquestração do agente | **Pydantic AI** (não LangChain) | Tipagem nativa com Pydantic, API enxuta, bom encaixe para um agente com poucas tools bem definidas — menos abstração do que o escopo do MVP justificaria com LangChain |
| Estratégia de conhecimento | Tool `fetch_source` (fetch HTTP + cache TTL), decisão de uso feita pelo próprio LLM via tool calling | Exigência explícita do desafio: nada de vector DB/embeddings como núcleo |
| Histórico de conversa passado ao agente | Transcrito como texto simples, prefixado ao prompt do turno atual (não usa `message_history` nativo do pydantic-ai) | Evita acoplamento aos tipos internos de mensagem da biblioteca (`ModelRequest`/`ModelResponse`), simplificando manutenção; suficiente para o volume de histórico do MVP (`CHAT_HISTORY_LIMIT`) |
| Transporte do chat | HTTP REST request/response | Mais simples de implementar, testar e hospedar dentro de um iframe; sem necessidade de conexão persistente para o volume de um MVP |
| Auth admin | API key estática (`X-Admin-Api-Key`) | Único papel administrativo no escopo do desafio; evita construir login/hash de senha/JWT sem necessidade real |
| Auth de embed | Token opaco por tutor (`embed_token`), validado a cada chamada pública | Não expõe a admin key no front público; escopado a um único tutor, rotacionável |
| Persistência | SQLite via SQLModel/SQLAlchemy | Zero infraestrutura extra para rodar o demo; troca para PostgreSQL é apenas mudar `DATABASE_URL`, pois a camada ORM é agnóstica ao dialeto |
| Rate limiting | `slowapi`, por IP, só na rota pública de chat | É o endpoint mais exposto (sem auth de usuário real); RNF explícito do desafio |
| Logs | JSON estruturado (`app/core/logging.py`) | Facilita depurar falhas de tool call do agente (RNF explícito) |

## Fluxo embed ponta a ponta

1. Admin autentica com `X-Admin-Api-Key` e cria um tutor via `POST /api/admin/tutors`
   (título, descrição curta, instruções de sistema, fontes opcionais). A API retorna um
   `embed_token` único para esse tutor.
2. Admin consulta `GET /api/admin/tutors/{id}/embed-snippet` e recebe um `<iframe>` pronto
   (`{FRONTEND_BASE_URL}/widget?tutorId=...&token=...`).
3. O integrador cola o snippet no site dele.
4. O usuário final abre o site; o iframe carrega a página `/widget` do frontend, que chama
   `POST /api/public/chat` com `tutor_id`, `embed_token` e a mensagem.
5. O backend valida o token, carrega o histórico recente da sessão, monta o agente Pydantic AI
   com as instruções do tutor, executa o turno (podendo chamar `fetch_source` se precisar de
   contexto de uma fonte) e persiste o par pergunta/resposta.
6. Recarregar o iframe com o mesmo `session_id` (guardado no `localStorage` do widget) recupera
   o histórico via `GET /api/public/chat/{session_id}/history`.

## Limitações conhecidas do MVP

- Segurança "mínima aceitável para demo": API key estática, sem múltiplos admins/login, sem
  expiração automática do `embed_token`.
- Mitigação de SSRF no fetch de fontes é básica (bloqueia IP privado/loopback resolvido), não
  é uma proteção completa contra todos os vetores.
- Fontes suportadas são apenas URLs públicas HTTP(S) retornando texto/JSON simples — sem PDF,
  sem autenticação na fonte, sem crawler.
- SQLite não é adequado para alta concorrência real; ver `DATABASE_URL` para trocar por Postgres.
- Sem streaming de resposta (SSE/WebSocket): a resposta do chat é retornada de uma vez.

## Próximos passos para produção (não implementados)

- Autenticação multi-admin (JWT/OAuth) em vez de API key estática.
- Migração para PostgreSQL + Alembic para migrações versionadas.
- Streaming de resposta (SSE) para reduzir a latência percebida.
- Expiração/rotação automática de `embed_token`, com possibilidade de múltiplos tokens por tutor.
- Harness de avaliação automatizada do agente (conjunto de perguntas-âncora + verificação de
  alucinação) além do QA manual.
- Hardening adicional de SSRF (allow-list de domínios por tutor, proxy de egress dedicado).
- Isolamento multi-tenant real caso a plataforma passe a atender múltiplas organizações.

## Diagrama de arquitetura

Ver `../IMPLEMENTATION_PLAN.md` na raiz do projeto para os diagramas completos (Mermaid).
Resumo em ASCII:

```
Integrador (site) --iframe--> Widget (frontend) --HTTP--> Backend API
                                                              |
                                     +------------------------+------------------------+
                                     |                        |                        |
                              Admin API                 Public API                Agente (Pydantic AI)
                              (X-Admin-Api-Key)          (embed_token)                  |
                                     |                        |                  Tool: fetch_source
                                     +----------- SQLite (Tutor, Source, --------------+
                                                  ChatSession, ChatMessage)
```
