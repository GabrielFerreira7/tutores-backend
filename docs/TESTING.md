# Roteiro de Testes — Plataforma de Tutores Personalizados

> Checklist manual de validação do MVP, organizado com base nos casos de uso e critérios de
> aceite do PRD (`Cópia de PRD - Plataforma de tutores personalizados.pdf`). Marque os itens
> conforme for testando.
>
> Este documento cobre os dois repositórios juntos (backend + frontend) e por isso assume
> que ambos estão clonados **lado a lado**, como `backend/` e `frontend/` sob a mesma pasta
> pai — é assim que os comandos `cd backend`/`cd frontend` abaixo fazem sentido. Cópia
> idêntica também existe em
> [`tutores-frontend/docs/TESTING.md`](https://github.com/GabrielFerreira7/tutores-frontend/blob/main/docs/TESTING.md).

## 0. Pré-requisitos

- [ ] Docker Desktop rodando
- [ ] Containers no ar:
  ```bash
  cd backend  && docker compose up -d
  cd frontend && docker compose up -d
  ```
- [ ] Backend respondendo: `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] Popular os dois tutores de exemplo (Tutor 1 e Tutor 2 abaixo):
  ```bash
  docker compose exec backend python -m app.seed
  ```
  Passo opcional, mas sem ele o banco começa **vazio** — nenhum tutor é criado
  automaticamente no startup do backend (ver "Dados de exemplo (seed)" no
  `backend/README.md` para o porquê disso ser um passo explícito em vez de
  automático). É seguro rodar de novo a qualquer momento: só insere os dois
  tutores se o banco ainda não tiver nenhum tutor, nunca sobrescreve dados
  existentes.
- [ ] Frontend respondendo: abrir http://localhost:5173/admin/tutors no navegador
- [ ] `backend/.env` com uma **chave real de LLM** (`ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`,
      conforme o `LLM_MODEL` escolhido) e com quota/billing disponível na conta do provedor —
      sem isso, o passo 4 (conversa) não funciona de verdade (uma chave sem crédito dá 500
      genérico, igual a uma chave ausente). Depois de editar o `.env`, **recrie** o container
      (um `restart` sozinho não relê o arquivo): `docker compose up -d --force-recreate backend`

### Credenciais e URLs deste ambiente local

| Item | Valor |
|---|---|
| Admin dashboard | http://localhost:5173/admin/tutors |
| Admin API key | `dot-demo-admin-key` |
| Backend (API/docs) | http://localhost:8000 (Swagger em `/docs`) |
| Página de exemplo do integrador | http://localhost:5173/embed-demo.html |

## 1. Dados de exemplo para os tutores

Use estes dados prontos ao testar o formulário de criação/edição de tutor no dashboard admin
(`+ Novo tutor`). Cobrem os quatro cenários que valem a pena testar: sem fonte, com fonte válida,
com fonte quebrada (404) e com fonte bloqueada por segurança (SSRF).

### Tutor 1 — "Tutor de Boas-Vindas" (criado pelo seed, sem fonte)

| Campo | Valor |
|---|---|
| Título | `Tutor de Boas-Vindas` |
| Descrição curta | `Tutor genérico, sem fonte de conhecimento cadastrada` |
| Instruções do sistema | `Você é um tutor amigável de boas-vindas da DOT Digital Group. Cumprimente o usuário, explique brevemente que você é uma demonstração de um MVP de plataforma de tutores e responda de forma breve e simpática.` |
| Fontes | nenhuma |
| Widget direto | http://localhost:5173/widget?tutorId=c9ba4d13a81e44b394ed52deecaac5f2&token=411yVJOfeyZ37VouD156FzDkWMqNwWWL |
| Mensagem de teste | `Olá, quem é você e o que você faz?` |
| Esperado | Resposta coerente com a persona, sem tentar consultar nenhuma fonte |

### Tutor 2 — "Tutor de .gitignore" (criado pelo seed, com fonte real)

| Campo | Valor |
|---|---|
| Título | `Tutor de .gitignore` |
| Descrição curta | `Tutor com uma fonte de conhecimento real para testar a busca agêntica` |
| Instruções do sistema | `Você é um tutor especialista no arquivo README de modelos de .gitignore do GitHub. Use a ferramenta fetch_source para consultar a fonte cadastrada antes de responder perguntas sobre o conteúdo dela. Se a pergunta não tiver relação com a fonte, responda normalmente sem inventar que consultou algo.` |
| Fontes | rótulo `README gitignore templates`, URL `https://raw.githubusercontent.com/github/gitignore/main/README.md` |
| Widget direto | http://localhost:5173/widget?tutorId=2b9a2c220d4d4164812b13f6b2eaf908&token=TDRkSv6g8FmIhydqponNpbvjsovwTBvu |
| Mensagem de teste | `Que tipos de projeto esse repositório de templates cobre?` |
| Esperado | Resposta refletindo o conteúdo real do README (a IDE/linguagem devem aparecer na resposta), evidenciando que a tool `fetch_source` foi usada — **sem** vector DB/embeddings |

### Tutor 3 — "Tutor de Requests" (crie manualmente pelo dashboard)

Use este para testar o formulário de criação do zero.

| Campo | Valor |
|---|---|
| Título | `Tutor de Requests (Python)` |
| Descrição curta | `Tira dúvidas sobre a biblioteca requests, com base no README oficial` |
| Instruções do sistema | `Você é um tutor especialista na biblioteca Python "requests". Use fetch_source para consultar o README oficial antes de responder perguntas sobre a biblioteca. Seja técnico, mas didático.` |
| Fontes | rótulo `README requests`, URL `https://raw.githubusercontent.com/psf/requests/main/README.md` |
| Mensagem de teste | `Como eu instalo e faço uma requisição GET simples com essa biblioteca?` |
| Esperado | Resposta com o comando de instalação e um exemplo de código coerente com o README real |

### Tutor 4 — "Tutor com Fonte Quebrada" (crie manualmente — testa tratamento de erro)

| Campo | Valor |
|---|---|
| Título | `Tutor com Fonte Quebrada` |
| Descrição curta | `Fonte que não existe — testa o tratamento de erro do fetch` |
| Instruções do sistema | `Você é um tutor de testes. Tente consultar a fonte cadastrada com fetch_source para responder qualquer pergunta sobre ela. Se a fonte estiver indisponível, diga isso claramente ao usuário em vez de inventar uma resposta.` |
| Fontes | rótulo `Fonte inexistente`, URL `https://raw.githubusercontent.com/github/gitignore/main/nao-existe.md` (404 real) |
| Mensagem de teste | `O que diz o conteúdo da fonte cadastrada?` |
| Esperado | Tutor informa que não conseguiu acessar a fonte — **não** deve inventar conteúdo (mitigação de alucinação) |

> Bônus opcional de segurança: adicione uma segunda fonte a este tutor com URL
> `http://127.0.0.1:9999/segredo` e pergunte sobre ela — a resposta da tool deve indicar
> "host não permitido" (mitigação básica de SSRF), nunca tentar de fato acessar a rede interna.

## 2. Roteiro por persona / caso de uso (PRD seção 3)

### 2.1 Administrador — CRUD de tutor (PRD 4.1a/4.1b)

- [ ] Login no dashboard com `dot-demo-admin-key` em http://localhost:5173/admin/tutors
- [ ] Os tutores 1 e 2 aparecem na listagem com status `active`
- [ ] Criar o **Tutor 3** pelo formulário (`+ Novo tutor`), preenchendo com a fonte
- [ ] Criar o **Tutor 4** pelo formulário
- [ ] Editar um tutor existente (ex.: mudar a descrição curta) e confirmar que persiste após
      recarregar a página
- [ ] Desativar um tutor e confirmar que o status muda para `inactive` na listagem, e que o
      botão vira "Ativar" no lugar de "Desativar"
- [ ] Clicar em "Ativar" no mesmo tutor e confirmar que o status volta para `active` (via
      `PATCH /api/admin/tutors/{id}` com `{"status":"active"}` — não existe endpoint dedicado
      de reativação, o dashboard reaproveita o PATCH genérico)

### 2.2 Administrador — snippet de embed (PRD 4.2a / caso de uso "b")

- [ ] Abrir a tela "Embed" de qualquer tutor ativo
- [ ] Confirmar que o `<iframe>` gerado tem `tutorId` e `token` corretos
- [ ] Clicar em "Copiar" e colar em outro lugar para confirmar que o snippet foi copiado

### 2.3 Integrador — incorporação via iframe (PRD 4.2 / caso de uso "c")

- [ ] Abrir http://localhost:5173/embed-demo.html
- [ ] Na tela "Embed" de um tutor (dashboard admin), copiar a **"URL direta"**
- [ ] Colar essa URL no campo da página `embed-demo.html` e clicar em "Carregar" — o iframe
      deve aparecer na hora, sem precisar editar nenhum arquivo nem rebuildar o frontend
- [ ] Repetir com outro tutor (ex.: o Tutor 3 que você criou) e confirmar que troca corretamente
- [ ] O widget carrega dentro do `<iframe>`, sem menu/navegação do admin
- [ ] (Opcional) Copiar a URL da barra de endereço depois de carregar um tutor, abrir em uma
      aba nova — o mesmo tutor deve carregar automaticamente (link direto/bookmarkável)

### 2.4 Usuário final — conversa (PRD 4.3 / caso de uso "c") — precisa da chave de LLM real

- [ ] Tutor 1: enviar a mensagem de teste, validar resposta coerente com a persona
- [ ] Tutor 2: enviar a mensagem de teste, validar que a resposta usa o conteúdo real da fonte
- [ ] Tutor 3: enviar a mensagem de teste, validar resposta técnica coerente com o README real
- [ ] Tutor 4: enviar a mensagem de teste, validar que o tutor **admite** não ter acesso à fonte
      em vez de inventar uma resposta
- [ ] Recarregar a página do widget de qualquer tutor e confirmar que o histórico da conversa
      continua aparecendo (persistência de sessão — PRD 4.4b)

### 2.5 Autenticação e segurança (caso de uso "d" / PRD 5a)

- [ ] Acessar `/admin/tutors` sem a chave admin (ou com uma errada) → API responde 401, sem
      stack trace na resposta
- [ ] No dashboard, digitar uma chave errada na tela de login: a aplicação deve **voltar para
      a própria tela de login** com a mensagem "Chave de administrador inválida. Informe a
      chave correta." — ela **não** deve mostrar a listagem de tutores pela metade (com botões
      como "+ Novo tutor" visíveis mas quebrados); esse era um bug real já corrigido
