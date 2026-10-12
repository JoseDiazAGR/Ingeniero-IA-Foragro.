"""
Endpoints públicos del kiosco ChatAgro POP:
  WS   /api/chat-ws          — WebSocket manos libres (PDV-aware, escalada, offline cache)
  POST /api/chat             — Chat HTTP (fallback / API directa)
  POST /api/tts              — Síntesis de voz (OpenAI TTS con caché)
  POST /api/transcribe       — Transcripción de audio (Whisper)
  POST /api/analyze-image    — Diagnóstico visual (GPT-4o Vision)
  POST /api/lead             — Guardar lead / productor
  POST /api/send-whatsapp    — Enviar resumen por WhatsApp
  GET  /api/products         — Catálogo de inventario FORAGRO
  GET  /api/disease-references — Banco de fotos fitosanitarias
  GET  /api/weather          — Clima por zona
  GET  /api/soil             — Datos de suelo por zona
  GET  /api/offline-cache    — Paquete de datos para modo offline de la tablet
"""

import asyncio
import base64
import json
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Request, Response, UploadFile, WebSocket, WebSocketDisconnect,
)

from app.config import DEFAULT_COUPON_DISCOUNT, DEFAULT_COUPON_EXPIRES_DAYS, DEFAULT_PDV_CODE, logger
from app.data.constants import ALLOWED_CANALES, ALLOWED_CULTIVOS, ALLOWED_PROBLEMAS, ALLOWED_ZONAS, RECOMENDACIONES, SUELOS
from app.database import get_db
from app.models import ChatRequest, LeadRequest, TTSRequest, WhatsAppRequest
from app.security import normalize_hn_phone, rate_limit, require_choice
from app.services.coupon_service import get_default_coupon_for_lead
from app.services.hubspot_service import fire_and_forget_hubspot
from app.services.openai_service import analyze_image, chat_with_openai
from app.services.voice_service import synthesize_speech, transcribe_audio
from app.services.weather_service import get_weather_for_zone
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter(prefix="/api", tags=["public"])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _resolve_pdv_id(conn, codigo: Optional[str]) -> Optional[int]:
    """Convierte el código de PDV (string de URL) al ID numérico de la BD."""
    if not codigo:
        return None
    row = conn.execute(
        "SELECT id FROM puntos_de_venta WHERE codigo = %s AND activo = TRUE",
        (codigo.upper(),),
    ).fetchone()
    return row["id"] if row else None


