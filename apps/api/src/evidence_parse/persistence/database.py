from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool

from evidence_parse.persistence.tables import Base


class Database:
    """Own the SQLAlchemy engine and portable schema lifecycle."""

    def __init__(self, url: str) -> None:
        parsed_url = make_url(url)
        engine_options = {"pool_pre_ping": True}
        if parsed_url.get_backend_name() == "sqlite":
            database = parsed_url.database
            if database and database != ":memory:":
                Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            engine_options["connect_args"] = {"check_same_thread": False}
            if database == ":memory:":
                engine_options["poolclass"] = StaticPool
        self.engine: Engine = create_engine(url, **engine_options)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()
