from __future__ import annotations

import time

import jwt

from config import Settings


def build_license_hint(license_key: str) -> str:
    trimmed = license_key.strip()
    visible = trimmed[-6:] if len(trimmed) >= 6 else trimmed
    return f"...{visible}"


def issue_activation_token(
    settings: Settings,
    *,
    license_hash: str,
    license_hint: str,
    install_id: str,
    application_id: str,
    product_permalink: str,
) -> str:
    now_millis = int(time.time() * 1000)
    revalidate_after = now_millis + settings.revalidation_interval_hours * 60 * 60 * 1000
    offline_grace_until = revalidate_after + settings.offline_grace_hours * 60 * 60 * 1000

    payload = {
        "iss": settings.token_issuer,
        "sub": license_hash,
        "status": "active",
        "license_hint": license_hint,
        "install_id": install_id,
        "application_id": application_id,
        "product_permalink": product_permalink,
        "issued_at_millis": now_millis,
        "activated_at_millis": now_millis,
        "last_validated_at_millis": now_millis,
        "revalidate_after_millis": revalidate_after,
        "offline_grace_until_millis": offline_grace_until,
    }
    return jwt.encode(payload, settings.activation_signing_private_key, algorithm="RS256")
