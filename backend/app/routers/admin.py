"""
Panel de Administración sin código — FORAGRO.

Permite a gerencia y agrónomos gestionar datos del sistema sin escribir código:
  - Productos e inventario (CRUD completo)
  - Referencias fitosanitarias (CRUD)
  - Métricas personalizadas (configuración sin SQL visible)
  - Reportes dinámicos (CSV / JSON)
  - Bandeja de escaladas (alertas IA → agrónomo)

Todos los endpoints requieren sesión de dashboard.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import require_auth
from app.database import get_db
from app.models import (
    AdminMetricRequest,
    DiseaseReferenceRequest,
    EscaladaResolveRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Productos — CRUD completo
# ---------------------------------------------------------------------------

@router.post("/products", status_code=201)
def create_product(req: ProductCreateRequest, username: str = Depends(require_auth)):
    """Agrega un nuevo producto al catálogo e inventario FORAGRO."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM products WHERE sku = %s", (req.sku,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Ya existe un producto con SKU '{req.sku}'.")

        cursor = conn.execute(
            """INSERT INTO products
               (sku, nombre, categoria, ingrediente_activo, cultivos, problemas, dosis,
                precio_hnl, stock, unidad, imagen_url, descripcion)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                req.sku, req.nombre, req.categoria, req.ingrediente_activo or "",
                req.cultivos or "", req.problemas or "", req.dosis or "",
                req.precio_hnl, req.stock, req.unidad,
                req.imagen_url or "", req.descripcion or "",
            ),
        )
        conn.commit()
    return {"status": "created", "product_id": cursor.lastrowid}


@router.put("/products/{product_id}")
def update_product(
    product_id: int, req: ProductUpdateRequest, username: str = Depends(require_auth)
):
    """Actualiza cualquier campo de un producto existente."""
    updates, params = [], []
    field_map = {
        "nombre": req.nombre, "categoria": req.categoria,
        "ingrediente_activo": req.ingrediente_activo, "cultivos": req.cultivos,
        "problemas": req.problemas, "dosis": req.dosis,
        "precio_hnl": req.precio_hnl, "stock": req.stock,
        "unidad": req.unidad, "imagen_url": req.imagen_url, "descripcion": req.descripcion,
    }
    for field, value in field_map.items():
        if value is not None:
            updates.append(f"{field} = %s")
            params.append(value)

    if not updates:
        return {"status": "no_changes"}

    params.append(product_id)
    with get_db() as conn:
        prod = conn.execute("SELECT id FROM products WHERE id = %s", (product_id,)).fetchone()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")
        conn.execute(f"UPDATE products SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    return {"status": "updated", "product_id": product_id}


@router.delete("/products/{product_id}")
def delete_product(product_id: int, username: str = Depends(require_auth)):
    """Elimina un producto del catálogo."""
    with get_db() as conn:
        prod = conn.execute("SELECT id FROM products WHERE id = %s", (product_id,)).fetchone()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")
        conn.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
    return {"status": "deleted", "product_id": product_id}


# ---------------------------------------------------------------------------
# Referencias Fitosanitarias — CRUD
# ---------------------------------------------------------------------------

@router.post("/disease-references", status_code=201)
def create_disease_reference(req: DiseaseReferenceRequest, username: str = Depends(require_auth)):
    """Agrega una nueva referencia fotográfica de enfermedad o plaga."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO disease_references
               (cultivo, problema, nombre_enfermedad, nombre_cientifico,
                descripcion_sintomas, foto_url, productos_recomendados_ids)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                req.cultivo, req.problema, req.nombre_enfermedad,
                req.nombre_cientifico or "", req.descripcion_sintomas or "",
                req.foto_url or "", req.productos_recomendados_ids or "",
            ),
        )
        conn.commit()
    return {"status": "created", "reference_id": cursor.lastrowid}


@router.put("/disease-references/{ref_id}")
def update_disease_reference(
    ref_id: int, req: DiseaseReferenceRequest, username: str = Depends(require_auth)
):
    with get_db() as conn:
        ref = conn.execute("SELECT id FROM disease_references WHERE id = %s", (ref_id,)).fetchone()
        if not ref:
            raise HTTPException(status_code=404, detail="Referencia no encontrada.")
        conn.execute(
            """UPDATE disease_references SET
               cultivo = %s, problema = %s, nombre_enfermedad = %s, nombre_cientifico = %s,
               descripcion_sintomas = %s, foto_url = %s, productos_recomendados_ids = %s
               WHERE id = %s""",
            (
                req.cultivo, req.problema, req.nombre_enfermedad,
                req.nombre_cientifico or "", req.descripcion_sintomas or "",
                req.foto_url or "", req.productos_recomendados_ids or "", ref_id,
            ),
        )
        conn.commit()
    return {"status": "updated", "reference_id": ref_id}