- [ ] Na URL de um widget, trocar o `token` por qualquer valor → erro 403, sem stack trace
- [ ] Abrir o DevTools (F12 → Network) na página do widget e confirmar que a **admin API key
      nunca aparece** nas chamadas — só o `embed_token` do tutor

### 2.6 Requisitos não funcionais (PRD 5)

- [ ] **Rate limit**: enviar várias mensagens seguidas rapidamente no widget (mais de 20/min) e
      confirmar que em algum momento aparece um erro de "muitas requisições"
- [ ] **Logs estruturados**: `docker logs backend-backend-1` — confirmar formato JSON legível
- [ ] **CORS**: já liberado como `*` para este ambiente local (documentado como aceitável só
      para demo, não para produção)
- [ ] **Sem stack trace**: repita qualquer um dos testes de erro acima e confirme que a resposta
      da API nunca inclui trace de código Python

### 2.7 Fora de escopo (PRD seção 6) — confirmar que **não** existe

- [ ] Nenhuma integração LTI 1.x/1.3 ou com LMS
- [ ] Nenhum banco vetorial / embeddings no fluxo de conhecimento
- [ ] Nenhum fluxo de pagamento/faturamento
- [ ] Nenhum app mobile nativo

### 2.8 Documentação e materiais de apoio (PRD 7e/7f/8)

