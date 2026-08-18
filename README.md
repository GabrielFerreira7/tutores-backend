# Tutores — Backend

API do MVP da **Plataforma de Tutores Personalizados** (desafio técnico DOT Digital Group).
FastAPI + Pydantic AI + SQLModel/SQLite. Ver o repositório irmão
[`tutores-frontend`](https://github.com/GabrielFerreira7/tutores-frontend) para o dashboard
admin e o widget de embed.

Documentação adicional: [plano de implementação](docs/IMPLEMENTATION_PLAN.md) (diagramas de
arquitetura, decisões e trade-offs discutidos antes de implementar) e
[roteiro de testes manuais](docs/TESTING.md) (cobre os dois repositórios juntos).

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
ruff check app tests   # lint
ruff format app tests  # formatador (substitui black; um único binário para as duas coisas)
```

Os testes **não fazem chamadas reais a nenhum provedor de LLM** — a rota de chat usa
`pydantic_ai.models.test.TestModel` injetado via *dependency override* (`tests/conftest.py`),
e o fetch de fontes é mockado com `respx`. Isso mantém a suíte determinística, rápida e sem custo.

## Variáveis de ambiente

Veja `.env.example` para a lista completa e comentada. Principais:

| Variável | Uso |
|---|---|
| `ADMIN_API_KEY` | Chave exigida no header `X-Admin-Api-Key` para todas as rotas `/api/admin/*` |
| `DATABASE_URL` | **Obrigatória** — string de conexão SQLAlchemy. Ver seção [Banco de dados](#banco-de-dados) abaixo antes de rodar em qualquer ambiente que não seja o seu localhost |
| `LLM_MODEL` | Modelo no formato `provider:model` do pydantic-ai (ex.: `anthropic:claude-haiku-4-5-20251001`) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Lida diretamente pelo SDK do provedor (nunca pela aplicação) |
| `MAX_SOURCE_FETCH_BYTES`, `SOURCE_FETCH_TIMEOUT_SECONDS`, `SOURCE_CACHE_TTL_SECONDS` | Limites do fetch de fontes de conhecimento |
| `CHAT_HISTORY_LIMIT` | Quantas últimas mensagens por sessão são carregadas/persistidas |
| `CORS_ALLOWED_ORIGINS` | Lista separada por vírgula, ou `*` |
| `CHAT_RATE_LIMIT` | Limite da rota pública de chat, sintaxe do `slowapi` (ex. `20/minute`) |
| `FRONTEND_BASE_URL` | Usada só para montar o snippet `<iframe>` retornado ao admin |

## Banco de dados

A aplicação **precisa** de `DATABASE_URL` configurada em `.env` — sem ela, `Settings` cai no
default (`sqlite:///./data/tutors.db`), o que funciona para rodar local mas não deve ser
assumido implicitamente em outros ambientes. Configure explicitamente essa variável em
qualquer deploy fora do seu localhost.

### Opção padrão — SQLite (zero provisionamento)

Não é preciso instalar nem subir nada: no primeiro start, `app/db.py` cria o diretório
`data/` e o arquivo `tutors.db` automaticamente, e `SQLModel.metadata.create_all(engine)`
cria as tabelas. Basta a `DATABASE_URL` apontar para um caminho de arquivo local:

```bash
DATABASE_URL=sqlite:///./data/tutors.db
```

No Docker, esse arquivo vive dentro do volume nomeado `tutors-data` (declarado no
`compose.yaml`), então sobrevive a `docker compose restart`/`up` — só é perdido se o volume
for removido explicitamente (`docker compose down -v`).

### Alternativa — PostgreSQL (se não houver banco disponível no ambiente)

Se o ambiente onde você for rodar isso **não tiver um PostgreSQL disponível**, este repo
já traz um serviço descartável pronto no `compose.yaml`, atrás de um profile (não sobe
com o `docker compose up` normal, só sob demanda):

```bash
# 1. Provisiona um Postgres local descartável (porta 5432, usuário/senha "tutores")
docker compose --profile postgres up -d db

# 2. Instala o driver (não vem por padrão, só quem usa Postgres precisa dele)
pip install "psycopg[binary]==3.2.3"
# ou descomente a linha correspondente em requirements.txt e rode pip install -r requirements.txt

# 3. Aponta o backend para ele em .env
DATABASE_URL=postgresql+psycopg://tutores:tutores@localhost:5432/tutores
# se o backend também estiver rodando via docker compose (não local), use "db" em vez de
# "localhost" — é o nome do serviço na rede interna do compose:
# DATABASE_URL=postgresql+psycopg://tutores:tutores@db:5432/tutores

# 4. Recria o backend para pegar a nova env var (restart sozinho não relê o .env)
docker compose up -d --force-recreate backend
```

Como a persistência é feita via SQLModel/SQLAlchemy, nenhuma linha de código muda ao trocar
de SQLite para Postgres — só a `DATABASE_URL` e o driver instalado. Se você tiver um
PostgreSQL gerenciado externo (RDS, Supabase, Neon, etc.), o mesmo vale: só aponte a
`DATABASE_URL` para ele em vez de usar o serviço `db` do compose.

## Dados de exemplo (seed)

O banco começa **vazio**: como explicado acima, `data/` (SQLite) fica fora do controle de
versão de propósito — dados de aplicação (tutores, tokens de embed, histórico de chat) não
devem ir pro git, só código. Isso significa que qualquer clone deste repositório precisa
criar tutores do zero antes de ter algo pra mostrar.

Para eliminar esse passo manual, existe um script de seed que popula dois tutores de exemplo
prontos para uso (os mesmos "Tutor 1" e "Tutor 2" descritos em
[`docs/TESTING.md`](docs/TESTING.md)):

```bash
docker compose exec backend python -m app.seed
# ou, rodando localmente sem Docker:
python -m app.seed
```

É seguro rodar quantas vezes quiser: `seed_example_tutors()` só insere os dois tutores se o
banco **ainda não tiver nenhum tutor** — nunca sobrescreve ou duplica dados existentes.

**Por que isso não roda sozinho no startup do backend?** Foi uma escolha deliberada, não um
esquecimento:

- O mesmo `lifespan` do FastAPI que cria as tabelas (`create_db_and_tables()`) também é
  disparado pela suíte de testes via `TestClient` — se o seed rodasse ali, `pytest` passaria
  a escrever tutores de demo no `data/tutors.db` real do desenvolvedor a cada execução, sem
  nenhuma relação com o que o teste está validando.
- Um deploy real não deveria ganhar dois tutores de demonstração "de graça" no primeiro
  boot sem ninguém pedir — dados de exemplo devem ser um passo opt-in, do mesmo jeito que os
  profiles `postgres` e `local-llm` do `compose.yaml` também não sobem sozinhos.

Os IDs e `embed_token`s dos dois tutores de exemplo são **fixos** (não gerados
aleatoriamente a cada seed), de propósito: é o que permite os links de widget já prontos em
`docs/TESTING.md` funcionarem em qualquer clone, sem precisar copiar valores novos do
dashboard antes de testar. Assim como o `ADMIN_API_KEY` padrão (`dot-demo-admin-key`), são
valores de demo conhecidos, não segredos — regenere o token de cada tutor pelo dashboard
("Regenerar token") antes de usar isso como base de um deploy real.

## Sem chave de LLM? Use um modelo local (Ollama)

Se você não tem (ou não quer gastar) uma chave de API de um provedor pago, este repo traz
um serviço opcional de [Ollama](https://ollama.com) — runtime de LLM local — atrás de um
profile do `compose.yaml` (**não sobe com `docker compose up` normal, só sob demanda**),
igual ao do Postgres.

Isso é *opt-in* em dois níveis independentes, e os dois precisam ser verdade para o Ollama
entrar em uso:

1. O serviço `ollama` só existe se alguém rodar `docker compose --profile local-llm up -d
   ollama` explicitamente — sem isso, ele não roda, não consome porta/RAM/CPU, e o backend
   nem sabe que ele existe.
2. Mesmo com o serviço no ar, o backend só fala com ele se `LLM_MODEL` em `.env` apontar
   para `ollama:...`. **Se você já tem uma chave real configurada (`LLM_MODEL=anthropic:...`
   ou `openai:...`), nada muda** — o Ollama fica completamente inerte, mesmo que o container
   esteja rodando. Não existe fallback automático de "chave falhou → tenta o local"; é uma
   troca manual de `LLM_MODEL`, uma ou outra, nunca os dois ao mesmo tempo.

```bash
# 1. Sobe o Ollama (porta 11434)
docker compose --profile local-llm up -d ollama

# 2. Baixa um modelo pequeno (uma vez só; fica no volume tutores-ollama-data)
docker exec -it $(docker compose ps -q ollama) ollama pull qwen2.5:0.5b

# 3. Aponta o backend para ele em .env
LLM_MODEL=ollama:qwen2.5:0.5b
OLLAMA_BASE_URL=http://ollama:11434/v1

# 4. Recria o backend (restart sozinho não relê o .env)
docker compose up -d --force-recreate backend
```

O pydantic-ai já tem um provider nativo para Ollama (lê `OLLAMA_BASE_URL`), então nenhuma
linha de código precisa mudar — é só configuração, igual à troca de banco de dados.

### ⚠️ Testado de verdade — e a tool calling não funcionou nos modelos pequenos

Antes de documentar isso, testei manualmente contra o backend real (não só em teoria):

| Modelo | Conversa simples (sem fonte) | Tool calling (`fetch_source`) | Latência (CPU, sem GPU) |
|---|---|---|---|
| `qwen2.5:0.5b` | ✅ Resposta coerente | ❌ Nunca invocou a tool (fonte nunca ficou em cache) | ~5s |
| `llama3.2:1b` | — | ❌ "Tentou" chamar a tool, mas vazou o JSON da chamada como texto da resposta em vez de usar o protocolo de tool calling da API | ~9s |
| `qwen2.5:3b` | — | ❌ Mesma falha — nunca buscou a fonte de verdade | ~22s |

**Conclusão honesta**: um modelo local pequeno via Ollama é uma opção real e testada para
**tutores sem fonte de conhecimento** (persona/conversa pura) — funciona, é grátis, não
precisa de internet além do pull inicial. Mas para tutores que dependem de `fetch_source`
(o núcleo da estratégia agêntica deste desafio), nenhum dos três modelos testados chamou a
tool de forma confiável — a causa provável é como o endpoint OpenAI-compatible do Ollama
lida com tool calling nesses modelos/quantizações, não um bug deste código. Se você
precisar de um tutor com fonte respondendo de verdade, use uma chave real (Anthropic/OpenAI)
para esse caso — o modelo local fica como fallback de conversa, não substituto completo.

Se quiser tentar um modelo maior que talvez chame a tool de forma mais confiável (ex.
`qwen2.5:7b` ou `qwen2.5:14b`), o mesmo passo a passo vale — só troque a tag no `pull` e no
`LLM_MODEL`; espere latência bem maior sem GPU.

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
| Fallback de LLM sem chave de API | Ollama atrás de um profile do Docker Compose (não LM Studio/vLLM/repo próprio) | pydantic-ai já tem provider nativo para Ollama (zero código); testado e honesto sobre a limitação real (tool calling não confiável em modelos ≤3B — ver seção "Sem chave de LLM?") |

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
- Fallback local via Ollama (ver "Sem chave de LLM?") só é confiável para tutores **sem**
  fonte de conhecimento — testado e confirmado que modelos ≤3B não chamam `fetch_source` de
  forma consistente através do endpoint OpenAI-compatible do Ollama.

## Próximos passos para produção (não implementados)

Lista de evolução, conforme pedido pelo PRD (seção 8b) — nada abaixo está implementado
neste MVP, é só o roteiro do que viria depois. Alguns itens (RAG vetorial, por exemplo)
tocam em pontos explicitamente fora de escopo desta entrega (PRD seção 6b); estão aqui
apenas como possibilidade *futura e opcional*, não como algo que este MVP deveria ter feito.

### Deploy e infraestrutura

- **Hospedagem**: hoje só há `Dockerfile`/`compose.yaml` para rodar local; em produção, subir
  a imagem em um serviço gerenciado (Fly.io, Railway, Render, AWS Fargate/App Runner, Google
  Cloud Run) atrás de HTTPS gerenciado pelo provedor, em vez de expor a porta 8000 direto.
- **Domínio**: um esquema simples funciona bem aqui — algo como `api.tutores.<dominio>` para o
  backend e `app.tutores.<dominio>` (admin) / `embed.tutores.<dominio>` (widget) para o
  frontend, mantendo o admin e o widget público em subdomínios/paths separados por clareza,
  não por necessidade técnica.
- **Banco gerenciado**: trocar SQLite por PostgreSQL gerenciado (RDS, Supabase, Neon — a troca
  já é trivial, só mudar `DATABASE_URL`, ver seção "Banco de dados" acima) para permitir mais
  de uma instância do backend rodando ao mesmo tempo atrás de um load balancer.
- **Secrets**: mover `ADMIN_API_KEY`/chaves de LLM do `.env` local para um secret manager do
  provedor de hospedagem (Fly secrets, AWS Secrets Manager, variáveis criptografadas do CI) —
  nunca commitar, nunca deixar em texto puro num volume compartilhado.
- **CI/CD**: pipeline (ex. GitHub Actions) rodando `pytest` + `ruff check` + `ruff format --check`
  em cada PR, build/push da imagem Docker e deploy automático ao mergear na `main`. Hoje essa
  verificação é manual, feita antes de cada push.
- **CORS de produção**: restringir `CORS_ALLOWED_ORIGINS` aos domínios reais dos integradores
  autorizados — o `*` atual é aceitável só para demo local, documentado como tal.
- **Cabeçalhos de embed**: configurar explicitamente `Content-Security-Policy: frame-ancestors`
  com allow-list dos domínios integradores autorizados a incorporar o widget (hoje funciona
  por *ausência* de bloqueio; em produção deveria ser uma permissão explícita, não implícita).
- **Observabilidade real**: os logs JSON estruturados já existem, mas em produção precisam de
  um destino de agregação (Grafana Loki, Datadog, CloudWatch Logs), rastreamento de erros
  (Sentry) e alertas de uptime/latência sobre a rota de chat.
- **Escalonamento horizontal**: o backend já é stateless (sem estado em memória entre
  requisições, exceto o cache de fonte, que é só otimização), então escalar horizontalmente
  atrás de um load balancer é direto assim que o banco deixar de ser SQLite local.

### Estratégia de conhecimento e evolução do agente

- **RAG vetorial como complemento opcional, não substituto**: se o volume/tamanho das fontes de
  um tutor crescer muito (dezenas de documentos grandes), o fetch simples + cache pode não
  escalar bem. Uma evolução possível é adicionar uma tool adicional (`search_knowledge_base`,
  por exemplo, apoiada em embeddings/índice vetorial) **ao lado** de `fetch_source` — o agente
  continuaria decidindo qual ferramenta usar, mantendo a estratégia agêntica como núcleo
  (conforme exigido pelo PRD) em vez de trocá-la por um pipeline de RAG clássico.
- **Chunking e sumarização incremental** de fontes grandes antes de truncar, em vez do corte
  simples por tamanho de bytes usado hoje (`MAX_SOURCE_FETCH_BYTES`).
- **Cache semântico** de respostas para perguntas repetidas/similares, reduzindo custo e
  latência além do cache de fonte já existente.
- **Streaming de resposta** (SSE) para reduzir a latência percebida — hoje a resposta só chega
  de uma vez.
- **Roteamento de modelo por custo**: usar um modelo mais barato/rápido por padrão e escalar
  para um mais caro só em casos que o modelo barato sinalize incerteza.
- **Monitorar confiabilidade de tool calling por provedor/modelo**: testamos isso de verdade
  (ver seção "Sem chave de LLM?") e nem todo modelo chama `fetch_source` de forma confiável —
  vale registrar isso por modelo/provedor conforme novos forem adicionados, não assumir que
  "qualquer LLM com tool calling" funciona igual.

### Segurança e confiabilidade

- **Mitigação de prompt injection via fonte externa**: o conteúdo de `fetch_source` vem de uma
  URL pública e é injetado no contexto do LLM — uma fonte maliciosa poderia conter texto
  tentando sobrescrever as instruções do tutor (“ignore as instruções anteriores e...”). Hoje
  não há sanitização/isolamento desse conteúdo além do limite de tamanho; em produção, vale
  marcar explicitamente o conteúdo buscado como *dado não confiável*, não instrução, no prompt.
- **Harness de avaliação automatizada** do agente (conjunto de perguntas-âncora + verificação
  de alucinação/regressão de prompt) além do QA manual atual.
- **Guardrails de conteúdo** (moderação de entrada/saída) se a plataforma passar a atender
  público não controlado.
- **Autenticação multi-admin** (JWT/OAuth) em vez de API key estática — hoje é aceitável por
  ser um único papel administrativo no escopo do MVP.
- **Expiração/rotação automática** de `embed_token`, com possibilidade de múltiplos tokens por
  tutor (ex.: um por ambiente/integrador).
- **Hardening adicional de SSRF**: allow-list de domínios por tutor, proxy de egress dedicado —
  a mitigação atual (bloqueio de IP privado/loopback) é básica, não completa.
- **Isolamento multi-tenant real**, caso a plataforma passe a atender múltiplas organizações
  com dados segregados de verdade (hoje é single-tenant, fora de escopo explícito do PRD).

## Diagrama de arquitetura

Ver [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) para os diagramas completos
(Mermaid: componentes, sequência de conversa, sequência de setup de embed, modelo de dados).
Resumo em ASCII (frontend, backend, agente, persistência, embed):

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