@router.delete("/disease-references/{ref_id}")
def delete_disease_reference(ref_id: int, username: str = Depends(require_auth)):
    with get_db() as conn:
        conn.execute("DELETE FROM disease_references WHERE id = %s", (ref_id,))
        conn.commit()
    return {"status": "deleted", "reference_id": ref_id}


# ---------------------------------------------------------------------------
# Métricas Personalizadas (sin código)
# ---------------------------------------------------------------------------

# Mapa de métricas permitidas → query SQL segura (evita SQL injection por diseño)
_METRIC_QUERIES = {
    "leads_por_cultivo":      "SELECT cultivo as label, COUNT(*) as value FROM leads {WHERE} GROUP BY cultivo ORDER BY value DESC LIMIT 10",
    "leads_por_zona":         "SELECT zona as label, COUNT(*) as value FROM leads {WHERE} GROUP BY zona ORDER BY value DESC LIMIT 10",
    "leads_por_pdv":          "SELECT pdv.nombre as label, COUNT(l.id) as value FROM leads l LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id {WHERE_L} GROUP BY pdv.nombre ORDER BY value DESC",
    "leads_por_canal":        "SELECT canal as label, COUNT(*) as value FROM leads {WHERE} GROUP BY canal ORDER BY value DESC",
    "leads_por_problema":     "SELECT problema as label, COUNT(*) as value FROM leads {WHERE} WHERE problema != '' GROUP BY problema ORDER BY value DESC LIMIT 10",
    "manzanas_por_zona":      "SELECT zona as label, SUM(CAST(manzanas AS REAL)) as value FROM leads {WHERE} WHERE manzanas != '' GROUP BY zona ORDER BY value DESC",
    "escaladas_por_agronomo": "SELECT u.nombre as label, COUNT(e.id) as value FROM agronomo_escaladas e JOIN users u ON e.user_id = u.id {WHERE_E} GROUP BY u.nombre ORDER BY value DESC",
    "cupones_por_pdv":        "SELECT pdv.nombre as label, COUNT(c.id) as value FROM coupons c JOIN leads l ON c.lead_id = l.id LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id {WHERE_L} GROUP BY pdv.nombre ORDER BY value DESC",
    "total_leads":            "SELECT 'Total Leads' as label, COUNT(*) as value FROM leads {WHERE}",
    "total_manzanas":         "SELECT 'Manzanas Totales' as label, SUM(CAST(manzanas AS REAL)) as value FROM leads {WHERE}",
}

