from __future__ import annotations

from fastapi import FastAPI

from config import get_settings
from db import (
    count_active_installations,
    deactivate_installation,
    get_installation,
    get_license,
    hash_license_key,
    init_db,
    open_db,
    upsert_installation,
    upsert_license,
)
from gumroad import verify_license
from schemas import (
    ActivationRequest,
    ActivationResponse,
    DeactivateRequest,
    RevalidateRequest,
)
from tokens import build_license_hint, issue_activation_token


app = FastAPI(title="Trevinium Activation Backend", version="1.0.0")
settings = None


@app.on_event("startup")
async def on_startup() -> None:
    global settings
    settings = get_settings()
    init_db()


def _require_settings():
    if settings is None:
        raise RuntimeError("Activation backend is still starting.")
    return settings


def _product_mismatch(request_product_permalink: str | None) -> bool:
    cfg = _require_settings()
    return bool(
        request_product_permalink
        and request_product_permalink.strip()
        and request_product_permalink.strip() != cfg.gumroad_product_permalink
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/activation/activate", response_model=ActivationResponse)
async def activate(request: ActivationRequest) -> ActivationResponse:
    if _product_mismatch(request.product_permalink):
        return ActivationResponse(
            allowed=False,
            status="product_mismatch",
            message="The request product permalink does not match the backend configuration.",
        )

    cfg = _require_settings()
    gumroad_result = await verify_license(
        cfg,
        license_key=request.license_key,
        product_permalink=cfg.gumroad_product_permalink,
    )
    if not gumroad_result.valid:
        return ActivationResponse(
            allowed=False,
            status=gumroad_result.status,
            message=gumroad_result.message,
            revoked=gumroad_result.status == "license_revoked",
        )

    license_hash = hash_license_key(request.license_key)

    with open_db() as connection:
        upsert_license(
            connection,
            license_hash=license_hash,
            raw_license_key=request.license_key.strip(),
            product_permalink=cfg.gumroad_product_permalink,
            sale_id=gumroad_result.sale_id,
            purchaser_email=gumroad_result.purchaser_email,
            purchaser_name=gumroad_result.purchaser_name,
            revoked=False,
            last_status="active",
            checked_at_millis=_now_millis(),
        )

        existing_install = get_installation(
            connection,
            install_id=request.install_id,
            application_id=request.application_id,
        )
        active_install_count = count_active_installations(connection, license_hash)
        if existing_install is None and active_install_count >= cfg.max_active_installs:
            return ActivationResponse(
                allowed=False,
                status="device_limit_reached",
                message="This license is already in use on the maximum allowed number of devices.",
            )

        upsert_installation(
            connection,
            install_id=request.install_id,
            license_hash=license_hash,
            application_id=request.application_id,
            version_name=request.version_name,
            activated_at_millis=_now_millis(),
            last_validated_at_millis=_now_millis(),
            active=True,
        )

    token = issue_activation_token(
        cfg,
        license_hash=license_hash,
        license_hint=build_license_hint(request.license_key),
        install_id=request.install_id,
        application_id=request.application_id,
        product_permalink=cfg.gumroad_product_permalink,
    )
    return ActivationResponse(
        allowed=True,
        status="active",
        message="Activation completed successfully.",
        token=token,
        license_hint=build_license_hint(request.license_key),
    )


@app.post("/api/v1/activation/revalidate", response_model=ActivationResponse)
async def revalidate(request: RevalidateRequest) -> ActivationResponse:
    cfg = _require_settings()
    if _product_mismatch(request.product_permalink):
        return ActivationResponse(
            allowed=False,
            status="product_mismatch",
            message="The request product permalink does not match the backend configuration.",
        )

    with open_db() as connection:
        installation = get_installation(
            connection,
            install_id=request.install_id,
            application_id=request.application_id,
        )
        if installation is None:
            return ActivationResponse(
                allowed=False,
                status="activation_missing",
                message="No activation was found for this install. Enter the Gumroad license key again.",
            )

        license_row = get_license(connection, installation["license_hash"])
        if license_row is None:
            return ActivationResponse(
                allowed=False,
                status="activation_missing",
                message="The backend has no stored license for this install. Enter the Gumroad license key again.",
            )

        if license_row["revoked"] or installation["revoked"]:
            return ActivationResponse(
                allowed=False,
                status="license_revoked",
                message="This license or install has been revoked on the backend.",
                revoked=True,
            )

        gumroad_result = await verify_license(
            cfg,
            license_key=license_row["raw_license_key"],
            product_permalink=cfg.gumroad_product_permalink,
        )
        if not gumroad_result.valid:
            revoked = gumroad_result.status == "license_revoked"
            upsert_license(
                connection,
                license_hash=installation["license_hash"],
                raw_license_key=license_row["raw_license_key"],
                product_permalink=cfg.gumroad_product_permalink,
                sale_id=license_row["sale_id"],
                purchaser_email=license_row["purchaser_email"],
                purchaser_name=license_row["purchaser_name"],
                revoked=revoked,
                last_status=gumroad_result.status,
                checked_at_millis=_now_millis(),
            )
            if revoked:
                deactivate_installation(
                    connection,
                    install_id=request.install_id,
                    application_id=request.application_id,
                )

            return ActivationResponse(
                allowed=False,
                status=gumroad_result.status,
                message=gumroad_result.message,
                revoked=revoked,
            )

        upsert_license(
            connection,
            license_hash=installation["license_hash"],
            raw_license_key=license_row["raw_license_key"],
            product_permalink=cfg.gumroad_product_permalink,
            sale_id=gumroad_result.sale_id or license_row["sale_id"],
            purchaser_email=gumroad_result.purchaser_email or license_row["purchaser_email"],
            purchaser_name=gumroad_result.purchaser_name or license_row["purchaser_name"],
            revoked=False,
            last_status="active",
            checked_at_millis=_now_millis(),
        )
        upsert_installation(
            connection,
            install_id=request.install_id,
            license_hash=installation["license_hash"],
            application_id=request.application_id,
            version_name=request.version_name or installation["version_name"],
            activated_at_millis=installation["activated_at"],
            last_validated_at_millis=_now_millis(),
            active=True,
        )

    token = issue_activation_token(
        cfg,
        license_hash=installation["license_hash"],
        license_hint=build_license_hint(license_row["raw_license_key"]),
        install_id=request.install_id,
        application_id=request.application_id,
        product_permalink=cfg.gumroad_product_permalink,
    )
    return ActivationResponse(
        allowed=True,
        status="active",
        message="License revalidated successfully.",
        token=token,
        license_hint=build_license_hint(license_row["raw_license_key"]),
    )


@app.post("/api/v1/activation/deactivate", response_model=ActivationResponse)
async def deactivate(request: DeactivateRequest) -> ActivationResponse:
    with open_db() as connection:
        deactivate_installation(
            connection,
            install_id=request.install_id,
            application_id=request.application_id,
        )

    return ActivationResponse(
        allowed=True,
        status="deactivated",
        message="This device has been deactivated and its seat was released.",
    )


def _now_millis() -> int:
    import time

    return int(time.time() * 1000)
