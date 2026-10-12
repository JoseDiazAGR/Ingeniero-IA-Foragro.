"""
Servicio de inteligencia artificial con Function Calling (Tools) y Visión.

Arquitectura:
  - AGRO_TOOLS: esquema de herramientas para OpenAI (declarativo, fácil de extender)
  - _tool_*: ejecutores locales de cada herramienta (1 función por herramienta)
  - chat_with_openai: orquestador del ciclo conversacional con soporte de PDV
  - analyze_image: análisis de fotos por visión (GPT-4o)
"""

import base64
import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, UploadFile

from app.config import MAX_IMAGE_BYTES, OPENAI_API_KEY, logger
from app.data.constants import FALLBACKS_CLIMA, RECOMENDACIONES, SUELOS, SYSTEM_PROMPT
from app.database import get_db
from app.services.coupon_service import get_default_coupon_for_lead
from app.services.whatsapp_service import send_whatsapp_message, send_escalada_alert


# ---------------------------------------------------------------------------
# Esquema de herramientas para OpenAI (Tool Calling)
# Para agregar una nueva tool: añade un dict aquí y su ejecutor _tool_*() abajo.
# ---------------------------------------------------------------------------

AGRO_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "consultar_inventario",
            "description": (
                "Consulta el catálogo e inventario oficial de FORAGRO en bodega para un cultivo, "
                "problema o categoría. Devuelve existencias reales, precios en HNL, dosis e "
                "ingredientes activos. Usar siempre antes de recomendar un producto para evitar "
                "alucinaciones y citar precios incorrectos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cultivo": {
                        "type": "string",
                        "description": "Cultivo objetivo (ej: Café, Maíz, Frijol, Plátano, Tomate)",
                    },
                    "problema": {
                        "type": "string",
                        "description": "Problema o plaga (ej: Roya, Cogollero, Broca, Antracnosis)",
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Categoría: Fungicida, Insecticida, Fertilizante Foliar, Bioestimulante",
                    },
                },
                "required": ["cultivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mostrar_fotos_referencia",
            "description": (
                "Despliega en la pantalla de la tablet fotografías de referencia de enfermedades "
                "o plagas para que el productor compare visualmente y confirme el diagnóstico."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cultivo": {"type": "string", "description": "Nombre del cultivo"},
                    "problema": {"type": "string", "description": "Tipo de problema o sospecha"},
                },
                "required": ["cultivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solicitar_foto_camara",
            "description": (
                "Activa la cámara de la tablet para que el agricultor tome una foto de la hoja "
                "o planta enferma para análisis por visión IA."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "motivo": {
                        "type": "string",
                        "description": "Por qué se necesita la foto",
                    }
                },
                "required": ["motivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_datos_agronomicos",
            "description": (
                "Obtiene características agronómicas del suelo y condiciones climáticas "
                "del departamento o zona de Honduras indicado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "zona": {
                        "type": "string",
                        "description": "Zona o departamento de Honduras",
                    }
                },
                "required": ["zona"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_datos_productor",
            "description": (
                "Registra en el CRM todos los datos capturados del productor y genera su cupón "
                "del 5% de descuento. Llamar cuando se tenga cultivo, zona y teléfono confirmados."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cultivo":               {"type": "string"},
                    "zona":                  {"type": "string"},
                    "manzanas":              {"type": "string"},
                    "fecha_siembra":         {"type": "string"},
                    "problema":              {"type": "string"},
                    "historial":             {"type": "string"},
                    "telefono":              {"type": "string"},
                    "canal":                 {"type": "string"},
                    "productos_recomendados":{"type": "string"},
                    "nombre_productor":      {"type": "string", "description": "Nombre del productor si lo dio"},
                },
                "required": ["cultivo", "zona", "telefono"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_resumen_whatsapp",
            "description": "Envía al WhatsApp del productor la recomendación técnica y su cupón.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID del lead registrado"}
                },
                "required": ["lead_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalar_a_agronomo",
            "description": (
                "Usa esta herramienta cuando la pregunta del productor requiere criterio experto "
                "que va más allá de los datos disponibles, o cuando el diagnóstico es ambiguo y "
                "una recomendación incorrecta podría dañar el cultivo. El agrónomo responsable "
                "del punto de venta recibirá una alerta por WhatsApp para responder directamente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pregunta": {
                        "type": "string",
                        "description": "Pregunta o situación específica del productor",
                    },
                    "motivo": {
                        "type": "string",
                        "description": "Por qué la IA no puede responder con certeza",
                    },
                },
                "required": ["pregunta", "motivo"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Ejecutores locales de herramientas (_tool_*)
# Cada función es independiente y testeable de forma aislada.
# ---------------------------------------------------------------------------

def _tool_consultar_inventario(
    cultivo: str, problema: str = "", categoria: str = ""
) -> dict:
    with get_db() as conn:
        query = (
            "SELECT id, sku, nombre, categoria, ingrediente_activo, dosis, "
            "precio_hnl, stock, unidad, descripcion FROM products WHERE 1=1"
        )
        params = []
        if cultivo:
            query += " AND (cultivos LIKE %s OR cultivos LIKE '%%Todos%%')"
            params.append(f"%{cultivo}%")
        if problema:
            query += " AND problemas LIKE %s"
            params.append(f"%{problema}%")
        if categoria:
            query += " AND categoria LIKE %s"
            params.append(f"%{categoria}%")
        query += " ORDER BY stock DESC LIMIT 6"
        rows = conn.execute(query, params).fetchall()

        # Fallback: solo por cultivo si no hubo resultados
        if not rows and cultivo:
            rows = conn.execute(
                "SELECT id, sku, nombre, categoria, ingrediente_activo, dosis, "
                "precio_hnl, stock, unidad, descripcion FROM products "
                "WHERE cultivos LIKE %s LIMIT 4",
                (f"%{cultivo}%",),
            ).fetchall()

    return {"encontrados": len(rows), "productos": [dict(r) for r in rows]}


def _tool_mostrar_fotos_referencia(cultivo: str, problema: str = "") -> dict:
    with get_db() as conn:
        query = (
            "SELECT id, cultivo, problema, nombre_enfermedad, nombre_cientifico, "
            "descripcion_sintomas, foto_url, productos_recomendados_ids "
            "FROM disease_references WHERE cultivo LIKE %s"
        )
        params = [f"%{cultivo}%"]
        if problema:
            query += " AND (problema LIKE %s OR nombre_enfermedad LIKE %s OR descripcion_sintomas LIKE %s)"
            params.extend([f"%{problema}%", f"%{problema}%", f"%{problema}%"])
        rows = conn.execute(query, params).fetchall()

        if not rows:
            rows = conn.execute(
                "SELECT id, cultivo, problema, nombre_enfermedad, nombre_cientifico, "
                "descripcion_sintomas, foto_url, productos_recomendados_ids "
                "FROM disease_references WHERE cultivo LIKE %s",
                (f"%{cultivo}%",),
            ).fetchall()

    return {"total_fotos": len(rows), "referencias": [dict(r) for r in rows]}


def _tool_obtener_datos_agronomicos(zona: str) -> dict:
    return {
        "zona": zona,
        "suelo": SUELOS.get(zona, SUELOS.get("Otro", {})),
        "clima": FALLBACKS_CLIMA.get(zona, FALLBACKS_CLIMA.get("Otro", {})),
    }


def _tool_guardar_datos_productor(
    cultivo: str,
    zona: str,
    telefono: str,
    manzanas: str = "",
    fecha_siembra: str = "",
    problema: str = "",
    historial: str = "",
    canal: str = "Punto de venta",
    productos_recomendados: str = "",
    nombre_productor: str = "",
    punto_venta_id: Optional[int] = None,
) -> dict:
    from app.security import normalize_hn_phone

    try:
        norm_phone = normalize_hn_phone(telefono)
    except Exception:
        norm_phone = telefono

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO leads (
                cultivo, zona, manzanas, fecha_siembra, problema, historial,
                canal, telefono, recomendacion, productos_sugeridos,
                estado_seguimiento, nombre_productor, punto_venta_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Nuevo', %s, %s)""",
            (
                cultivo, zona, manzanas, fecha_siembra, problema, historial,
                canal or "Punto de venta", norm_phone,
                RECOMENDACIONES.get(cultivo, {}).get(problema, "Diagnóstico personalizado por IA"),
                productos_recomendados,
                nombre_productor,
                punto_venta_id,
            ),
        )
        lead_id = cursor.lastrowid
        conn.commit()

    coupon = get_default_coupon_for_lead(lead_id)
    return {
        "status": "success",
        "lead_id": lead_id,
        "cupon": coupon["code"],
        "descuento": coupon["discount_percent"],
        "telefono": norm_phone,
    }


async def _tool_enviar_resumen_whatsapp(lead_id: int) -> dict:
    with get_db() as conn:
        lead = conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()
    if not lead:
        return {"status": "error", "message": "Lead no encontrado"}
    result = await send_whatsapp_message(dict(lead))
    return {"status": "success", "whatsapp_result": result}


async def _tool_escalar_a_agronomo(
    pregunta: str,
    motivo: str,
    lead_id: Optional[int],
    punto_venta_id: Optional[int],
) -> dict:
    """
    Registra la escalada en la BD y envía alerta WhatsApp al agrónomo responsable del PDV.
    """
    agronomo_telefono = None
    agronomo_nombre = "Agrónomo FORAGRO"
    pdv_nombre = "FORAGRO"
    lead = None

    with get_db() as conn:
        # Obtener info del PDV y su agrónomo responsable
        if punto_venta_id:
            pdv_row = conn.execute(
                "SELECT nombre FROM puntos_de_venta WHERE id = %s", (punto_venta_id,)
            ).fetchone()
            if pdv_row:
                pdv_nombre = pdv_row["nombre"]

            agro_row = conn.execute(
                """SELECT u.telefono_wa, u.nombre
                   FROM pdv_agronomos pa
                   JOIN users u ON pa.user_id = u.id
                   WHERE pa.pdv_id = %s AND pa.es_responsable = TRUE
                   LIMIT 1""",
                (punto_venta_id,),
            ).fetchone()
            if agro_row:
                agronomo_telefono = agro_row["telefono_wa"]
                agronomo_nombre = agro_row["nombre"] or "Agrónomo"

        if lead_id:
            lead_row = conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()
            if lead_row:
                lead = dict(lead_row)

        # Registrar escalada en BD
        cursor = conn.execute(
            """INSERT INTO agronomo_escaladas (lead_id, pdv_id, pregunta, motivo, estado)
               VALUES (%s, %s, %s, %s, 'pendiente')""",
            (lead_id, punto_venta_id, pregunta[:1000], motivo[:500]),
        )
        escalada_id = cursor.lastrowid
        conn.commit()

    # Enviar alerta WhatsApp si el agrónomo tiene número configurado
    wa_result = {"status": "no_phone", "note": "Agrónomo sin WhatsApp configurado."}
    if agronomo_telefono:
        wa_result = await send_escalada_alert(
            agronomo_telefono, pregunta, motivo, lead, pdv_nombre, escalada_id
        )

    return {
        "status": "escalada_registrada",
        "escalada_id": escalada_id,
        "agronomo": agronomo_nombre,
        "whatsapp_alert": wa_result,
    }


# ---------------------------------------------------------------------------
# Utilidad: normalización de strings para comparación sin tildes
# ---------------------------------------------------------------------------
import unicodedata as _unicodedata


def _normalize_str(s: str) -> str:
    """Quita tildes y pone en minúsculas: 'Café' == 'cafe' == 'CAFE'."""
    return _unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()


# ---------------------------------------------------------------------------
# Fallback local con conocimiento base (sin internet / sin API key)
# ---------------------------------------------------------------------------

def _generate_local_agronomic_fallback(
    msg: str, user_cultivo: Optional[str], user_zona: Optional[str]
) -> dict:
    """
    Motor agronómico local que funciona sin conexión a OpenAI.
    Usa el inventario SQLite real. Tolera tildes/acentos en el mensaje.
    """
    detected_cultivo = user_cultivo
    detected_prob = None
    norm_msg = _normalize_str(msg + " " + (user_cultivo or ""))

    # Detectar cultivo (sin importar tildes)
    for c in ["Café", "Maíz", "Frijol", "Plátano", "Tomate", "Caña", "Palma"]:
        if _normalize_str(c) in norm_msg:
            detected_cultivo = c
            break
    detected_cultivo = detected_cultivo or "Café"

    # Detectar problema/plaga (keywords ya en minúsculas sin tildes)
    keywords_prob = {
        "roya": "Roya", "broca": "Broca", "cogollero": "Cogollero",
        "antracnosis": "Antracnosis", "sigatoka": "Sigatoka",
        "tizon": "Tizón", "ojo de gallo": "Ojo de Gallo",
        "plaga": "Plagas", "enfermedad": "Enfermedad",
        "amarillo": "Deficiencia nutricional", "marchit": "Marchitez",
    }
    for kw, p_val in keywords_prob.items():
        if kw in norm_msg:
            detected_prob = p_val
            break

    inv = _tool_consultar_inventario(detected_cultivo, detected_prob or "")
    ref = _tool_mostrar_fotos_referencia(detected_cultivo, detected_prob or "")

    actions = []
    if ref.get("referencias"):
        actions.append({"type": "show_disease_photos", "data": ref["referencias"]})
    if inv.get("productos"):
        actions.append({"type": "show_products", "data": inv["productos"]})

    rec_base = RECOMENDACIONES.get(detected_cultivo, {}).get(detected_prob or "", "")
    if not rec_base:
        rec_base = RECOMENDACIONES.get(detected_cultivo, {}).get(
            "Enfermedad", "revisión fitosanitaria técnica en finca"
        )

    prod_names = [p["nombre"] for p in inv.get("productos", [])[:2]]
    prod_str = f" con {', '.join(prod_names)}" if prod_names else ""

    reply = (
        f"Para tu cultivo de {detected_cultivo}, el tratamiento recomendado es {rec_base}. "
        f"En bodega tenemos disponibilidad inmediata{prod_str}. "
        f"Compara los síntomas con las fotos en pantalla y facilítame tu WhatsApp "
        f"para enviarte tu cupón del 5% de descuento."
    )

    return {"reply": reply, "ui_actions": actions, "model": "local_offline_engine"}


# ---------------------------------------------------------------------------
# Orquestador principal: chat_with_openai
# ---------------------------------------------------------------------------

async def chat_with_openai(
    message: str,
    context: list,
    cultivo: Optional[str] = None,
    zona: Optional[str] = None,
    lead_id: Optional[int] = None,
    punto_venta_id: Optional[int] = None,   # ID numérico del PDV en BD
    punto_venta_codigo: Optional[str] = None,  # código legible del PDV
) -> dict:
    """
    Gestiona el ciclo conversacional con soporte completo de Function Calling.
    Devuelve: reply (texto), ui_actions (acciones para la tablet) y metadata.
    """
    ui_actions = []

    if not OPENAI_API_KEY:
        return _generate_local_agronomic_fallback(message, cultivo, zona)

    safe_context = [
        {"role": m.get("role"), "content": str(m.get("content", ""))[:2000]}
        for m in (context or [])[-12:]
        if m.get("role") in ("user", "assistant")
    ]

    system_content = SYSTEM_PROMPT
    if cultivo:
        system_content += f"\nContexto actual del cliente: Cultivo = {cultivo}"
    if zona:
        system_content += f", Zona = {zona}"
    if lead_id:
        system_content += f", Lead ID = {lead_id}"
    if punto_venta_codigo:
        system_content += f", Punto de Venta = {punto_venta_codigo}"

    messages = [
        {"role": "system", "content": system_content},
        *safe_context,
        {"role": "user", "content": message[:2000]},
    ]

    active_model = "gpt-4o-mini"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            first_resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": active_model,
                    "messages": messages,
                    "tools": AGRO_TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.6,
                    "max_tokens": 400,
                },
            )

            if first_resp.status_code != 200:
                logger.warning(
                    "OpenAI devolvió status %d. Activando motor agronómico local.",
                    first_resp.status_code,
                )
                return _generate_local_agronomic_fallback(message, cultivo, zona)

            data = first_resp.json()
            choice = data["choices"][0]
            resp_msg = choice["message"]

            if resp_msg.get("tool_calls"):
                messages.append(resp_msg)

                for tool_call in resp_msg["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"].get("arguments") or "{}")
                    except Exception:
                        args = {}

                    tool_output = await _dispatch_tool(
                        fn_name=fn_name,
                        args=args,
                        cultivo=cultivo,
                        zona=zona,
                        lead_id=lead_id,
                        punto_venta_id=punto_venta_id,
                        ui_actions=ui_actions,
                    )

                    # Capturar lead_id si fue creado por guardar_datos_productor
                    if fn_name == "guardar_datos_productor" and tool_output.get("lead_id"):
                        lead_id = tool_output["lead_id"]

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": json.dumps(tool_output, ensure_ascii=False),
                    })

                # Segunda llamada para sintetizar respuesta final
                second_resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": active_model,
                        "messages": messages,
                        "temperature": 0.6,
                        "max_tokens": 300,
                    },
                )
                if second_resp.status_code == 200:
                    reply = second_resp.json()["choices"][0]["message"]["content"]
                else:
                    reply = resp_msg.get("content") or "He revisado la información técnica de bodega para tu cultivo."
            else:
                reply = resp_msg.get("content", "")

            return {
                "reply": reply,
                "ui_actions": ui_actions,
                "model": active_model,
                "lead_id": lead_id,
            }

    except Exception as exc:
        logger.warning("Excepción en OpenAI (%s). Activando motor agronómico local.", exc)
        return _generate_local_agronomic_fallback(message, cultivo, zona)


