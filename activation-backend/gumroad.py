from __future__ import annotations

from dataclasses import dataclass

import httpx

from config import Settings


@dataclass(frozen=True)
class GumroadVerification:
    valid: bool
    status: str
    message: str
    sale_id: str | None = None
    purchaser_email: str | None = None
    purchaser_name: str | None = None
    product_permalink: str | None = None
    refunded: bool = False
    disputed: bool = False


async def verify_license(
    settings: Settings,
    *,
    license_key: str,
    product_permalink: str,
) -> GumroadVerification:
    form_payload = {
        "product_permalink": product_permalink,
        "license_key": license_key.strip(),
        "increment_uses_count": "false",
    }
    if settings.gumroad_access_token:
        form_payload["access_token"] = settings.gumroad_access_token

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(settings.gumroad_verify_url, data=form_payload)
        except httpx.HTTPError as exc:
            return GumroadVerification(
                valid=False,
                status="gumroad_network_error",
                message=f"Gumroad verification request failed: {exc.__class__.__name__}.",
            )

    try:
        data = response.json()
    except ValueError:
        return GumroadVerification(
            valid=False,
            status="gumroad_http_error",
            message=f"Gumroad verification failed with HTTP {response.status_code} and a non-JSON response.",
        )

    if not isinstance(data, dict):
        return GumroadVerification(
            valid=False,
            status="gumroad_http_error",
            message=f"Gumroad verification failed with HTTP {response.status_code} and an unexpected response payload.",
        )

    purchase = data.get("purchase") or data.get("sale") or {}
    valid = bool(data.get("success"))
    product = purchase.get("product_permalink") or product_permalink
    sale_id = purchase.get("sale_id") or purchase.get("id")
    refunded = bool(purchase.get("refunded") or purchase.get("is_refunded"))
    disputed = bool(
        purchase.get("disputed")
        or purchase.get("chargebacked")
        or purchase.get("is_chargebacked")
    )

    if not valid:
        return GumroadVerification(
            valid=False,
            status="license_denied",
            message=data.get("message") or "Gumroad rejected the license key.",
            sale_id=sale_id,
            purchaser_email=purchase.get("email"),
            purchaser_name=purchase.get("full_name"),
            product_permalink=product,
            refunded=refunded,
            disputed=disputed,
        )

    if response.status_code >= 400:
        return GumroadVerification(
            valid=False,
            status="gumroad_http_error",
            message=f"Gumroad verification failed with HTTP {response.status_code}.",
            sale_id=sale_id,
            purchaser_email=purchase.get("email"),
            purchaser_name=purchase.get("full_name"),
            product_permalink=product,
            refunded=refunded,
            disputed=disputed,
        )

    if refunded or disputed:
        return GumroadVerification(
            valid=False,
            status="license_revoked",
            message="This Gumroad license is refunded, disputed, or otherwise not valid for activation.",
            sale_id=sale_id,
            purchaser_email=purchase.get("email"),
            purchaser_name=purchase.get("full_name"),
            product_permalink=product,
            refunded=refunded,
            disputed=disputed,
        )

    return GumroadVerification(
        valid=True,
        status="active",
        message="License verified successfully.",
        sale_id=sale_id,
        purchaser_email=purchase.get("email"),
        purchaser_name=purchase.get("full_name"),
        product_permalink=product,
        refunded=refunded,
        disputed=disputed,
    )
