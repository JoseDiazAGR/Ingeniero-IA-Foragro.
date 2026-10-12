"""
Gestión de sesiones: creación, validación, destrucción y dependencia
de autenticación para endpoints protegidos.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException

from app.config import SESSION_TTL_HOURS
from app.database import get_db


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, username, expires_at) VALUES (%s, %s, %s)",
            (_hash_token(token), username, expires_at),
        )
        conn.commit()
    return token


def get_session_username(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT username, expires_at FROM sessions WHERE token_hash = %s",
            (_hash_token(token),),
        ).fetchone()
        if not row:
            return None
        # expires_at ya es un objeto datetime en PostgreSQL (no string)
        expires = row["expires_at"]
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires)
        if expires < datetime.utcnow():
            conn.execute("DELETE FROM sessions WHERE token_hash = %s", (_hash_token(token),))
            conn.commit()
            return None
        return row["username"]


def delete_session(token: Optional[str]):
    if not token:
        return
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = %s", (_hash_token(token),))
        conn.commit()


def require_auth(foragro_session: Optional[str] = Cookie(default=None)) -> str:
    """
    SECURITY: dependencia usada en todos los endpoints que exponen datos de
    negocio o PII de clientes. Un cliente HTTP directo (curl, Postman) debe
    pasar por aquí obligatoriamente.
    """
    username = get_session_username(foragro_session)
    if not username:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    return username