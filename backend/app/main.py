"""
Punto de entrada de la aplicación FastAPI v2.0.
Registra todos los routers, middleware CORS, archivos estáticos y lifecycle events.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import ALLOWED_ORIGINS, logger
from app.database import init_db
from app.routers import auth, dashboard, public
from app.routers import pdv, admin, whatsapp_webhook

# ---------------------------------------------------------------------------
# Metadatos de grupos de endpoints (aparecen en Swagger UI y API Explorer)
# ---------------------------------------------------------------------------

_TAGS_METADATA = [
    {
        "name": "public",
        "description": (
            "🌾 **Kiosco POP** — Endpoints públicos de la tablet en punto de venta. "
            "Chat con IA (WebSocket y HTTP), síntesis de voz TTS, transcripción Whisper, "
            "diagnóstico por foto, catálogo de productos, registro de productor y envío por WhatsApp."
        ),
    },
    {
        "name": "auth",
        "description": (
            "🔑 **Autenticación** — Login, logout y consulta de sesión activa del dashboard. "
            "Usa cookie HTTP-only firmada con bcrypt + SHA-256."
        ),
    },
    {
        "name": "dashboard",
        "description": (
            "📊 **Dashboard CRM** — Endpoints protegidos para el panel de gerencia. "
            "KPIs globales, CRM de productores con filtros avanzados, inventario de bodega, "
            "campañas publicitarias, cupones manuales y estadísticas de agrónomos."
        ),
    },
    {
        "name": "pdv",
        "description": (
            "🏪 **Puntos de Venta** — CRUD completo de PDVs y asignación de agrónomos. "
            "Métricas individuales por sucursal, historial de leads por punto de venta."
        ),
    },
    {
        "name": "admin",
        "description": (
            "⚙️ **Panel Admin** — Gestión avanzada sin código. Catálogo de productos (CRUD), "
            "banco de fotos fitosanitarias, métricas personalizadas, reportes dinámicos CSV/JSON "
            "y bandeja de escaladas IA → agrónomo."
        ),
    },
    {
        "name": "whatsapp",
        "description": (
            "📱 **WhatsApp** — Webhook de Meta Cloud API para conversaciones entrantes del productor. "
            "Historial de conversaciones por número y lista de chats activos para el dashboard."
        ),
    },
]

# ---------------------------------------------------------------------------
# Aplicación principal
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Inge. Agro IA — FORAGRO v2.0",
    description=(
        "## Sistema integral de asesoría agrícola con IA\n\n"
        "Red multi-punto de asesoría agrícola con IA conversacional, WhatsApp, diagnóstico visual "
        "y CRM centralizado para tiendas y agroveterinarias FORAGRO en Honduras.\n\n"
        "### Accesos rápidos\n"
        "- 🌾 [Kiosco POP](/kiosk/?pdv=PRINCIPAL)\n"
        "- 📊 [Dashboard CRM](/dashboard/)\n"
        "- ⚙️ [Panel Admin](/admin-panel/)\n"
        "- 🔍 [API Explorer](/api-explorer)\n\n"
        "### Autenticación\n"
        "Los endpoints protegidos requieren sesión activa. Usa `POST /api/login` primero "
        "y la cookie `foragro_session` se enviará automáticamente."
    ),
    version="2.0.0",
    openapi_tags=_TAGS_METADATA,
    docs_url=None,    # deshabilitamos docs por defecto para usar el nuestro personalizado
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS (nunca "*" con credentials=True)
# ---------------------------------------------------------------------------

if not ALLOWED_ORIGINS:
    logger.warning(
        "ALLOWED_ORIGINS no configurado. Solo se aceptarán solicitudes de localhost. "
        "Define: ALLOWED_ORIGINS=https://kiosko.foragro.hn,https://dashboard.foragro.hn"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Routers — API
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(dashboard.router)
app.include_router(pdv.router)
app.include_router(admin.router)
app.include_router(whatsapp_webhook.router)

# ---------------------------------------------------------------------------
# Archivos estáticos (Kiosco, Dashboard, Panel Admin, Shared)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_static_mounts = [
    ("/kiosk",        BASE_DIR / "kiosk",     "kiosk"),
    ("/dashboard",    BASE_DIR / "dashboard",  "dashboard"),
    ("/admin-panel",  BASE_DIR / "admin",      "admin"),
    ("/shared",       BASE_DIR / "shared",     "shared"),
]

for path, directory, name in _static_mounts:
    if directory.exists():
        app.mount(path, StaticFiles(directory=str(directory), html=True), name=name)
    else:
        logger.warning("Directorio estático '%s' no encontrado: %s", name, directory)

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    init_db()
    logger.info("✅ FORAGRO v2.0 — Base de datos inicializada y routers cargados.")


# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse(url="/kiosk/")


@app.get("/health")
def health():
    """Endpoint de salud para monitoreo y load balancers."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Swagger UI personalizado con branding FORAGRO."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="FORAGRO v2.0 — API Docs",
        swagger_favicon_url="https://em-content.zobj.net/source/twitter/376/seedling_1f331.png",
        swagger_ui_parameters={
            "deepLinking": True,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
            "defaultModelsExpandDepth": 0,
        },
    )


@app.get("/api-explorer", include_in_schema=False)
async def api_explorer_redirect():
    """Redirige al API Explorer HTML personalizado."""
    return RedirectResponse(url="/admin-panel/api-explorer.html")


# ---------------------------------------------------------------------------
# Ejecución directa (desarrollo)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("🌱 Inge. Agro IA — FORAGRO v2.0")
    print("   API:          http://localhost:8000")
    print("   Swagger Docs: http://localhost:8000/docs")
    print("   API Explorer: http://localhost:8000/api-explorer")
    print("   ReDoc:        http://localhost:8000/redoc")
    print("   Kiosco:       http://localhost:8000/kiosk/?pdv=PRINCIPAL")
    print("   Dashboard:    http://localhost:8000/dashboard/")
    print("   Admin:        http://localhost:8000/admin-panel/")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)