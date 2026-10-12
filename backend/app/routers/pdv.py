"""
Gestión de Puntos de Venta (PDV) y perfiles de agrónomos.

Endpoints:
  GET    /api/pdv                    — Listar PDVs
  POST   /api/pdv                    — Crear PDV
  GET    /api/pdv/{id}               — Detalle de PDV con agrónomos asignados
  PUT    /api/pdv/{id}               — Editar PDV
  DELETE /api/pdv/{id}               — Desactivar PDV
  POST   /api/pdv/{id}/agronomo      — Asignar agrónomo a PDV
  DELETE /api/pdv/{id}/agronomo/{uid}— Desasignar agrónomo
  GET    /api/pdv/{id}/metrics       — Métricas del PDV específico
  GET    /api/agrónomos              — Listar agrónomos (usuarios con rol agronomo/admin)
  PUT    /api/agrónomos/{id}         — Actualizar perfil de agrónomo
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_auth
from app.database import get_db
from app.models import PDVRequest, PDVUpdateRequest, PDVAgronomoRequest, AgronomoProfileRequest

router = APIRouter(prefix="/api", tags=["pdv"])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _resolve_pdv_or_404(conn, pdv_id: int):
    pdv = conn.execute(
        "SELECT * FROM puntos_de_venta WHERE id = %s", (pdv_id,)
    ).fetchone()
    if not pdv:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado.")
    return dict(pdv)


def _get_pdv_agronomo_ids(conn, pdv_id: int) -> list:
    rows = conn.execute(
        """SELECT pa.user_id, pa.es_responsable,
                  u.username, u.nombre, u.telefono_wa, u.especialidad, u.rol
           FROM pdv_agronomos pa
           JOIN users u ON pa.user_id = u.id
           WHERE pa.pdv_id = %s""",
        (pdv_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CRUD de Puntos de Venta
# ---------------------------------------------------------------------------

@router.get("/pdv")
def list_pdv(
    activo: Optional[bool] = None,
    username: str = Depends(require_auth),
):
    """Lista todos los puntos de venta con conteo de leads e info del agrónomo responsable."""
    with get_db() as conn:
        query = "SELECT p.* FROM puntos_de_venta p WHERE 1=1"
        params = []
        if activo is not None:
            query += " AND p.activo = %s"
            params.append(activo)
        query += " ORDER BY p.nombre ASC"
        rows = conn.execute(query, params).fetchall()

        result = []
        for row in rows:
            pdv = dict(row)
            pdv_id = pdv["id"]

            # Conteo de leads
            pdv["total_leads"] = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE punto_venta_id = %s", (pdv_id,)
            ).fetchone()[0]

            # Agrónomo responsable
            resp = conn.execute(
                """SELECT u.nombre, u.username, u.telefono_wa
                   FROM pdv_agronomos pa JOIN users u ON pa.user_id = u.id
                   WHERE pa.pdv_id = %s AND pa.es_responsable = TRUE LIMIT 1""",
                (pdv_id,),
            ).fetchone()
            pdv["agronomo_responsable"] = dict(resp) if resp else None

            result.append(pdv)

    return {"puntos_de_venta": result}


@router.post("/pdv", status_code=201)
def create_pdv(req: PDVRequest, username: str = Depends(require_auth)):
    """Crea un nuevo punto de venta."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM puntos_de_venta WHERE codigo = %s", (req.codigo.upper(),)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Ya existe un PDV con código '{req.codigo}'."
            )
        cursor = conn.execute(
            """INSERT INTO puntos_de_venta (codigo, nombre, municipio, departamento, direccion, telefono)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                req.codigo.upper(), req.nombre, req.municipio or "",
                req.departamento or "", req.direccion or "", req.telefono or "",
            ),
        )
        conn.commit()
    return {"status": "created", "pdv_id": cursor.lastrowid, "codigo": req.codigo.upper()}


@router.get("/pdv/{pdv_id}")
def get_pdv(pdv_id: int, username: str = Depends(require_auth)):
    """Detalle completo del PDV incluyendo agrónomos asignados y métricas básicas."""
    with get_db() as conn:
        pdv = _resolve_pdv_or_404(conn, pdv_id)
        pdv["agronomos"] = _get_pdv_agronomo_ids(conn, pdv_id)
        pdv["total_leads"] = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE punto_venta_id = %s", (pdv_id,)
        ).fetchone()[0]
        pdv["escaladas_pendientes"] = conn.execute(
            "SELECT COUNT(*) FROM agronomo_escaladas WHERE pdv_id = %s AND estado = 'pendiente'",
            (pdv_id,),
        ).fetchone()[0]
    return {"pdv": pdv}


@router.put("/pdv/{pdv_id}")
def update_pdv(pdv_id: int, req: PDVUpdateRequest, username: str = Depends(require_auth)):
    """Actualiza datos del PDV."""
    updates, params = [], []

    field_map = {
        "nombre": req.nombre, "municipio": req.municipio,
        "departamento": req.departamento, "direccion": req.direccion,
        "telefono": req.telefono, "activo": req.activo,
    }
    for field, value in field_map.items():
        if value is not None:
            updates.append(f"{field} = %s")
            params.append(value)

    if not updates:
        return {"status": "no_changes"}

    params.append(pdv_id)
    with get_db() as conn:
        _resolve_pdv_or_404(conn, pdv_id)
        conn.execute(
            f"UPDATE puntos_de_venta SET {', '.join(updates)} WHERE id = %s", params
        )
        conn.commit()
    return {"status": "updated", "pdv_id": pdv_id}


@router.delete("/pdv/{pdv_id}")
def deactivate_pdv(pdv_id: int, username: str = Depends(require_auth)):
    """Desactiva un PDV (no elimina datos históricos)."""
    with get_db() as conn:
        _resolve_pdv_or_404(conn, pdv_id)
        conn.execute("UPDATE puntos_de_venta SET activo = FALSE WHERE id = %s", (pdv_id,))
        conn.commit()
    return {"status": "deactivated", "pdv_id": pdv_id}


# ---------------------------------------------------------------------------
# Asignación de agrónomos a PDV
# ---------------------------------------------------------------------------

@router.post("/pdv/{pdv_id}/agronomo")
def assign_agronomo(
    pdv_id: int,
    req: PDVAgronomoRequest,
    username: str = Depends(require_auth),
):
    """Asigna un usuario/agrónomo a un PDV. Si es_responsable=True, actualiza el responsable."""
    with get_db() as conn:
        _resolve_pdv_or_404(conn, pdv_id)

        user = conn.execute("SELECT id FROM users WHERE id = %s", (req.user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        # Si va a ser responsable, quitar responsabilidad de otro
        if req.es_responsable:
            conn.execute(
                "UPDATE pdv_agronomos SET es_responsable = FALSE WHERE pdv_id = %s",
                (pdv_id,),
            )

        conn.execute(
            """INSERT INTO pdv_agronomos (pdv_id, user_id, es_responsable)
               VALUES (%s, %s, %s)
               ON CONFLICT(pdv_id, user_id) DO UPDATE SET es_responsable = excluded.es_responsable""",
            (pdv_id, req.user_id, req.es_responsable),
        )
        conn.commit()
    return {"status": "assigned", "pdv_id": pdv_id, "user_id": req.user_id}


@router.delete("/pdv/{pdv_id}/agronomo/{user_id}")
def remove_agronomo(pdv_id: int, user_id: int, username: str = Depends(require_auth)):
    """Elimina la asignación de un agrónomo a un PDV."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM pdv_agronomos WHERE pdv_id = %s AND user_id = %s",
            (pdv_id, user_id),
        )
        conn.commit()
    return {"status": "removed", "pdv_id": pdv_id, "user_id": user_id}


