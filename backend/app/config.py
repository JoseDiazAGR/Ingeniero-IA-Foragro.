"""
Configuración centralizada. Todos los valores sensibles vienen de variables
de entorno; nunca están hardcodeados en el código fuente.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("foragro")

# ---------------------------------------------------------------------------
# APIs externas
# ---------------------------------------------------------------------------
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY", "")
WHATSAPP_TOKEN       = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID", "")
# Token de verificación del webhook de Meta (tú lo defines, Meta lo confirma)
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "foragro_webhook_2025")
OPENWEATHER_API_KEY  = os.getenv("OPENWEATHER_API_KEY", "")
HUBSPOT_API_KEY      = os.getenv("HUBSPOT_API_KEY", "")

# ---------------------------------------------------------------------------
# Base de datos — PostgreSQL (Supabase / Render / Neon)
# ---------------------------------------------------------------------------
# Formato: postgresql://USER:PASSWORD@HOST:PORT/DBNAME
# Supabase: usa la URL de "Connection string" → modo "URI" en Settings → Database
# Ejemplo:  postgresql://postgres:mi_password@db.xxxx.supabase.co:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# CORS — nunca "*" con credentials=True
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# Seguridad de sesiones
# ---------------------------------------------------------------------------
COOKIE_SECURE        = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_TTL_HOURS    = int(os.getenv("SESSION_TTL_HOURS", "12"))
SESSION_COOKIE_NAME  = "foragro_session"
BCRYPT_MAX_BYTES     = 72   # límite real del algoritmo bcrypt

# ---------------------------------------------------------------------------
# Cupones
# ---------------------------------------------------------------------------
DEFAULT_COUPON_DISCOUNT     = float(os.getenv("DEFAULT_COUPON_DISCOUNT", "5.0"))
DEFAULT_COUPON_EXPIRES_DAYS = int(os.getenv("DEFAULT_COUPON_EXPIRES_DAYS", "7"))

# ---------------------------------------------------------------------------
# Imágenes
# ---------------------------------------------------------------------------
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

# ---------------------------------------------------------------------------
# Multi-PDV
# ---------------------------------------------------------------------------
# Código del PDV predeterminado cuando no se especifica en la URL
DEFAULT_PDV_CODE = os.getenv("DEFAULT_PDV_CODE", "PRINCIPAL")