"""
Endpoints protegidos del dashboard y CRM FORAGRO (requieren sesión):
  GET  /api/metrics              — KPIs globales (con filtro por PDV)
  GET  /api/leads                — CRM con filtros (incluye PDV)
  GET  /api/leads/{id}           — Detalle del lead con historial y canal
  PUT  /api/leads/{id}           — Actualizar estado / notas
  GET  /api/leads/export/csv     — Exportar a CSV (con columna PDV)
  GET  /api/inventory            — Inventario de bodega
  PUT  /api/inventory/{id}       — Ajustar stock y precio
  GET  /api/campaigns            — Rendimiento por canal publicitario
  POST /api/campaign             — Crear campaña
  POST /api/generate-coupon      — Emitir cupón manual
  GET  /api/agronomo-stats       — Estadísticas de desempeño por agrónomo
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import require_auth
from app.config import logger
from app.database import get_db
from app.models import CampaignRequest, CouponRequest, LeadUpdateRequest
from app.security import require_json_content_type
from app.services.coupon_service import create_coupon_for_lead

router = APIRouter(prefix="/api", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Métricas globales (con filtro opcional por PDV)
# ---------------------------------------------------------------------------

@router.get("/metrics")
def get_metrics(
    pdv_id: Optional[int] = None,
    username: str = Depends(require_auth),
):
    """KPIs y estadísticas completas. Si pdv_id se especifica, filtra por PDV."""
    pdv_filter = "AND punto_venta_id = %s" if pdv_id else ""
    pdv_params = [pdv_id] if pdv_id else []

    with get_db() as conn:
        total_leads = conn.execute(
            f"SELECT COUNT(*) FROM leads WHERE 1=1 {pdv_filter}", pdv_params
        ).fetchone()[0]

        total_convs = conn.execute(
            f"SELECT COUNT(DISTINCT lead_id) FROM conversations WHERE lead_id IN "
            f"(SELECT id FROM leads WHERE 1=1 {pdv_filter})",
            pdv_params,
        ).fetchone()[0]

        total_coupons = conn.execute(
            f"SELECT COUNT(*) FROM coupons WHERE used = TRUE AND lead_id IN "
            f"(SELECT id FROM leads WHERE 1=1 {pdv_filter})",
            pdv_params,
        ).fetchone()[0]

        total_generated = conn.execute(
            f"SELECT COUNT(*) FROM coupons WHERE lead_id IN "
            f"(SELECT id FROM leads WHERE 1=1 {pdv_filter})",
            pdv_params,
        ).fetchone()[0]

        # Manzanas totales
        manzanas_raw = conn.execute(
            f"SELECT manzanas FROM leads WHERE manzanas IS NOT NULL AND manzanas != '' {pdv_filter}",
            pdv_params,
        ).fetchall()
        total_manzanas = 0.0
        for m in manzanas_raw:
            try:
                total_manzanas += float(str(m[0]).replace(",", "."))
            except Exception:
                pass

        # Canales
        campaigns = {
            row["canal"]: row["c"]
            for row in conn.execute(
                f"SELECT canal, COUNT(*) as c FROM leads WHERE canal IS NOT NULL {pdv_filter} GROUP BY canal",
                pdv_params,
            ).fetchall()
        }

        # Por cultivo
        cultivos_stat = {
            row["cultivo"]: row["c"]
            for row in conn.execute(
                f"SELECT cultivo, COUNT(*) as c FROM leads WHERE cultivo IS NOT NULL {pdv_filter} "
                f"GROUP BY cultivo ORDER BY c DESC LIMIT 6",
                pdv_params,
            ).fetchall()
        }

        # Por zona
        zonas_stat = {
            row["zona"]: row["c"]
            for row in conn.execute(
                f"SELECT zona, COUNT(*) as c FROM leads WHERE zona IS NOT NULL {pdv_filter} "
                f"GROUP BY zona ORDER BY c DESC LIMIT 6",
                pdv_params,
            ).fetchall()
        }

        # Problemas más frecuentes
        problemas_stat = {
            row["problema"]: row["c"]
            for row in conn.execute(
                f"SELECT problema, COUNT(*) as c FROM leads "
                f"WHERE problema IS NOT NULL AND problema != '' {pdv_filter} "
                f"GROUP BY problema ORDER BY c DESC LIMIT 6",
                pdv_params,
            ).fetchall()
        }

        # Estados CRM
        estados_stat = {
            row["estado_seguimiento"]: row["c"]
            for row in conn.execute(
                f"SELECT estado_seguimiento, COUNT(*) as c FROM leads WHERE 1=1 {pdv_filter} "
                f"GROUP BY estado_seguimiento",
                pdv_params,
            ).fetchall()
        }

        # Últimos 15 leads
        leads = conn.execute(
            f"""SELECT l.id, l.cultivo, l.zona, l.manzanas, l.fecha_siembra, l.problema,
                      l.historial, l.canal, l.telefono, l.cupon, l.recomendacion,
                      l.productos_sugeridos, l.estado_seguimiento, l.notas_seguimiento,
                      l.nombre_productor, l.created_at,
                      pdv.nombre as pdv_nombre, pdv.codigo as pdv_codigo
               FROM leads l
               LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
               WHERE 1=1 {pdv_filter}
               ORDER BY l.created_at DESC LIMIT 15""",
            pdv_params,
        ).fetchall()

        # Escaladas pendientes
        escaladas_pendientes = conn.execute(
            "SELECT COUNT(*) FROM agronomo_escaladas WHERE estado = 'pendiente'"
        ).fetchone()[0]

        # Conversaciones WhatsApp activas (últimas 24h)
        wa_activas = conn.execute(
            "SELECT COUNT(DISTINCT telefono) FROM whatsapp_sessions "
            "WHERE created_at >= NOW() - INTERVAL '24 hours'"
        ).fetchone()[0]

    conv_rate = round((total_generated / max(1, total_leads)) * 100, 1)

    return {
        "leads": total_leads,
        "conversations": total_convs,
        "coupons": total_coupons,
        "coupons_generated": total_generated,
        "total_manzanas": round(total_manzanas, 1),
        "conversion_rate": conv_rate,
        "campaigns": campaigns,
        "cultivos": cultivos_stat,
        "zonas": zonas_stat,
        "problemas": problemas_stat,
        "estados_crm": estados_stat,
        "leads_list": [dict(r) for r in leads],
        "escaladas_pendientes": escaladas_pendientes,
        "wa_activas_24h": wa_activas,
    }


# ---------------------------------------------------------------------------
# CRM de Leads
# ---------------------------------------------------------------------------

@router.get("/leads")
def get_leads(
    search: Optional[str] = None,
    cultivo: Optional[str] = None,
    zona: Optional[str] = None,
    estado: Optional[str] = None,
    pdv_id: Optional[int] = None,
    canal: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    username: str = Depends(require_auth),
):
    """Consulta avanzada del CRM con filtros múltiples incluyendo PDV y canal."""
    with get_db() as conn:
        query = """
            SELECT l.*, pdv.nombre as pdv_nombre, pdv.codigo as pdv_codigo
            FROM leads l
            LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (l.telefono LIKE %s OR l.cultivo LIKE %s OR l.zona LIKE %s OR l.problema LIKE %s OR l.nombre_productor LIKE %s)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s, s])
        if cultivo:
            query += " AND l.cultivo = %s"
            params.append(cultivo)
        if zona:
            query += " AND l.zona = %s"
            params.append(zona)
        if estado:
            query += " AND l.estado_seguimiento = %s"
            params.append(estado)
        if pdv_id:
            query += " AND l.punto_venta_id = %s"
            params.append(pdv_id)
        if canal:
            query += " AND l.canal = %s"
            params.append(canal)

        count_q = query.replace(
            "SELECT l.*, pdv.nombre as pdv_nombre, pdv.codigo as pdv_codigo",
            "SELECT COUNT(*)",
        )
        total_matching = conn.execute(count_q, params).fetchone()[0]

        query += " ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()

    return {
        "leads": [dict(r) for r in rows],
        "total": total_matching,
        "limit": limit,
        "offset": offset,
    }


