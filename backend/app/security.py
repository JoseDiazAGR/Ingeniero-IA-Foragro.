"""
Utilidades de seguridad: rate limiting, validación de teléfono,
validación de listas blancas, y mitigación CSRF básica.
"""

import hashlib
import re
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Optional

import bcrypt
from fastapi import HTTPException, Request

from app.config import BCRYPT_MAX_BYTES


# ===================== RATE LIMITING =====================
# SECURITY: limitador en memoria (por proceso). Para producción con múltiples
# workers o instancias, reemplazar por Redis (ej. slowapi + Redis).
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def _check_rate_limit(key: str, max_requests: int, window_seconds: int):
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets[key]
        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Intenta de nuevo en unos minutos.")
        bucket.append(now)


def rate_limit(max_requests: int, window_seconds: int):
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"
        _check_rate_limit(key, max_requests, window_seconds)
    return dependency


# ===================== VALIDACIÓN =====================
def normalize_hn_phone(raw: str) -> str:
    """Valida y normaliza a formato +504XXXXXXXX. Lanza 400 si es inválido."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("504") and len(digits) == 11:
        pass
    elif len(digits) == 8:
        digits = "504" + digits
    else:
        raise HTTPException(status_code=400, detail="Número de teléfono hondureño inválido.")
    return "+" + digits


def require_choice(value: Optional[str], allowed: set, field_name: str) -> str:
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"Valor inválido para {field_name}.")
    return value


# ===================== PASSWORD HASHING =====================
def hash_password(password: str) -> str:
    # SECURITY: bcrypt trunca silenciosamente después de 72 bytes.
    # Rechazamos explícitamente para que el usuario lo sepa.
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"La contraseña no puede superar {BCRYPT_MAX_BYTES} bytes.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:BCRYPT_MAX_BYTES], password_hash.encode("utf-8"))
    except Exception:
        return False


# ===================== CSRF BÁSICO =====================
def require_json_content_type(request: Request):
    """
    SECURITY: mitigación de CSRF. Un <form> HTML clásico no puede enviar
    Content-Type: application/json. Combinado con SameSite=Strict en la
    cookie de sesión, cubre los vectores comunes.
    """
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        raise HTTPException(status_code=415, detail="Content-Type debe ser application/json.")