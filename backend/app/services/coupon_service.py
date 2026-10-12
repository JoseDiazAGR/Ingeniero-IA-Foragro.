"""
Lógica de generación y gestión de cupones.
"""

import random
import string
from datetime import datetime, timedelta

from app.config import DEFAULT_COUPON_DISCOUNT, DEFAULT_COUPON_EXPIRES_DAYS
from app.database import get_db


def _generate_coupon_code() -> str:
    chars = string.ascii_uppercase + string.digits
    chars = chars.translate({ord(c): None for c in "OI0"})
    return "AGRO-" + "".join(random.choices(chars, k=6))


def create_coupon_for_lead(lead_id: int, discount_percent: float, expires_days: int) -> dict:
    code = _generate_coupon_code()
    expires = datetime.utcnow() + timedelta(days=expires_days)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO coupons (code, discount_percent, lead_id, expires_at) VALUES (%s, %s, %s, %s)",
            (code, discount_percent, lead_id, expires),
        )
        conn.execute("UPDATE leads SET cupon = %s WHERE id = %s", (code, lead_id))
        conn.commit()
    return {"code": code, "discount_percent": discount_percent, "expires_at": expires.isoformat()}


def get_default_coupon_for_lead(lead_id: int) -> dict:
    return create_coupon_for_lead(lead_id, DEFAULT_COUPON_DISCOUNT, DEFAULT_COUPON_EXPIRES_DAYS)