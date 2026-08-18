from sqlmodel import Session, select

from app import seed
from app.models.tutor import Tutor
from app.schemas.tutor import TutorCreate
from app.services import tutor_service


def test_seed_example_tutors_creates_two_tutors_on_empty_db(session: Session):
    created = seed.seed_example_tutors(session)

    assert created == 2
    tutors = list(session.exec(select(Tutor)))
    assert {t.id for t in tutors} == {seed._WELCOME_TUTOR_ID, seed._GITIGNORE_TUTOR_ID}
    assert {t.embed_token for t in tutors} == {
        seed._WELCOME_TUTOR_TOKEN,
        seed._GITIGNORE_TUTOR_TOKEN,
    }

    gitignore_tutor = tutor_service.get_tutor(session, seed._GITIGNORE_TUTOR_ID)
    assert len(gitignore_tutor.sources) == 1


def test_seed_example_tutors_skips_when_any_tutor_already_exists(session: Session):
    tutor_service.create_tutor(
        session,
        TutorCreate(title="Tutor existente", system_instructions="Instruções."),
    )

    created = seed.seed_example_tutors(session)

    assert created == 0
    assert len(list(session.exec(select(Tutor)))) == 1
