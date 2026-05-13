import secrets
from fastapi import Security, status, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key: str = Security(api_key_header)):
    if not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Access denied.",
            headers={"WWW-Authenticate": "APIKey"},
        )
