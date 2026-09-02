import secrets
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
) -> None:
    """Protect API routes without exposing configured keys in application state logs."""

    settings = request.app.state.settings
    if not settings.auth_required:
        return
    if api_key is not None:
        matches = [
            secrets.compare_digest(api_key, configured_key)
            for configured_key in settings.api_keys
        ]
        if any(matches):
            return
    raise HTTPException(
        status_code=401,
        detail="A valid API key is required.",
        headers={"WWW-Authenticate": "ApiKey"},
    )