async def _dispatch_tool(
    fn_name: str,
    args: dict,
    cultivo: Optional[str],
    zona: Optional[str],
    lead_id: Optional[int],
    punto_venta_id: Optional[int],
    ui_actions: list,
) -> dict:
    """
    Despacha la llamada a la herramienta correcta y actualiza ui_actions.
    Separado del orquestador para mantener claridad y facilitar extensión.
    """
    if fn_name == "consultar_inventario":
        result = _tool_consultar_inventario(
            args.get("cultivo", cultivo or ""),
            args.get("problema", ""),
            args.get("categoria", ""),
        )
        if result.get("productos"):
            ui_actions.append({"type": "show_products", "data": result["productos"]})
        return result

    elif fn_name == "mostrar_fotos_referencia":
        result = _tool_mostrar_fotos_referencia(
            args.get("cultivo", cultivo or ""),
            args.get("problema", ""),
        )
        if result.get("referencias"):
            ui_actions.append({"type": "show_disease_photos", "data": result["referencias"]})
        return result

    elif fn_name == "solicitar_foto_camara":
        motivo = args.get("motivo", "Fotografía para diagnóstico fitosanitario")
        ui_actions.append({"type": "request_camera", "motivo": motivo})
        return {"status": "camera_prompt_displayed", "motivo": motivo}

    elif fn_name == "obtener_datos_agronomicos":
        result = _tool_obtener_datos_agronomicos(args.get("zona", zona or "Copán"))
        ui_actions.append({"type": "show_soil_weather", "data": result})
        return result

    elif fn_name == "guardar_datos_productor":
        result = _tool_guardar_datos_productor(
            cultivo=args.get("cultivo", cultivo or "Otro"),
            zona=args.get("zona", zona or "Otro"),
            telefono=args.get("telefono", ""),
            manzanas=args.get("manzanas", ""),
            fecha_siembra=args.get("fecha_siembra", ""),
            problema=args.get("problema", ""),
            historial=args.get("historial", ""),
            canal=args.get("canal", "Punto de venta"),
            productos_recomendados=args.get("productos_recomendados", ""),
            nombre_productor=args.get("nombre_productor", ""),
            punto_venta_id=punto_venta_id,
        )
        ui_actions.append({"type": "show_coupon", "data": result})
        return result

    elif fn_name == "enviar_resumen_whatsapp":
        lid = args.get("lead_id") or lead_id
        if lid:
            result = await _tool_enviar_resumen_whatsapp(int(lid))
            ui_actions.append({"type": "whatsapp_sent", "data": result})
            return result
        return {"status": "missing_lead_id"}

    elif fn_name == "escalar_a_agronomo":
        result = await _tool_escalar_a_agronomo(
            pregunta=args.get("pregunta", ""),
            motivo=args.get("motivo", ""),
            lead_id=lead_id,
            punto_venta_id=punto_venta_id,
        )
        ui_actions.append({"type": "escalada_registrada", "data": result})
        return result

    else:
        logger.warning("Tool desconocida: %s", fn_name)
        return {"status": "unknown_tool"}


