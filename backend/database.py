from sqlmodel import SQLModel, create_engine, Session

from backend.config import config

DATABASE_URL = (
    f"postgresql://{config.PG_USER}:{config.PG_PASSWORD}"
    f"@{config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}"
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