def _build_date_filter(filtro_fecha: str, alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    if filtro_fecha == "7d":
        return f"{prefix}created_at >= NOW() - INTERVAL '7 days'"
    if filtro_fecha == "30d":
        return f"{prefix}created_at >= NOW() - INTERVAL '30 days'"
    if filtro_fecha == "90d":
        return f"{prefix}created_at >= NOW() - INTERVAL '90 days'"
    return "1=1"


@router.get("/metrics-custom")
def list_custom_metrics(username: str = Depends(require_auth)):
    """Lista todas las métricas personalizadas configuradas."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM admin_metrics_custom WHERE activo = TRUE ORDER BY orden, id"
        ).fetchall()
    return {"metrics": [dict(r) for r in rows]}


@router.post("/metrics-custom", status_code=201)
def create_custom_metric(req: AdminMetricRequest, username: str = Depends(require_auth)):
    """Crea una nueva métrica personalizada."""
    metric_key = f"{req.metrica}_por_{req.dimension}"
    if metric_key not in _METRIC_QUERIES and req.metrica not in _METRIC_QUERIES:
        raise HTTPException(
            status_code=400,
            detail=f"Combinación de métrica/dimensión no soportada. Disponibles: {list(_METRIC_QUERIES.keys())}",
        )
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO admin_metrics_custom
               (nombre, descripcion, tipo_grafico, dimension, metrica, filtro_fecha, orden)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (req.nombre, req.descripcion, req.tipo_grafico, req.dimension,
             req.metrica, req.filtro_fecha, req.orden),
        )
        conn.commit()
    return {"status": "created", "metric_id": cursor.lastrowid}


@router.get("/metrics-custom/{metric_id}/data")
def get_custom_metric_data(metric_id: int, username: str = Depends(require_auth)):
    """Ejecuta una métrica personalizada y devuelve los datos para el gráfico."""
    with get_db() as conn:
        metric = conn.execute(
            "SELECT * FROM admin_metrics_custom WHERE id = %s AND activo = TRUE", (metric_id,)
        ).fetchone()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada.")

        metric = dict(metric)
        metric_key = f"{metric['metrica']}_por_{metric['dimension']}"
        if metric_key not in _METRIC_QUERIES:
            metric_key = metric["metrica"]
        if metric_key not in _METRIC_QUERIES:
            raise HTTPException(status_code=400, detail="Tipo de métrica no soportado.")

        date_filter = _build_date_filter(metric["filtro_fecha"])
        query = _METRIC_QUERIES[metric_key]
        # Insertar el filtro de fecha de forma segura (los parámetros se pasan por separado)
        query = query.replace("{WHERE}", f"WHERE {date_filter}")
        query = query.replace("{WHERE_L}", f"WHERE {date_filter}")
        query = query.replace("{WHERE_E}", f"WHERE {date_filter}")

        rows = conn.execute(query).fetchall()

    return {
        "metric": metric,
        "data": [dict(r) for r in rows],
    }


@router.delete("/metrics-custom/{metric_id}")
def delete_custom_metric(metric_id: int, username: str = Depends(require_auth)):
    with get_db() as conn:
        conn.execute(
            "UPDATE admin_metrics_custom SET activo = FALSE WHERE id = %s", (metric_id,)
        )
        conn.commit()
    return {"status": "deleted", "metric_id": metric_id}


# ---------------------------------------------------------------------------
# Reportes dinámicos
# ---------------------------------------------------------------------------

@router.get("/report")
def generate_report(
    tipo: str = Query(..., description="Tipo: leads | products | escaladas | whatsapp"),
    formato: str = Query("json", description="Formato: json | csv"),
    dias: int = Query(30, ge=1, le=365),
    pdv_id: Optional[int] = None,
    username: str = Depends(require_auth),
):
    """
    Genera un reporte dinámico del sistema.
    tipo: leads | products | escaladas | whatsapp
    formato: json | csv
    """
    date_filter = f"NOW() - INTERVAL '{dias} days'"
    rows = []
    headers = []

    with get_db() as conn:
        if tipo == "leads":
            headers = ["id", "cultivo", "zona", "manzanas", "problema", "telefono",
                       "canal", "cupon", "estado_seguimiento", "pdv_nombre", "created_at"]
            query = """
                SELECT l.id, l.cultivo, l.zona, l.manzanas, l.problema, l.telefono,
                       l.canal, l.cupon, l.estado_seguimiento,
                       pdv.nombre as pdv_nombre, l.created_at
                FROM leads l
                LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
                WHERE l.created_at >= {date_filter}
            """.replace("{date_filter}", date_filter)
            params = []
            if pdv_id:
                query += " AND l.punto_venta_id = %s"
                params.append(pdv_id)
            query += " ORDER BY l.created_at DESC"
            rows = [dict(r) for r in conn.execute(query, params).fetchall()]

        elif tipo == "products":
            headers = ["id", "sku", "nombre", "categoria", "precio_hnl", "stock", "unidad"]
            rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT id, sku, nombre, categoria, precio_hnl, stock, unidad FROM products ORDER BY categoria, nombre"
                ).fetchall()
            ]

        elif tipo == "escaladas":
            headers = ["id", "pregunta", "motivo", "estado", "pdv_nombre", "agronomo", "created_at", "respondida_at"]
            query = """
                SELECT e.id, e.pregunta, e.motivo, e.estado,
                       pdv.nombre as pdv_nombre, u.nombre as agronomo,
                       e.created_at, e.respondida_at
                FROM agronomo_escaladas e
                LEFT JOIN puntos_de_venta pdv ON e.pdv_id = pdv.id
                LEFT JOIN users u ON e.user_id = u.id
                WHERE e.created_at >= %s
                ORDER BY e.created_at DESC
            """
            cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
            rows = [dict(r) for r in conn.execute(query, (cutoff,)).fetchall()]

        elif tipo == "whatsapp":
            headers = ["telefono", "total_mensajes", "ultima_actividad", "cultivo", "zona"]
            rows = [
                dict(r)
                for r in conn.execute(
                    f"""SELECT ws.telefono, COUNT(*) as total_mensajes,
                               MAX(ws.created_at) as ultima_actividad,
                               l.cultivo, l.zona
                        FROM whatsapp_sessions ws
                        LEFT JOIN leads l ON ws.lead_id = l.id
                        WHERE ws.created_at >= NOW() - INTERVAL '{dias} days'
                        GROUP BY ws.telefono, l.cultivo, l.zona ORDER BY ultima_actividad DESC"""
                ).fetchall()
            ]
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de reporte '{tipo}' no soportado.")

    if formato == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
        filename = f"reporte_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return {"tipo": tipo, "dias": dias, "total": len(rows), "data": rows}


# ---------------------------------------------------------------------------
# Bandeja de Escaladas
# ---------------------------------------------------------------------------

@router.get("/escaladas")
def list_escaladas(
    estado: Optional[str] = Query(None, description="pendiente | respondida | ignorada"),
    pdv_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    username: str = Depends(require_auth),
):
    """Lista de escaladas (alertas IA → agrónomo) con filtros."""
    with get_db() as conn:
        query = """
            SELECT e.*, pdv.nombre as pdv_nombre, u.nombre as agronomo_nombre,
                   l.cultivo, l.zona, l.telefono, l.nombre_productor
            FROM agronomo_escaladas e
            LEFT JOIN puntos_de_venta pdv ON e.pdv_id = pdv.id
            LEFT JOIN users u ON e.user_id = u.id
            LEFT JOIN leads l ON e.lead_id = l.id
            WHERE 1=1
        """
        params = []
        if estado:
            query += " AND e.estado = %s"
            params.append(estado)
        if pdv_id:
            query += " AND e.pdv_id = %s"
            params.append(pdv_id)
        query += " ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM agronomo_escaladas WHERE 1=1"
            + (" AND estado = %s" if estado else "")
            + (" AND pdv_id = %s" if pdv_id else ""),
            [p for p in [estado, pdv_id] if p is not None],
        ).fetchone()[0]

    return {"escaladas": [dict(r) for r in rows], "total": total}


@router.put("/escaladas/{escalada_id}/resolve")
def resolve_escalada(
    escalada_id: int,
    req: EscaladaResolveRequest,
    username: str = Depends(require_auth),
):
    """Marca una escalada como respondida o ignorada y registra la respuesta del agrónomo."""
    with get_db() as conn:
        esc = conn.execute(
            "SELECT id FROM agronomo_escaladas WHERE id = %s", (escalada_id,)
        ).fetchone()
        if not esc:
            raise HTTPException(status_code=404, detail="Escalada no encontrada.")
        conn.execute(
            """UPDATE agronomo_escaladas
               SET estado = %s, respuesta = %s, respondida_at = CURRENT_TIMESTAMP
               WHERE id = %s""",
            (req.estado, req.respuesta[:2000], escalada_id),
        )
        conn.commit()
    return {"status": "resolved", "escalada_id": escalada_id}


# ---------------------------------------------------------------------------
# Información de tablas disponibles (para interfaz de métricas custom)
# ---------------------------------------------------------------------------

@router.get("/schema-info")
def get_schema_info(username: str = Depends(require_auth)):
    """Devuelve dimensiones y métricas disponibles para el panel de métricas custom."""
    return {
        "dimensiones": [
            {"key": "cultivo",    "label": "Cultivo"},
            {"key": "zona",       "label": "Departamento / Zona"},
            {"key": "pdv",        "label": "Punto de Venta"},
            {"key": "canal",      "label": "Canal publicitario"},
            {"key": "problema",   "label": "Problema / Plaga"},
            {"key": "agronomo",   "label": "Agrónomo"},
        ],
        "metricas": [
            {"key": "leads",        "label": "Cantidad de Productores"},
            {"key": "manzanas",     "label": "Manzanas Totales"},
            {"key": "cupones",      "label": "Cupones Generados"},
            {"key": "escaladas",    "label": "Escaladas a Agrónomo"},
            {"key": "total_leads",  "label": "Total Global de Leads"},
            {"key": "total_manzanas", "label": "Total Global de Manzanas"},
        ],
        "filtros_fecha": [
            {"key": "7d", "label": "Últimos 7 días"},
            {"key": "30d", "label": "Últimos 30 días"},
            {"key": "90d", "label": "Últimos 90 días"},
            {"key": "all", "label": "Todo el historial"},
        ],
        "tipos_grafico": [
            {"key": "bar",    "label": "Barras"},
            {"key": "pie",    "label": "Pastel"},
            {"key": "line",   "label": "Línea"},
            {"key": "table",  "label": "Tabla"},
            {"key": "number", "label": "Número único"},
        ],
    }
