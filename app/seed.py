"""Popula o banco com os dois tutores de exemplo usados no roteiro de testes.

Deliberadamente **não** é chamado a partir do lifespan do FastAPI (app/main.py).
Se fosse automático no startup, a suíte de testes — que também sobe a aplicação
via TestClient, disparando o mesmo lifespan — escreveria esses tutores de demo
no data/tutors.db real do desenvolvedor a cada `pytest`, sem relação nenhuma
com o que o teste está validando. Em vez disso é um passo explícito e opcional,
documentado em docs/TESTING.md: `docker compose exec backend python -m app.seed`.

Os IDs e embed_tokens abaixo são fixos (não gerados aleatoriamente) de propósito:
é o que permite os links de widget já prontos no roteiro de testes (TESTING.md)
funcionarem em qualquer clone do repositório, sem precisar copiar valores novos
do dashboard antes de testar. Como o admin_api_key padrão, são valores de demo
conhecidos, não segredos — regenere o token de cada tutor pelo dashboard
("Regenerar token") antes de usar isso como base de um deploy real.
"""

import logging

from sqlmodel import Session, select

from app.db import create_db_and_tables, engine
from app.models.source import Source
from app.models.tutor import Tutor

logger = logging.getLogger(__name__)

_WELCOME_TUTOR_ID = "c9ba4d13a81e44b394ed52deecaac5f2"
_WELCOME_TUTOR_TOKEN = "411yVJOfeyZ37VouD156FzDkWMqNwWWL"
_GITIGNORE_TUTOR_ID = "2b9a2c220d4d4164812b13f6b2eaf908"
_GITIGNORE_TUTOR_TOKEN = "TDRkSv6g8FmIhydqponNpbvjsovwTBvu"


def _example_tutors() -> list[Tutor]:
    return [
        Tutor(
            id=_WELCOME_TUTOR_ID,
            embed_token=_WELCOME_TUTOR_TOKEN,
            title="Tutor de Boas-Vindas",
            short_description="Tutor genérico, sem fonte de conhecimento cadastrada",
            system_instructions=(
                "Você é um tutor amigável de boas-vindas da DOT Digital Group. Cumprimente "
                "o usuário, explique brevemente que você é uma demonstração de um MVP de "
                "plataforma de tutores e responda de forma breve e simpática."
            ),
        ),
        Tutor(
            id=_GITIGNORE_TUTOR_ID,
            embed_token=_GITIGNORE_TUTOR_TOKEN,
            title="Tutor de .gitignore",
            short_description=(
                "Tutor com uma fonte de conhecimento real para testar a busca agêntica"
            ),
            system_instructions=(
                "Você é um tutor especialista no arquivo README de modelos de .gitignore do "
                "GitHub. Use a ferramenta fetch_source para consultar a fonte cadastrada antes "
                "de responder perguntas sobre o conteúdo dela. Se a pergunta não tiver relação "
                "com a fonte, responda normalmente sem inventar que consultou algo."
            ),
            sources=[
                Source(
                    label="README gitignore templates",
                    url="https://raw.githubusercontent.com/github/gitignore/main/README.md",
                )
            ],
        ),
    ]


def seed_example_tutors(session: Session) -> int:
    """Insere os tutores de exemplo se o banco ainda não tiver nenhum tutor.

    Idempotente e não-destrutivo: não roda se já existir qualquer tutor (mesmo que
    não sejam estes dois), para nunca sobrescrever dados reais de um admin. Retorna
    quantos tutores foram criados (0 se pulou).
    """
    if session.exec(select(Tutor)).first() is not None:
        return 0

    tutors = _example_tutors()
    for tutor in tutors:
        session.add(tutor)
    session.commit()
    return len(tutors)


def main() -> None:
    from app.config import get_settings
    from app.core.logging import configure_logging

    configure_logging(get_settings().log_level)
    create_db_and_tables()
    with Session(engine) as session:
        created = seed_example_tutors(session)

    if created:
        logger.info("seed_example_tutors_created", extra={"count": created})
    else:
        logger.info("seed_example_tutors_skipped_existing_data")


if __name__ == "__main__":
    main()
