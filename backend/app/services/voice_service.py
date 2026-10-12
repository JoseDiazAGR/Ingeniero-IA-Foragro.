"""
Servicio de voz de baja latencia y alta fidelidad para ChatAgro POP.
Genera voz ultra-natural mediante OpenAI TTS (tts-1) con caché local de audio
para latencias ultra-bajas (<50ms en frases repetidas o saludos comunes)
y transcripción de audio con Whisper.
"""

import hashlib
import os
import httpx
from fastapi import HTTPException, UploadFile

from app.config import OPENAI_API_KEY, logger

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "audio")
os.makedirs(CACHE_DIR, exist_ok=True)

# Voces recomendadas:
# 'onyx': Tono masculino, cálido, maduro y profesional (ideal para agrónomo experimentado)
# 'echo': Tono masculino amigable
DEFAULT_VOICE = "onyx"
TTS_MODEL = "tts-1"  # Optimizado para ultra-baja latencia


def get_cache_path(text: str, voice: str) -> str:
    key = f"{voice}:{text.strip()}".encode("utf-8")
    filename = hashlib.sha256(key).hexdigest() + ".mp3"
    return os.path.join(CACHE_DIR, filename)


async def synthesize_speech(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    Sintetiza audio a partir de texto. Si ya fue generado previamente,
    lo devuelve instantáneamente desde la caché local sin llamadas de red.
    """
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="El texto para síntesis no puede estar vacío.")

    cache_file = get_cache_path(cleaned, voice)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                return f.read()
        except Exception:
            pass

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API Key no configurada para TTS.")

    # Limitar longitud para prevenir abuso
    cleaned = cleaned[:1200]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": TTS_MODEL,
                    "input": cleaned,
                    "voice": voice,
                    "response_format": "mp3",
                    "speed": 1.05,  # Ligero aumento para mayor dinamismo
                },
            )

            if response.status_code != 200:
                logger.warning("OpenAI TTS devolvió status %d (%s). El kiosco usará síntesis de voz del navegador.", response.status_code, response.text[:120])
                raise HTTPException(status_code=503, detail="TTS en la nube no disponible, usar síntesis local.")

            audio_data = response.content

            # Guardar en caché
            try:
                with open(cache_file, "wb") as f:
                    f.write(audio_data)
            except Exception as e:
                logger.warning("No se pudo guardar audio en caché: %s", e)

            return audio_data

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Fallo conectando a OpenAI TTS: %s. Usando fallback de voz.", e)
        raise HTTPException(status_code=503, detail="TTS no disponible, usar síntesis local.")


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe audio enviado desde el micrófono de la tablet usando Whisper-1.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API Key no configurada para STT.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio demasiado grande (máximo 10MB).")

    filename = file.filename or "recording.webm"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": (filename, contents, file.content_type or "audio/webm")},
                data={"model": "whisper-1", "language": "es"},
            )

            if response.status_code != 200:
                logger.error("Error en Whisper STT: %s", response.text)
                raise HTTPException(status_code=502, detail="Error transcribiendo audio.")

            data = response.json()
            return data.get("text", "").strip()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fallo en transcripción de audio: %s", e)
        raise HTTPException(status_code=502, detail="Fallo transcribiendo audio.")