# ---------------------------------------------------------------------------
# Métricas por PDV
# ---------------------------------------------------------------------------

@router.get("/pdv/{pdv_id}/metrics")
def get_pdv_metrics(pdv_id: int, username: str = Depends(require_auth)):
    """KPIs detallados del punto de venta específico."""
    with get_db() as conn:
        pdv = _resolve_pdv_or_404(conn, pdv_id)

        total_leads = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE punto_venta_id = %s", (pdv_id,)
        ).fetchone()[0]

        total_manzanas_raw = conn.execute(
            "SELECT manzanas FROM leads WHERE punto_venta_id = %s AND manzanas IS NOT NULL",
            (pdv_id,),
        ).fetchall()
        total_manzanas = 0.0
        for m in total_manzanas_raw:
            try:
                total_manzanas += float(str(m[0]).replace(",", "."))
            except Exception:
                pass

        cultivos = {
            row["cultivo"]: row["c"]
            for row in conn.execute(
                "SELECT cultivo, COUNT(*) as c FROM leads WHERE punto_venta_id = %s "
                "AND cultivo IS NOT NULL GROUP BY cultivo ORDER BY c DESC LIMIT 5",
                (pdv_id,),
            ).fetchall()
        }

        problemas = {
            row["problema"]: row["c"]
            for row in conn.execute(
                "SELECT problema, COUNT(*) as c FROM leads WHERE punto_venta_id = %s "
                "AND problema IS NOT NULL AND problema != '' GROUP BY problema ORDER BY c DESC LIMIT 5",
                (pdv_id,),
            ).fetchall()
        }

        estados = {
            row["estado_seguimiento"]: row["c"]
            for row in conn.execute(
                "SELECT estado_seguimiento, COUNT(*) as c FROM leads WHERE punto_venta_id = %s "
                "GROUP BY estado_seguimiento",
                (pdv_id,),
            ).fetchall()
        }

        escaladas = conn.execute(
            "SELECT COUNT(*) FROM agronomo_escaladas WHERE pdv_id = %s", (pdv_id,)
        ).fetchone()[0]
        escaladas_pendientes = conn.execute(
            "SELECT COUNT(*) FROM agronomo_escaladas WHERE pdv_id = %s AND estado = 'pendiente'",
            (pdv_id,),
        ).fetchone()[0]

        cupones = conn.execute(
            """SELECT COUNT(DISTINCT c.id) FROM coupons c
               JOIN leads l ON c.lead_id = l.id
               WHERE l.punto_venta_id = %s""",
            (pdv_id,),
        ).fetchone()[0]

    return {
        "pdv": pdv,
        "total_leads": total_leads,
        "total_manzanas": round(total_manzanas, 1),
        "cupones_generados": cupones,
        "cultivos": cultivos,
        "problemas": problemas,
        "estados_crm": estados,
        "escaladas_total": escaladas,
        "escaladas_pendientes": escaladas_pendientes,
    }


