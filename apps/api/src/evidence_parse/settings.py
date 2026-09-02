import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    auto_create_schema: bool

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "EVIDENCE_PARSE_DATABASE_URL", "sqlite+pysqlite:///./data/evidence_parse.db"
            ),
            auto_create_schema=_environment_flag("EVIDENCE_PARSE_AUTO_CREATE_SCHEMA", True),
        )


def _environment_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.casefold().strip() in {"1", "true", "yes", "on"}
