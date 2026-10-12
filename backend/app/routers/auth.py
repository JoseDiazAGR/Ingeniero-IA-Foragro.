"""
Endpoints de autenticación del dashboard:
POST /api/login
POST /api/logout
GET  /api/session
"""

from fastapi import APIRouter, Cookie, Depends, Response

from app.auth import create_session, delete_session, get_session_username, require_auth
from app.config import COOKIE_SECURE, SESSION_COOKIE_NAME, SESSION_TTL_HOURS, logger
from app.database import get_db
from app.models import LoginRequest
from app.security import rate_limit, verify_password

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, response: Response, _rl=Depends(rate_limit(5, 60))):
    with get_db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username = %s", (req.username,)).fetchone()

    # SECURITY: mismo trabajo y mensaje de error exista o no el usuario.
    dummy_hash = "$2b$12$CwYlbMkuHfsQzYqz4b2rL.k5gTPWq7eyDp3xNQmvS8YFVEUEuFo0e"
    valid = verify_password(req.password, row["password_hash"] if row else dummy_hash)

    if not row or not valid:
        logger.info("Intento de login fallido para usuario=%r", req.username)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    token = create_session(req.username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )
    return {"status": "ok", "username": req.username}


@router.post("/logout")
def logout(response: Response, foragro_session: str | None = Cookie(default=None)):
    delete_session(foragro_session)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/session")
def session_info(username: str = Depends(require_auth)):
    return {"username": username}


from fastapi import HTTPException