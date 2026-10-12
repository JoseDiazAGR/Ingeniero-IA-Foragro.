"""
Gestión de conexiones PostgreSQL mediante pool de conexiones.
Compatible con Supabase, Render PostgreSQL, Neon y cualquier proveedor PostgreSQL estándar.
"""

import sys
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app.config import DATABASE_URL, logger

# ---------------------------------------------------------------------------
# Pool de conexiones — reutiliza conexiones entre requests (eficiente y seguro)
# ---------------------------------------------------------------------------
# min_conn=1  → siempre tiene al menos 1 conexión lista
# max_conn=10 → suficiente para el plan Free/Starter de Supabase (max 60 conexiones)
# Ajustar max_conn si se contrata un plan superior.

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _init_pool():
    global _pool
    if not DATABASE_URL:
        logger.error(
            "DATABASE_URL no configurada. "
            "Agrega la variable de entorno en .env o en Render/Supabase."
        )
        sys.exit(1)
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DATABASE_URL,
        # Supabase usa SSL en producción — psycopg2 lo detecta automáticamente
        # desde la URL (sslmode=require). No hace falta parámetro extra.
    )
    logger.info("✅ Pool de conexiones PostgreSQL inicializado.")


@contextmanager
def get_db():
    """Context manager que entrega una conexión del pool con cursor de diccionarios.

    Uso:
        with get_db() as conn:
            row = conn.execute("SELECT ...", (param,)).fetchone()
            # row["campo"] o row[0]

    La conexión se devuelve al pool al salir del bloque (commit/rollback automáticos
    si no se hizo commit explícito). Los routers existentes hacen conn.commit()
    explícitamente — esto es compatible y seguro.
    """
    if _pool is None:
        raise RuntimeError("Pool de BD no inicializado. Llama a init_db() primero.")

    conn = _pool.getconn()
    # Usamos un wrapper fino para mantener la API idéntica a SQLite:
    # conn.execute(sql, params) y conn.commit()
    try:
        yield _PgConnWrapper(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


class _PgConnWrapper:
    """Adapta psycopg2 para que la API sea idéntica a sqlite3.Connection.

    Esto permite que todos los routers existentes (conn.execute, conn.commit,
    row["campo"]) funcionen sin cambios de estructura.
    """

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql: str, params=()) -> "_PgCursorWrapper":
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(sql, params)
        last_id = None
        if sql.lstrip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            last_id = self._fetch_lastval()
        return _PgCursorWrapper(cur, last_id)

    def _fetch_lastval(self):
        """Obtiene el último ID SERIAL generado en esta conexión (equivalente a
        sqlite3.Cursor.lastrowid). Se ejecuta dentro de un SAVEPOINT para que, si la
        tabla no usa SERIAL (ej. sessions), el error no aborte la transacción."""
        cur = self._conn.cursor()
        try:
            cur.execute("SAVEPOINT _lastval_sp")
            try:
                cur.execute("SELECT lastval()")
                value = cur.fetchone()[0]
                cur.execute("RELEASE SAVEPOINT _lastval_sp")
                return value
            except psycopg2.Error:
                cur.execute("ROLLBACK TO SAVEPOINT _lastval_sp")
                return None
        finally:
            cur.close()

    def executemany(self, sql: str, seq_of_params):
        cur = self._conn.cursor()
        cur.executemany(sql, seq_of_params)
        cur.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    # Permite usar: with get_db() as conn: conn.close() sin romper nada
    def close(self):
        pass  # El pool gestiona el cierre real


class _PgCursorWrapper:
    """Envuelve psycopg2.cursor para imitar la API de sqlite3.Cursor."""

    def __init__(self, cur, last_id=None):
        self._cur = cur
        self._last_id = last_id

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        # ID generado por el último INSERT (obtenido con lastval() al ejecutarlo).
        # Se calcula en execute() porque varios routers leen este valor después
        # de que la conexión ya fue devuelta al pool.
        return self._last_id

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur)

    def __getitem__(self, key):
        return self._cur[key]


# ---------------------------------------------------------------------------
# Esquema de base de datos — DDL completo para PostgreSQL
# ---------------------------------------------------------------------------
# Diferencias respecto a SQLite:
#  - SERIAL PRIMARY KEY  en lugar de INTEGER PRIMARY KEY AUTOINCREMENT
#  - BOOLEAN nativo (no INTEGER 0/1)
#  - Parámetros con %s en lugar de ?

