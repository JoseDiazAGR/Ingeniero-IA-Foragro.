"""
Servicio de clima: OpenWeather con datos de respaldo (fallback).
"""

import httpx

from app.config import OPENWEATHER_API_KEY, logger
from app.data.constants import COORDENADAS, FALLBACKS_CLIMA


async def get_weather_for_zone(zona: str) -> dict:
    lat, lon = COORDENADAS.get(zona, (14.07, -87.20))

    if not OPENWEATHER_API_KEY:
        return {"zona": zona, **FALLBACKS_CLIMA.get(zona, FALLBACKS_CLIMA["Otro"]), "source": "fallback"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "es"},
            )
            data = response.json()
            return {
                "zona": zona,
                "temperatura": data["main"]["temp"],
                "humedad": data["main"]["humidity"],
                "descripcion": data["weather"][0]["description"],
                "viento": data["wind"]["speed"],
                "source": "openweather",
            }
    except Exception:
        logger.exception("Fallo llamando a OpenWeather")
        return {"zona": zona, **FALLBACKS_CLIMA.get(zona, FALLBACKS_CLIMA["Otro"]), "source": "fallback"}