@router.get("/leads/export/csv")
def export_leads_csv(
    pdv_id: Optional[int] = None,
    username: str = Depends(require_auth),
):
    """Exporta leads a CSV con columna PDV, compatible con Excel."""
    with get_db() as conn:
        query = """
            SELECT l.*, pdv.nombre as pdv_nombre
            FROM leads l
            LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
            WHERE 1=1
        """
        params = []
        if pdv_id:
            query += " AND l.punto_venta_id = %s"
            params.append(pdv_id)
        query += " ORDER BY l.created_at DESC"
        rows = conn.execute(query, params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, dialect="excel")
    writer.writerow([
        "ID", "Fecha", "Punto de Venta", "Nombre Productor", "Cultivo", "Zona",
        "Manzanas", "Fecha Siembra", "Problema", "Historial", "Teléfono",
        "Canal Atribución", "Cupón", "Recomendación", "Productos Sugeridos",
        "Estado Seguimiento", "Notas Agrónomo", "Agrónomo Asignado",
    ])
    for r in rows:
        writer.writerow([
            r["id"], r["created_at"], r["pdv_nombre"] or "", r["nombre_productor"] or "",
            r["cultivo"], r["zona"], r["manzanas"] or "", r["fecha_siembra"] or "",
            r["problema"] or "", r["historial"] or "", r["telefono"] or "",
            r["canal"] or "", r["cupon"] or "", r["recomendacion"] or "",
            r["productos_sugeridos"] or "", r["estado_seguimiento"] or "Nuevo",
            r["notas_seguimiento"] or "", r["agronomo_asignado"] or "",
        ])

    output.seek(0)
    filename = f"leads_foragro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/leads/{lead_id}")
