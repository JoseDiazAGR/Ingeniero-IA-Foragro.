"""
Webhook de WhatsApp (Meta Cloud API) — Canal independiente del kiosco.

El productor puede escribir al número de FORAGRO desde su casa y continuar
la conversación con el Inge. Agro IA, con historial persistente por teléfono.

Endpoints:
  GET  /webhook/whatsapp   — Verificación del webhook (Meta lo llama 1 vez al configurar)
  POST /webhook/whatsapp   — Mensajes entrantes del productor → IA → respuesta WA
  GET  /api/whatsapp/history/{telefono} — Historial de conversación WA (dashboard)
  GET  /api/whatsapp/conversations      — Lista de conversaciones activas (dashboard)
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response

from app.auth import require_auth
from app.config import WHATSAPP_VERIFY_TOKEN, logger
from app.database import get_db
from app.services.openai_service import chat_with_openai
from app.services.whatsapp_service import _send_text_message, parse_incoming_webhook

router = APIRouter(tags=["whatsapp"])


# ---------------------------------------------------------------------------
# Verificación del webhook (Meta llama a este GET al configurar el número)
# ---------------------------------------------------------------------------

@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta llama a este endpoint con hub.mode=subscribe para verificar la URL del webhook.
    Responde con hub.challenge si el token coincide con WHATSAPP_VERIFY_TOKEN del .env
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook de WhatsApp verificado exitosamente.")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("❌ Verificación de webhook WA fallida. Token incorrecto.")
    raise HTTPException(status_code=403, detail="Token de verificación incorrecto.")


# ---------------------------------------------------------------------------
# Procesamiento de mensajes entrantes
# ---------------------------------------------------------------------------

@router.post("/webhook/whatsapp")
async def whatsapp_webhook_receive(request: Request, background_tasks: BackgroundTasks):
    """
    Recibe mensajes entrantes de WhatsApp, los procesa con la IA y responde.
    Mantiene historial de conversación por número de teléfono.

    Flujo:
      1. Parsear payload de Meta
      2. Buscar lead existente por teléfono (o crear contexto anónimo)
      3. Cargar historial reciente de la BD
      4. Llamar a chat_with_openai con el historial
      5. Guardar mensaje + respuesta en whatsapp_sessions
      6. Enviar respuesta al productor vía WA en BackgroundTasks
    """
    try:
        payload = await request.json()
    except Exception:
        # Meta envía status updates sin body válido; retornamos 200 para no generar reintentos
        return {"status": "ok"}

    incoming = parse_incoming_webhook(payload)
    if not incoming:
        return {"status": "ok"}  # Ignorar: status updates, receipts, etc.

    telefono = incoming["from"]
    user_text = incoming["text"]
    wa_msg_id = incoming["message_id"]

    # Deduplicación por wa_message_id (si Meta reintenta)
    if wa_msg_id:
        with get_db() as conn:
            dup = conn.execute(
                "SELECT id FROM whatsapp_sessions WHERE wa_message_id = %s", (wa_msg_id,)
            ).fetchone()
            if dup:
                logger.info("Webhook WA: mensaje duplicado ignorado (%s)", wa_msg_id)
                return {"status": "already_processed"}

    logger.info("📲 WA entrante de %s: %s", telefono, user_text[:80])

    # Recuperar lead existente y contexto del PDV de origen
    lead_id = None
    punto_venta_id = None
    punto_venta_codigo = None
    cultivo = None
    zona = None

    with get_db() as conn:
        lead_row = conn.execute(
            "SELECT id, cultivo, zona, punto_venta_id FROM leads WHERE telefono = %s ORDER BY created_at DESC LIMIT 1",
            (telefono,),
        ).fetchone()
        if lead_row:
            lead_id = lead_row["id"]
            cultivo = lead_row["cultivo"]
            zona = lead_row["zona"]
            punto_venta_id = lead_row["punto_venta_id"]

        if punto_venta_id:
            pdv_row = conn.execute(
                "SELECT codigo FROM puntos_de_venta WHERE id = %s", (punto_venta_id,)
            ).fetchone()
            if pdv_row:
                punto_venta_codigo = pdv_row["codigo"]

        # Cargar últimas 10 interacciones del historial WA para contexto
        hist_rows = conn.execute(
            """SELECT role, message FROM whatsapp_sessions
               WHERE telefono = %s ORDER BY created_at DESC LIMIT 10""",
            (telefono,),
        ).fetchall()

    # Construir contexto para la IA (en orden cronológico)
    wa_context = [{"role": r["role"], "content": r["message"]} for r in reversed(hist_rows)]

    # Llamar a la IA
    ai_result = await chat_with_openai(
        message=user_text,
        context=wa_context,
        cultivo=cultivo,
        zona=zona,
        lead_id=lead_id,
        punto_venta_id=punto_venta_id,
        punto_venta_codigo=punto_venta_codigo,
    )

    reply_text = ai_result.get("reply", "Disculpa, hubo un problema procesando tu consulta. Intenta de nuevo.")
    new_lead_id = ai_result.get("lead_id") or lead_id

    # Guardar en historial WA
    with get_db() as conn:
        conn.execute(
            """INSERT INTO whatsapp_sessions (telefono, lead_id, role, message, pdv_origen_id, wa_message_id)
               VALUES (%s, %s, 'user', %s, %s, %s)""",
            (telefono, new_lead_id, user_text[:2000], punto_venta_id, wa_msg_id),
        )
        conn.execute(
            """INSERT INTO whatsapp_sessions (telefono, lead_id, role, message, pdv_origen_id)
               VALUES (%s, %s, 'assistant', %s, %s)""",
            (telefono, new_lead_id, reply_text[:2000], punto_venta_id),
        )
        # Actualizar lead_id en mensajes anteriores si recién se creó el lead
        if new_lead_id and not lead_id:
            conn.execute(
                "UPDATE whatsapp_sessions SET lead_id = %s WHERE telefono = %s AND lead_id IS NULL",
                (new_lead_id, telefono),
            )
        conn.commit()

    # Enviar respuesta al productor en background task confiable
    background_tasks.add_task(_send_text_message, telefono, reply_text)

    return {"status": "processed"}


# ---------------------------------------------------------------------------
# Endpoints del dashboard para canal WhatsApp
# ---------------------------------------------------------------------------

@router.get("/api/whatsapp/conversations")
def list_whatsapp_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    username: str = Depends(require_auth),
):
    """
    Lista de conversaciones de WhatsApp activas agrupadas por teléfono.
    Incluye último mensaje, fecha y datos del productor si existe lead.
    """
    with get_db() as conn:
        rows = conn.execute(
            """SELECT
                 ws.telefono,
                 MAX(ws.created_at) as ultima_actividad,
                 COUNT(ws.id)       as total_mensajes,
                 ws.lead_id,
                 l.cultivo, l.zona, l.nombre_productor,
                 l.punto_venta_id,
                 pdv.nombre         as pdv_nombre
               FROM whatsapp_sessions ws
               LEFT JOIN leads l ON ws.lead_id = l.id
               LEFT JOIN puntos_de_venta pdv ON l.punto_venta_id = pdv.id
               GROUP BY ws.telefono
               ORDER BY ultima_actividad DESC
               LIMIT %s OFFSET %s""",
            (limit, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(DISTINCT telefono) FROM whatsapp_sessions"
        ).fetchone()[0]

    return {
        "conversations": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/whatsapp/history/{telefono}")
def get_whatsapp_history(
    telefono: str,
    limit: int = Query(50, ge=1, le=200),
    username: str = Depends(require_auth),
):
    """Historial completo de una conversación WhatsApp por número de teléfono."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT role, message, created_at FROM whatsapp_sessions
               WHERE telefono = %s ORDER BY created_at ASC LIMIT %s""",
            (telefono, limit),
        ).fetchall()

        # Info del lead si existe
        lead_row = conn.execute(
            "SELECT * FROM leads WHERE telefono = %s ORDER BY created_at DESC LIMIT 1",
            (telefono,),
        ).fetchone()

    return {
        "telefono": telefono,
        "messages": [dict(r) for r in rows],
        "lead": dict(lead_row) if lead_row else None,
    }
