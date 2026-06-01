from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database_path: str
    token_issuer: str
    gumroad_verify_url: str
    gumroad_product_permalink: str
    gumroad_access_token: str | None
    activation_signing_private_key: str
    revalidation_interval_hours: int
    offline_grace_hours: int
    max_active_installs: int


def _read_private_key() -> str:
    b64_key = os.environ.get("ACTIVATION_SIGNING_PRIVATE_KEY_B64", "").strip()
    if b64_key:
        return base64.b64decode(b64_key).decode("utf-8")

    inline_key = os.environ.get("ACTIVATION_SIGNING_PRIVATE_KEY", "").strip()
    if inline_key:
        return inline_key.replace("\\n", "\n")

    key_path = os.environ.get("ACTIVATION_SIGNING_PRIVATE_KEY_PATH", "").strip()
    if key_path:
        return Path(key_path).expanduser().read_text(encoding="utf-8")

    raise RuntimeError(
        "Set ACTIVATION_SIGNING_PRIVATE_KEY_B64, ACTIVATION_SIGNING_PRIVATE_KEY, "
        "or ACTIVATION_SIGNING_PRIVATE_KEY_PATH."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    gumroad_product_permalink = os.environ.get("GUMROAD_PRODUCT_PERMALINK", "").strip()
    if not gumroad_product_permalink:
        raise RuntimeError("GUMROAD_PRODUCT_PERMALINK is required.")

    return Settings(
        host=os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        database_path=os.environ.get("DATABASE_PATH", "./activation.db").strip() or "./activation.db",
        token_issuer=os.environ.get("TOKEN_ISSUER", "trevinium-activation").strip() or "trevinium-activation",
        gumroad_verify_url=os.environ.get("GUMROAD_VERIFY_URL", "https://api.gumroad.com/v2/licenses/verify").strip(),
        gumroad_product_permalink=gumroad_product_permalink,
        gumroad_access_token=os.environ.get("GUMROAD_ACCESS_TOKEN", "").strip() or None,
        activation_signing_private_key=_read_private_key(),
        revalidation_interval_hours=int(os.environ.get("REVALIDATION_INTERVAL_HOURS", "168")),
        offline_grace_hours=int(os.environ.get("OFFLINE_GRACE_HOURS", "336")),
        max_active_installs=int(os.environ.get("MAX_ACTIVE_INSTALLS", "2")),
    )