def get_lead_detail(lead_id: int, username: str = Depends(require_auth)):
    """Detalle del lead con historial completo (kiosco + WhatsApp)."""
    with get_db() as conn:
        lead = conn.execute(
            """SELECT l.*, pdv.nombre as pdv_nombre, pdv.codigo as pdv_codigo
               FROM leads l
               LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
               WHERE l.id = %s""",
            (lead_id,),
        ).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead no encontrado.")

        chat_history = conn.execute(
            "SELECT role, message, canal, created_at FROM conversations WHERE lead_id = %s ORDER BY id ASC",
            (lead_id,),
        ).fetchall()

        wa_history = conn.execute(
            "SELECT role, message, created_at FROM whatsapp_sessions WHERE lead_id = %s ORDER BY id ASC",
            (lead_id,),
        ).fetchall()

        escaladas = conn.execute(
            "SELECT * FROM agronomo_escaladas WHERE lead_id = %s ORDER BY created_at DESC",
            (lead_id,),
        ).fetchall()

    return {
        "lead": dict(lead),
        "conversations": [dict(c) for c in chat_history],
        "whatsapp_history": [dict(w) for w in wa_history],
        "escaladas": [dict(e) for e in escaladas],
    }


@router.put("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    req: LeadUpdateRequest,
    username: str = Depends(require_auth),
    _ct=Depends(require_json_content_type),
):
    """Actualiza estado de seguimiento, notas y agrónomo asignado."""
    updates, params = [], []
    if req.estado_seguimiento is not None:
        updates.append("estado_seguimiento = %s")
        params.append(req.estado_seguimiento)
    if req.notas_seguimiento is not None:
        updates.append("notas_seguimiento = %s")
        params.append(req.notas_seguimiento)
    if req.agronomo_asignado is not None:
        updates.append("agronomo_asignado = %s")
        params.append(req.agronomo_asignado)

    if not updates:
        return {"status": "no_changes"}

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(lead_id)

    with get_db() as conn:
        lead = conn.execute("SELECT id FROM leads WHERE id = %s", (lead_id,)).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead no encontrado.")
        conn.execute(f"UPDATE leads SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    return {"status": "updated", "lead_id": lead_id}


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------

@router.get("/inventory")
def get_inventory(username: str = Depends(require_auth)):
    """Catálogo completo de productos con stock en bodega."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY categoria, nombre ASC").fetchall()
    return {"products": [dict(r) for r in rows]}


@router.put("/inventory/{product_id}")
def update_product_stock(
    product_id: int,
    stock: int = Query(..., ge=0),
    precio_hnl: Optional[float] = Query(None, ge=0),
    username: str = Depends(require_auth),
):
    """Ajuste rápido de stock y precio desde el dashboard."""
    with get_db() as conn:
        prod = conn.execute("SELECT id FROM products WHERE id = %s", (product_id,)).fetchone()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")
        if precio_hnl is not None:
            conn.execute(
                "UPDATE products SET stock = %s, precio_hnl = %s WHERE id = %s",
                (stock, precio_hnl, product_id),
            )
        else:
            conn.execute("UPDATE products SET stock = %s WHERE id = %s", (stock, product_id))
        conn.commit()
    return {"status": "updated", "product_id": product_id, "stock": stock}


# ---------------------------------------------------------------------------
# Campañas publicitarias
# ---------------------------------------------------------------------------

@router.get("/campaigns")
def get_campaigns(username: str = Depends(require_auth)):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT canal, COUNT(*) as leads,
                      SUM(CASE WHEN cupon IS NOT NULL THEN 1 ELSE 0 END) as coupons
               FROM leads WHERE canal IS NOT NULL GROUP BY canal"""
        ).fetchall()
    return {"campaigns": [dict(r) for r in rows]}


