import os
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class Settings:
    database_url: str
    auto_create_schema: bool
    auth_required: bool
    api_keys: Tuple[str, ...] = field(repr=False)
    cors_origins: Tuple[str, ...]

    def __post_init__(self) -> None:
        if self.auth_required and not self.api_keys:
            raise ValueError(
                "EVIDENCE_PARSE_API_KEYS must contain at least one key "
                "when authentication is required."
            )

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "EVIDENCE_PARSE_DATABASE_URL", "sqlite+pysqlite:///./data/evidence_parse.db"
            ),
            auto_create_schema=_environment_flag("EVIDENCE_PARSE_AUTO_CREATE_SCHEMA", True),
            auth_required=_environment_flag("EVIDENCE_PARSE_AUTH_REQUIRED", False),
            api_keys=_environment_list("EVIDENCE_PARSE_API_KEYS"),
            cors_origins=_environment_list(
                "EVIDENCE_PARSE_CORS_ORIGINS",
                ("http://localhost:3000", "http://127.0.0.1:3000"),
            ),
        )


def _environment_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.casefold().strip() in {"1", "true", "yes", "on"}


def _environment_list(name: str, default: Tuple[str, ...] = ()) -> Tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())
