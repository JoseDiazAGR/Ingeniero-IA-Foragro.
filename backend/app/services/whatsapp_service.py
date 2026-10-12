"""
Servicio de WhatsApp Business API (Meta Cloud API).

Responsabilidades:
  - Enviar mensajes de texto salientes (notificaciones de cupón, resúmenes).
  - Enviar alertas de escalada al agrónomo responsable de un PDV.
  - Procesar mensajes ENTRANTES del webhook de Meta y generar respuestas del agente IA.
"""

import hashlib
import json
from typing import Optional

import httpx
from fastapi import HTTPException

from app.config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, logger
from app.data.constants import RECOMENDACIONES


# ---------------------------------------------------------------------------
# Construcción de mensajes salientes
# ---------------------------------------------------------------------------

def build_whatsapp_message(lead: dict) -> str:
    """Mensaje de resumen para el productor al finalizar la consulta."""
    recomendacion = lead.get("recomendacion") or RECOMENDACIONES.get(
        lead.get("cultivo", ""), {}
    ).get(lead.get("problema", ""), "Consultar con técnico especializado.")
    cupon = lead.get("cupon", "")
    pdv_nombre = lead.get("pdv_nombre", "FORAGRO")
    return (
        f"✅ *Inge. Agro IA — {pdv_nombre}*\n\n"
        f"Hola! Tu diagnóstico para *{lead.get('cultivo', 'tu cultivo')}*:\n"
        f"{recomendacion}\n\n"
        f"🎟️ Tu cupón de descuento: *{cupon}*\n"
        f"Válido en cualquier tienda FORAGRO. ¡Que le vaya bien en el campo! 🌿"
    )


def build_whatsapp_escalada_message(
    pregunta: str,
    motivo: str,
    lead: Optional[dict],
    pdv_nombre: str,
    escalada_id: int,
) -> str:
    """Alerta enviada al agrónomo responsable del PDV cuando la IA escala."""
    productor_info = ""
    if lead:
        productor_info = (
            f"\n📋 *Productor:* {lead.get('nombre_productor') or 'Sin nombre'}"
            f"\n📞 *Teléfono:* {lead.get('telefono', '')}"
            f"\n🌾 *Cultivo:* {lead.get('cultivo', '')}"
            f"\n📍 *Zona:* {lead.get('zona', '')}"
        )

    return (
        f"⚠️ *CONSULTA ESCALADA — {pdv_nombre}*\n\n"
        f"La IA necesita tu criterio experto:\n\n"
        f"❓ *Pregunta del productor:*\n{pregunta}\n\n"
        f"🤖 *Motivo de escalada:*\n{motivo}"
        f"{productor_info}\n\n"
        f"🆔 ID Escalada: #{escalada_id}\n"
        f"Responde directamente al productor y marca como resuelta en el dashboard."
    )


# ---------------------------------------------------------------------------
# Envío de mensajes (saliente)
# ---------------------------------------------------------------------------

def _is_demo_mode() -> bool:
    return not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)


async def _send_text_message(to_number: str, body: str) -> dict:
    """Función interna de bajo nivel para enviar un mensaje de texto."""
    if _is_demo_mode():
        logger.info("WhatsApp DEMO → %s: %s", to_number, body[:80])
        return {
            "status": "demo",
            "message_id": f"demo_{hashlib.md5(body.encode()).hexdigest()[:8]}",
            "note": "Configura WHATSAPP_TOKEN y WHATSAPP_PHONE_ID para envío real.",
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {"body": body, "preview_url": False},
            },
        )
        data = response.json()
        if "messages" in data:
            return {"status": "sent", "message_id": data["messages"][0]["id"]}
        logger.warning("WhatsApp API error: %s", data)
        raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje de WhatsApp.")


async def send_whatsapp_message(lead: dict) -> dict:
    """Envía el resumen de recomendación y cupón al productor."""
    message = build_whatsapp_message(lead)
    telefono = lead.get("telefono", "")
    if not telefono:
        raise HTTPException(status_code=400, detail="El lead no tiene teléfono registrado.")
    try:
        return await _send_text_message(telefono, message)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Fallo en send_whatsapp_message")
        raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje de WhatsApp.")


async def send_escalada_alert(
    agronomo_telefono: str,
    pregunta: str,
    motivo: str,
    lead: Optional[dict],
    pdv_nombre: str,
    escalada_id: int,
) -> dict:
    """Envía alerta de escalada al agrónomo responsable del PDV."""
    message = build_whatsapp_escalada_message(
        pregunta, motivo, lead, pdv_nombre, escalada_id
    )
    try:
        return await _send_text_message(agronomo_telefono, message)
    except Exception:
        logger.exception("No se pudo enviar alerta de escalada a %s", agronomo_telefono)
        return {"status": "error", "note": "Alerta guardada en dashboard pero no enviada por WA."}


# ---------------------------------------------------------------------------
# Procesamiento de mensajes entrantes del webhook
# ---------------------------------------------------------------------------

def parse_incoming_webhook(payload: dict) -> Optional[dict]:
    """
    Extrae el primer mensaje de texto de un payload de webhook de Meta.
    Devuelve None si no hay mensajes procesables (ej: status updates).
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        msg_type = msg.get("type", "")

        # Solo procesamos texto por ahora; audio/imagen se puede extender aquí
        if msg_type != "text":
            logger.info("Webhook WA: mensaje de tipo '%s' ignorado.", msg_type)
            return None

        return {
            "from": msg["from"],                           # número del productor
            "message_id": msg["id"],
            "text": msg["text"]["body"],
            "timestamp": msg.get("timestamp", ""),
            "display_phone": value.get("metadata", {}).get("display_phone_number", ""),
        }
    except (KeyError, IndexError) as exc:
        logger.warning("No se pudo parsear webhook WA: %s", exc)
        return None