def _save_conversation(lead_id: int, user_msg: str, assistant_msg: str, canal: str = "kiosk"):
    """Guarda un par usuario/asistente en la tabla conversations."""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO conversations (lead_id, role, message, canal) VALUES (%s, 'user', %s, %s)",
                (lead_id, user_msg[:2000], canal),
            )
            conn.execute(
                "INSERT INTO conversations (lead_id, role, message, canal) VALUES (%s, 'assistant', %s, %s)",
                (lead_id, assistant_msg[:2000], canal),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("No se pudo guardar historial de conversación: %s", exc)


# ---------------------------------------------------------------------------
# WebSocket — Modo manos libres (PDV-aware)
# ---------------------------------------------------------------------------

@router.websocket("/chat-ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket permanente entre la tablet y FastAPI.

    Protocolo de mensajes (JSON):
      → Tablet envía:
         { "type": "init", "pdv": "CODIGO_PDV" }           — Inicializar sesión
         { "type": "message", "message": "...", "cultivo": "...", "zona": "..." }  — Turno del usuario

      ← FastAPI devuelve:
         { "type": "status", "status": "pensando" }         — IA procesando
         { "type": "response", "reply": "...", "audio": "<base64>", "ui_actions": [...], "lead_id": N }
         { "type": "error", "message": "..." }
    """
    await websocket.accept()
    logger.info("📱 Kiosco conectado por WebSocket.")

    # Estado de sesión conversacional en la tablet
    session_context = []
    cultivo_actual = None
    zona_actual = None
    lead_id = None
    punto_venta_codigo = None
    punto_venta_id = None

    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            msg_type = data.get("type", "message")

            # ── Inicialización de sesión PDV ──────────────────────────────
            if msg_type == "init":
                punto_venta_codigo = data.get("pdv", DEFAULT_PDV_CODE).upper()
                with get_db() as conn:
                    punto_venta_id = _resolve_pdv_id(conn, punto_venta_codigo)
                logger.info("🏪 PDV conectado: %s (id=%s)", punto_venta_codigo, punto_venta_id)
                await websocket.send_json({
                    "type": "ready",
                    "pdv": punto_venta_codigo,
                    "pdv_id": punto_venta_id,
                })
                continue

            # ── Heartbeat Ping/Pong ───────────────────────────────────────
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # ── Turno conversacional ──────────────────────────────────────
            user_message = data.get("message", "").strip()
            cultivo_actual = data.get("cultivo", cultivo_actual)
            zona_actual = data.get("zona", zona_actual)

            if not user_message:
                continue

            logger.info("🌾 [%s] Productor: %s", punto_venta_codigo or "%s", user_message[:80])

            session_context.append({"role": "user", "content": user_message})
            await websocket.send_json({"type": "status", "status": "pensando"})

            # ── Llamada a la IA ───────────────────────────────────────────
            ai_response = await chat_with_openai(
                message=user_message,
                context=session_context,
                cultivo=cultivo_actual,
                zona=zona_actual,
                lead_id=lead_id,
                punto_venta_id=punto_venta_id,
                punto_venta_codigo=punto_venta_codigo,
            )

            reply_text = ai_response.get("reply", "")
            ui_actions = ai_response.get("ui_actions", [])

            # Capturar lead_id si fue creado en este turno
            new_lead_id = ai_response.get("lead_id")
            if new_lead_id and new_lead_id != lead_id:
                lead_id = new_lead_id
                logger.info("💾 Lead vinculado a sesión WS: ID=%d, PDV=%s", lead_id, punto_venta_codigo)

            # Guardar historial en CRM
            if lead_id:
                _save_conversation(lead_id, user_message, reply_text, canal="kiosk")

            session_context.append({"role": "assistant", "content": reply_text})

            # ── TTS (síntesis de voz con fallback transparente) ───────────
            audio_b64 = None
            try:
                audio_bytes = await synthesize_speech(reply_text, voice="onyx")
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as tts_err:
                logger.info("TTS en la nube no disponible (%s). El kiosco usará síntesis del navegador.", tts_err)
                audio_b64 = None

            # ── Respuesta completa a la tablet ────────────────────────────
            await websocket.send_json({
                "type": "response",
                "reply": reply_text,
                "audio": audio_b64,
                "ui_actions": ui_actions,
                "lead_id": lead_id,
                "model": ai_response.get("model", ""),
            })

    except WebSocketDisconnect:
        logger.info("🔌 Kiosco desconectado. PDV=%s", punto_venta_codigo or "%s")
    except Exception as exc:
        logger.exception("Error crítico en WebSocket: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": "Error interno del servidor."})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Chat HTTP (fallback / integración directa)
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(req: ChatRequest, _rl=Depends(rate_limit(30, 60))):
    """Chat HTTP con Function Calling. El PDV se pasa como campo del request."""
    punto_venta_id = None
    if req.punto_venta_id:
        with get_db() as conn:
            punto_venta_id = _resolve_pdv_id(conn, req.punto_venta_id)

    result = await chat_with_openai(
        message=req.message,
        context=req.context,
        cultivo=req.cultivo,
        zona=req.zona,
        lead_id=req.lead_id,
        punto_venta_id=punto_venta_id,
        punto_venta_codigo=req.punto_venta_id,
    )

    if req.lead_id:
        _save_conversation(req.lead_id, req.message, result.get("reply", ""))

    return result


# ---------------------------------------------------------------------------
# Voz
# ---------------------------------------------------------------------------

@router.post("/tts")
async def text_to_speech(req: TTSRequest, _rl=Depends(rate_limit(60, 60))):
    """Genera audio MP3 con caché de baja latencia usando OpenAI TTS."""
    audio_bytes = await synthesize_speech(req.text, req.voice or "onyx")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), _rl=Depends(rate_limit(20, 60))):
    """Transcribe audio de micrófono usando Whisper."""
    text = await transcribe_audio(file)
    return {"text": text}


# ---------------------------------------------------------------------------
# Visión
# ---------------------------------------------------------------------------

@router.post("/analyze-image")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    cultivo: str = Form(""),
    _rl=Depends(rate_limit(10, 60)),
):
    """Diagnóstico fitosanitario por foto usando GPT-4o Vision."""
    return await analyze_image(file, cultivo)


# ---------------------------------------------------------------------------
# Catálogo e inventario
# ---------------------------------------------------------------------------

@router.get("/products")
def get_products(
    cultivo: Optional[str] = None,
    categoria: Optional[str] = None,
    _rl=Depends(rate_limit(60, 60)),
):
    """Devuelve productos FORAGRO con stock disponible y precios en HNL."""
    with get_db() as conn:
        query = (
            "SELECT id, sku, nombre, categoria, ingrediente_activo, cultivos, problemas, "
            "dosis, precio_hnl, stock, unidad, imagen_url, descripcion FROM products WHERE 1=1"
        )
        params = []
        if cultivo:
            query += " AND (cultivos LIKE %s OR cultivos LIKE '%%Todos%%')"
            params.append(f"%{cultivo}%")
        if categoria:
            query += " AND categoria LIKE %s"
            params.append(f"%{categoria}%")
        query += " ORDER BY categoria, stock DESC"
        rows = conn.execute(query, params).fetchall()
    return {"products": [dict(r) for r in rows]}


@router.get("/disease-references")
def get_disease_references(
    cultivo: Optional[str] = None,
    _rl=Depends(rate_limit(60, 60)),
):
    """Galería de fotografías de enfermedades de referencia."""
    with get_db() as conn:
        if cultivo:
            rows = conn.execute(
                "SELECT * FROM disease_references WHERE cultivo LIKE %s ORDER BY id ASC",
                (f"%{cultivo}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM disease_references ORDER BY cultivo, id ASC"
            ).fetchall()
    return {"references": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Lead (registro de productor)
# ---------------------------------------------------------------------------

@router.post("/lead")
async def save_lead(req: LeadRequest, _rl=Depends(rate_limit(10, 60))):
    """
    Guarda un lead con datos agronómicos completos,
    genera el cupón y lo registra en el CRM.
    """
    cultivo = require_choice(req.cultivo, ALLOWED_CULTIVOS, "cultivo")
    zona = require_choice(req.zona, ALLOWED_ZONAS, "zona")
    problema = (req.problema or "").strip()[:100] or None
    canal = require_choice(req.canal, ALLOWED_CANALES, "canal") if req.canal else "Punto de venta"
    telefono = normalize_hn_phone(req.telefono)
    manzanas = (req.manzanas or "")[:20]
    fecha_siembra = (req.fecha_siembra or "")[:50]
    historial = (req.historial or "")[:200]
    productos_sugeridos = (req.productos_sugeridos or "")[:500]
    nombre_productor = (req.nombre_productor or "")[:100]

    punto_venta_id = None
    if req.punto_venta_id:
        with get_db() as conn:
            punto_venta_id = _resolve_pdv_id(conn, req.punto_venta_id)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO leads (
                cultivo, zona, manzanas, fecha_siembra, problema, historial,
                canal, telefono, recomendacion, productos_sugeridos,
                estado_seguimiento, nombre_productor, punto_venta_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Nuevo', %s, %s)""",
            (
                cultivo, zona, manzanas, fecha_siembra, problema, historial,
                canal, telefono,
                RECOMENDACIONES.get(cultivo, {}).get(problema, "Diagnóstico personalizado por IA"),
                productos_sugeridos, nombre_productor, punto_venta_id,
            ),
        )
        lead_id = cursor.lastrowid
        conn.commit()

    coupon = get_default_coupon_for_lead(lead_id)
    fire_and_forget_hubspot(telefono, lead_id)

    return {
        "status": "saved",
        "lead_id": lead_id,
        "cupon": coupon["code"],
        "expires_at": coupon["expires_at"],
        "descuento": coupon["discount_percent"],
    }


# ---------------------------------------------------------------------------
# WhatsApp saliente
# ---------------------------------------------------------------------------

@router.post("/send-whatsapp")
async def send_whatsapp(req: WhatsAppRequest, _rl=Depends(rate_limit(10, 60))):
    """Envía el resumen de recomendación y cupón al WhatsApp del productor."""
    with get_db() as conn:
        lead = conn.execute("SELECT * FROM leads WHERE id = %s", (req.lead_id,)).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado.")
    return await send_whatsapp_message(dict(lead))


# ---------------------------------------------------------------------------
# Datos agronómicos
# ---------------------------------------------------------------------------

@router.get("/weather")
async def get_weather(zona: str, _rl=Depends(rate_limit(30, 60))):
    zona = require_choice(zona, ALLOWED_ZONAS, "zona")
    return await get_weather_for_zone(zona)


@router.get("/soil")
def get_soil(zona: str, _rl=Depends(rate_limit(30, 60))):
    zona = require_choice(zona, ALLOWED_ZONAS, "zona")
    return {"zona": zona, **SUELOS.get(zona, SUELOS["Otro"])}


# ---------------------------------------------------------------------------
# Caché offline para tablet
# ---------------------------------------------------------------------------

@router.get("/offline-cache")
def get_offline_cache(_rl=Depends(rate_limit(5, 60))):
    """
    Devuelve un paquete compacto con el conocimiento base necesario para
    que la tablet opere en modo offline (sin internet).
    Incluye: catálogo de productos, referencias fitosanitarias, suelos y FAQS.
    """
    with get_db() as conn:
        products = [
            dict(r)
            for r in conn.execute(
                "SELECT sku, nombre, categoria, cultivos, problemas, dosis, precio_hnl, stock, unidad "
                "FROM products WHERE stock > 0 ORDER BY categoria, nombre"
            ).fetchall()
        ]
        disease_refs = [
            dict(r)
            for r in conn.execute(
                "SELECT cultivo, problema, nombre_enfermedad, descripcion_sintomas, foto_url "
                "FROM disease_references ORDER BY cultivo"
            ).fetchall()
        ]

    return {
        "version": "2.0",
        "products": products,
        "disease_references": disease_refs,
        "suelos": SUELOS,
        "recomendaciones": RECOMENDACIONES,
        "cultivos": ALLOWED_CULTIVOS,
        "zonas": ALLOWED_ZONAS,
    }