# ---------------------------------------------------------------------------
# Análisis de imágenes por visión (GPT-4o)
# ---------------------------------------------------------------------------

async def analyze_image(file: UploadFile, cultivo: str = "") -> dict:
    """
    Analiza una imagen tomada con la cámara de la tablet.
    Identifica patógenos, daños o deficiencias y consulta el inventario.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503, detail="El análisis de imágenes no está disponible sin API Key."
        )
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida.")

    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen es demasiado grande (máximo 8 MB).")

    b64 = base64.b64encode(contents).decode()
    prompt_text = (
        f"Eres un fitopatólogo experto de FORAGRO en Honduras. "
        f"Analiza esta fotografía de {cultivo or 'cultivo agrícola'}. "
        f"1. Identifica la enfermedad, plaga o deficiencia (nombre común y científico). "
        f"2. Describe los síntomas visibles. "
        f"3. Indica el tipo de producto que se requiere (fungicida, insecticida, bioestimulante). "
        f"Respuesta en máximo 3 oraciones claras, para ser leída por voz en un kiosco POP."
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un ingeniero agrónomo y patólogo vegetal experto de FORAGRO Honduras.",
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            ],
                        },
                    ],
                    "max_tokens": 400,
                },
            )
            diagnosis = response.json()["choices"][0]["message"]["content"]

        # Buscar productos en inventario según diagnóstico
        matched_products = []
        with get_db() as conn:
            keywords = ["Roya", "Broca", "Antracnosis", "Cogollero", "Sigatoka", "Tizón", "Fungicida", "Insecticida"]
            detected = [k for k in keywords if k.lower() in diagnosis.lower()]
            if detected:
                rows = conn.execute(
                    "SELECT id, sku, nombre, categoria, ingrediente_activo, dosis, "
                    "precio_hnl, stock, unidad FROM products "
                    "WHERE problemas LIKE ? OR categoria LIKE ? LIMIT 3",
                    (f"%{detected[0]}%", f"%{detected[0]}%"),
                ).fetchall()
                matched_products = [dict(r) for r in rows]

        return {
            "diagnosis": diagnosis,
            "cultivo": cultivo,
            "confidence": "alta",
            "recommended_products": matched_products,
        }

    except Exception:
        logger.exception("Fallo en analyze_image")
        return {
            "diagnosis": (
                "Observo afectación foliar en la muestra. "
                "Te recomiendo aplicar un tratamiento preventivo y consultar con el agrónomo de tienda."
            ),
            "cultivo": cultivo,
            "confidence": "media",
            "recommended_products": [],
        }


# ---------------------------------------------------------------------------
# Re-exportar synthesize_speech para compatibilidad con imports existentes
# ---------------------------------------------------------------------------
from app.services.voice_service import synthesize_speech   # noqa: F401, E402