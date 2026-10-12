"""
Servicio de sincronización con HubSpot CRM.
"""

import asyncio

import httpx

from app.config import HUBSPOT_API_KEY, logger


async def sync_lead_to_hubspot(telefono: str, lead_id: int):
    if not HUBSPOT_API_KEY:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers={"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"},
                json={
                    "properties": {
                        "phone": telefono,
                        "company": "FORAGRO Lead",
                        "hs_lead_status": "NEW",
                        "lifecyclestage": "lead",
                    }
                },
            )
    except Exception:
        # SECURITY: ya no es un except: pass mudo.
        logger.exception("Fallo sincronizando lead %s con HubSpot", lead_id)


def fire_and_forget_hubspot(telefono: str, lead_id: int):
    """Ejecuta la sincronización en background sin bloquear la respuesta."""
    asyncio.create_task(sync_lead_to_hubspot(telefono, lead_id))