- [ ] `backend/README.md` e `frontend/README.md` explicam decisões de arquitetura, limitações
      do MVP e como reproduzir o demo
- [ ] Ambos os READMEs confirmam explicitamente o uso de agente de codificação
- [ ] `IMPLEMENTATION_PLAN.md` contém os diagramas de arquitetura (Mermaid) e a lista de
      próximos passos para produção

## 3. Banco de dados (opcional)

Só relevante se você quiser validar o caminho alternativo de persistência documentado no
README do backend (por padrão, tudo acima já roda em SQLite sem nenhum passo extra):

- [ ] `docker compose --profile postgres up -d db` sobe um PostgreSQL descartável (porta 5432)
- [ ] Trocar `DATABASE_URL` em `backend/.env` para
      `postgresql+psycopg://tutores:tutores@localhost:5432/tutores`
- [ ] `docker compose up -d --force-recreate backend` e confirmar que os tutores continuam
      sendo criados/listados normalmente (agora contra o Postgres, não o SQLite)
- [ ] Para voltar ao SQLite: reverter a `DATABASE_URL` e recriar o backend de novo

> ⚠️ Para derrubar só o Postgres depois, use `docker compose stop db` (ou `rm db`) — um simples
> `docker compose --profile postgres down` derruba **o projeto inteiro**, inclusive o `backend`
> que não tem nada a ver com o profile (aconteceu durante os testes deste roteiro).

