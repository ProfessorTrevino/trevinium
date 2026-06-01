from __future__ import annotations

from pydantic import BaseModel, Field


class ActivationRequest(BaseModel):
    license_key: str = Field(min_length=1)
    install_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    version_name: str | None = None
    product_permalink: str | None = None
    signature_sha256: str | None = None


class RevalidateRequest(BaseModel):
    install_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    version_name: str | None = None
    product_permalink: str | None = None
    activation_token: str | None = None
    reason: str | None = None


class DeactivateRequest(BaseModel):
    install_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    product_permalink: str | None = None
    activation_token: str | None = None


class ActivationResponse(BaseModel):
    allowed: bool
    status: str
    message: str
    token: str | None = None
    license_hint: str | None = None
    revoked: bool = False