# ---------------------------------------------------------------------------
# Gestión de perfiles de agrónomos
# ---------------------------------------------------------------------------

@router.get("/agronomos")
def list_agronomos(username: str = Depends(require_auth)):
    """Lista todos los usuarios con sus estadísticas de consultas respondidas."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, nombre, telefono_wa, especialidad, rol, created_at FROM users ORDER BY nombre"
        ).fetchall()
        result = []
        for row in rows:
            user = dict(row)
            user_id = user["id"]

            # Estadísticas de escaladas
            user["escaladas_respondidas"] = conn.execute(
                "SELECT COUNT(*) FROM agronomo_escaladas WHERE user_id = %s AND estado = 'respondida'",
                (user_id,),
            ).fetchone()[0]
            user["escaladas_pendientes"] = conn.execute(
                "SELECT COUNT(*) FROM agronomo_escaladas WHERE user_id = %s AND estado = 'pendiente'",
                (user_id,),
            ).fetchone()[0]

            # PDVs asignados
            pdvs = conn.execute(
                """SELECT p.codigo, p.nombre, pa.es_responsable
                   FROM pdv_agronomos pa JOIN puntos_de_venta p ON pa.pdv_id = p.id
                   WHERE pa.user_id = %s""",
                (user_id,),
            ).fetchall()
            user["pdvs_asignados"] = [dict(p) for p in pdvs]

            result.append(user)

    return {"agronomos": result}


@router.put("/agronomos/{user_id}")
def update_agronomo_profile(
    user_id: int,
    req: AgronomoProfileRequest,
    username: str = Depends(require_auth),
):
    """Actualiza el perfil de un agrónomo (nombre, WhatsApp, especialidad, rol)."""
    updates, params = [], []
    field_map = {
        "nombre": req.nombre, "telefono_wa": req.telefono_wa,
        "especialidad": req.especialidad, "rol": req.rol,
    }
    for field, value in field_map.items():
        if value is not None:
            updates.append(f"{field} = %s")
            params.append(value)

    if not updates:
        return {"status": "no_changes"}

    params.append(user_id)
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    return {"status": "updated", "user_id": user_id}