_SCHEMA_SQL = """
-- Tabla de productores (CRM core)
CREATE TABLE IF NOT EXISTS leads (
    id                  SERIAL PRIMARY KEY,
    cultivo             TEXT,
    zona                TEXT,
    manzanas            TEXT,
    fecha_siembra       TEXT,
    problema            TEXT,
    historial           TEXT,
    canal               TEXT,
    telefono            TEXT,
    cupon               TEXT,
    recomendacion       TEXT,
    productos_sugeridos TEXT,
    estado_seguimiento  TEXT DEFAULT 'Nuevo',
    notas_seguimiento   TEXT DEFAULT '',
    agronomo_asignado   TEXT DEFAULT '',
    punto_venta_id      INTEGER,
    nombre_productor    TEXT DEFAULT '',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historial de conversaciones del kiosco
CREATE TABLE IF NOT EXISTS conversations (
    id          SERIAL PRIMARY KEY,
    lead_id     INTEGER,
    role        TEXT,
    message     TEXT,
    canal       TEXT DEFAULT 'kiosk',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cupones de descuento
CREATE TABLE IF NOT EXISTS coupons (
    id               SERIAL PRIMARY KEY,
    code             TEXT UNIQUE,
    discount_percent REAL DEFAULT 5.0,
    used             BOOLEAN DEFAULT FALSE,
    lead_id          INTEGER,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at       TIMESTAMP
);

-- Campañas publicitarias
CREATE TABLE IF NOT EXISTS campaigns (
    id               SERIAL PRIMARY KEY,
    name             TEXT,
    channel          TEXT,
    start_date       DATE,
    end_date         DATE,
    budget           REAL,
    leads_generated  INTEGER DEFAULT 0,
    conversions      INTEGER DEFAULT 0
);

-- Catálogo de productos FORAGRO
CREATE TABLE IF NOT EXISTS products (
    id                  SERIAL PRIMARY KEY,
    sku                 TEXT UNIQUE NOT NULL,
    nombre              TEXT NOT NULL,
    categoria           TEXT NOT NULL,
    ingrediente_activo  TEXT,
    cultivos            TEXT,
    problemas           TEXT,
    dosis               TEXT,
    precio_hnl          REAL NOT NULL DEFAULT 0.0,
    stock               INTEGER NOT NULL DEFAULT 0,
    unidad              TEXT DEFAULT 'Unidad',
    imagen_url          TEXT,
    descripcion         TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Banco de fotos fitosanitarias
CREATE TABLE IF NOT EXISTS disease_references (
    id                          SERIAL PRIMARY KEY,
    cultivo                     TEXT NOT NULL,
    problema                    TEXT NOT NULL,
    nombre_enfermedad           TEXT NOT NULL,
    nombre_cientifico           TEXT,
    descripcion_sintomas        TEXT,
    foto_url                    TEXT,
    productos_recomendados_ids  TEXT,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usuarios del dashboard
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    telefono_wa   TEXT DEFAULT '',
    nombre        TEXT DEFAULT '',
    especialidad  TEXT DEFAULT '',
    rol           TEXT DEFAULT 'admin',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sesiones del dashboard (cookie httponly)
CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP NOT NULL
);

-- Puntos de venta
CREATE TABLE IF NOT EXISTS puntos_de_venta (
    id           SERIAL PRIMARY KEY,
    codigo       TEXT UNIQUE NOT NULL,
    nombre       TEXT NOT NULL,
    municipio    TEXT DEFAULT '',
    departamento TEXT DEFAULT '',
    direccion    TEXT DEFAULT '',
    telefono     TEXT DEFAULT '',
    activo       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relación PDV ↔ Agrónomos (muchos a muchos)
CREATE TABLE IF NOT EXISTS pdv_agronomos (
    id             SERIAL PRIMARY KEY,
    pdv_id         INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    es_responsable BOOLEAN DEFAULT FALSE,
    UNIQUE (pdv_id, user_id)
);

-- Escaladas IA → Agrónomo
CREATE TABLE IF NOT EXISTS agronomo_escaladas (
    id             SERIAL PRIMARY KEY,
    lead_id        INTEGER,
    pdv_id         INTEGER,
    user_id        INTEGER,
    pregunta       TEXT NOT NULL,
    motivo         TEXT DEFAULT '',
    respuesta      TEXT DEFAULT '',
    estado         TEXT DEFAULT 'pendiente',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    respondida_at  TIMESTAMP
);

-- Conversaciones WhatsApp entrantes
CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    id             SERIAL PRIMARY KEY,
    telefono       TEXT NOT NULL,
    lead_id        INTEGER,
    role           TEXT NOT NULL,
    message        TEXT NOT NULL,
    pdv_origen_id  INTEGER,
    wa_message_id  TEXT DEFAULT '',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_wa_sessions_telefono ON whatsapp_sessions(telefono);

-- Métricas personalizadas del panel admin
CREATE TABLE IF NOT EXISTS admin_metrics_custom (
    id           SERIAL PRIMARY KEY,
    nombre       TEXT NOT NULL,
    descripcion  TEXT DEFAULT '',
    tipo_grafico TEXT DEFAULT 'bar',
    dimension    TEXT DEFAULT 'cultivo',
    metrica      TEXT DEFAULT 'leads',
    filtro_fecha TEXT DEFAULT '30d',
    orden        INTEGER DEFAULT 0,
    activo       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    """Inicializa el pool, el esquema PostgreSQL y siembra el catálogo si está vacío."""
    from app.data.seed_catalog import seed_database_if_empty

    _init_pool()

    with get_db() as conn:
        conn.execute(_SCHEMA_SQL)
        conn.commit()
        seed_database_if_empty(conn)

    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        has_users = row["cnt"] if row else 0

    if not has_users:
        logger.warning(
            "No hay usuarios del dashboard. Créalo con: python scripts/create_admin.py"
        )
    logger.info("✅ Base de datos PostgreSQL v2.0 inicializada correctamente.")
