from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> Principal:
    settings = get_settings()
    try:
        claims = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token.") from exc

    subject = claims.get("sub")
    role = claims.get("role")
    if not isinstance(subject, str) or not isinstance(role, str):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token is missing required claims.")
    return Principal(subject=subject, role=role)


def require_role(*allowed: str) -> Callable[[Principal], Principal]:
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role {principal.role!r} may not perform this action.",
            )
        return principal

    return dependency