@router.post("/campaign")
def create_campaign(
    req: CampaignRequest,
    username: str = Depends(require_auth),
    _ct=Depends(require_json_content_type),
):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO campaigns (name, channel, start_date, end_date, budget) VALUES (%s, %s, %s, %s, %s)",
            (
                req.name, req.channel,
                datetime.now().date(),
                (datetime.now() + timedelta(days=30)).date(),
                req.budget,
            ),
        )
        conn.commit()
    return {"status": "created", "campaign_id": cursor.lastrowid}


# ---------------------------------------------------------------------------
# Cupones
# ---------------------------------------------------------------------------

@router.post("/generate-coupon")
def generate_coupon(
    req: CouponRequest,
    username: str = Depends(require_auth),
    _ct=Depends(require_json_content_type),
):
    with get_db() as conn:
        lead = conn.execute("SELECT id FROM leads WHERE id = %s", (req.lead_id,)).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado.")
    discount = max(1.0, min(req.discount_percent, 20.0))
    expires_days = max(1, min(req.expires_days, 30))
    coupon = create_coupon_for_lead(req.lead_id, discount, expires_days)
    return {**coupon, "status": "active"}


# ---------------------------------------------------------------------------
# Estadísticas de desempeño de agrónomos
# ---------------------------------------------------------------------------

@router.get("/agronomo-stats")
def get_agronomo_stats(username: str = Depends(require_auth)):
    """
    Estadísticas de desempeño por agrónomo:
    consultas escaladas respondidas, tiempo promedio de respuesta, PDVs asignados.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, nombre, telefono_wa, especialidad, rol FROM users ORDER BY nombre"
        ).fetchall()

        result = []
        for row in rows:
            u = dict(row)
            uid = u["id"]

            # Escaladas por estado
            u["escaladas_respondidas"] = conn.execute(
                "SELECT COUNT(*) FROM agronomo_escaladas WHERE user_id = %s AND estado = 'respondida'",
                (uid,),
            ).fetchone()[0]
            u["escaladas_pendientes"] = conn.execute(
                "SELECT COUNT(*) FROM agronomo_escaladas WHERE user_id = %s AND estado = 'pendiente'",
                (uid,),
            ).fetchone()[0]
            u["escaladas_total"] = conn.execute(
                "SELECT COUNT(*) FROM agronomo_escaladas WHERE user_id = %s", (uid,)
            ).fetchone()[0]

            # Tiempo promedio de respuesta (horas)
            avg_resp = conn.execute(
                """SELECT AVG(
                       EXTRACT(EPOCH FROM (respondida_at - created_at)) / 3600.0
                   ) as avg_hours
                   FROM agronomo_escaladas
                   WHERE user_id = %s AND estado = 'respondida' AND respondida_at IS NOT NULL""",
                (uid,),
            ).fetchone()["avg_hours"]
            u["tiempo_respuesta_horas"] = round(avg_resp, 1) if avg_resp else None

            # PDVs responsable
            pdvs = conn.execute(
                """SELECT p.codigo, p.nombre, pa.es_responsable
                   FROM pdv_agronomos pa JOIN puntos_de_venta p ON pa.pdv_id = p.id
                   WHERE pa.user_id = %s""",
                (uid,),
            ).fetchall()
            u["pdvs"] = [dict(p) for p in pdvs]

            result.append(u)

    return {"agronomos": result}