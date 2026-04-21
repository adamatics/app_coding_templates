from fastapi import HTTPException, status

from app.core.config import settings


def verify_token(token: str) -> str:
    if token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "demo-user"