## 4. LLM local sem chave de API (opcional)

Para quem não tem uma chave de Anthropic/OpenAI à mão. **Testado de verdade** — inclusive a
limitação abaixo, que não é hipotética:

- [ ] `docker compose --profile local-llm up -d ollama` sobe um Ollama local (porta 11434)
- [ ] `docker exec -it $(docker compose ps -q ollama) ollama pull qwen2.5:0.5b` baixa um
      modelo pequeno (~400MB, uma vez só)
- [ ] Em `backend/.env`: `LLM_MODEL=ollama:qwen2.5:0.5b` e
      `OLLAMA_BASE_URL=http://ollama:11434/v1`, depois `docker compose up -d --force-recreate backend`
- [ ] Testar o **Tutor de Boas-Vindas** (sem fonte) — deve responder normalmente, só mais
      devagar (~5s numa CPU comum, sem GPU)
- [ ] **Não espere** o Tutor de .gitignore (com fonte) funcionar de verdade com esse modelo —
      testei com `qwen2.5:0.5b`, `llama3.2:1b` e `qwen2.5:3b` e nenhum chamou a tool
      `fetch_source` de forma confiável (a resposta vem sem refletir o conteúdo real da fonte,
      ou até vaza o JSON da tentativa de chamada como texto). Pra esse caso, use uma chave real.
- [ ] Pra voltar pro provedor pago: reverter `LLM_MODEL`/chave em `.env` e recriar o backend

## 5. Troubleshooting rápido

| Sintoma | Causa provável | Solução |
|---|---|---|
| `curl http://localhost:8000/health` não responde | Container do backend não está de pé | `cd backend && docker compose up -d` e ver `docker compose logs -f` |
| Widget mostra "Não foi possível enviar a mensagem" (500 genérico) | Falta `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` real em `backend/.env`, **ou** a chave existe mas a conta do provedor está sem quota/billing (`insufficient_quota`) | `docker logs backend-backend-1` mostra o erro real (nunca aparece pro cliente); corrigir a chave/billing e `docker compose up -d --force-recreate backend` |
| Editei o `.env` e nada mudou | `docker compose restart` **não relê** o `.env` — só reinicia o processo com as env vars antigas já carregadas no container | `docker compose up -d --force-recreate backend` (ou `frontend`, conforme o caso) |
| 401 ao logar no dashboard admin | Chave digitada diferente de `dot-demo-admin-key` | Conferir `backend/.env` → `ADMIN_API_KEY`. A tela deve voltar para o login com uma mensagem clara (não deve sobrar UI autenticada visível) |
| `/embed-demo.html` mostra a tela do dashboard em vez da página estática | Bug já corrigido (rewrite do `serve` engolindo arquivos estáticos) — se voltar a acontecer, verificar `frontend/public/serve.json` e o `CMD` do `frontend/Dockerfile` | Rebuildar: `cd frontend && docker compose up --build -d` |
| Link direto do `embed-demo.html?tutorId=...&token=...` não carrega o tutor automaticamente | Bug já corrigido (`cleanUrls` do `serve` descartava a query string no redirect de `.html`) — verificar se `"cleanUrls": false` ainda está em `frontend/public/serve.json` | Rebuildar: `cd frontend && docker compose up --build -d` |
