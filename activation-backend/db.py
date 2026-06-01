from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import get_settings


def hash_license_key(license_key: str) -> str:
    return hashlib.sha256(license_key.strip().encode("utf-8")).hexdigest()


def init_db() -> None:
    database_path = Path(get_settings().database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                license_hash TEXT PRIMARY KEY,
                raw_license_key TEXT NOT NULL,
                product_permalink TEXT NOT NULL,
                sale_id TEXT,
                purchaser_email TEXT,
                purchaser_name TEXT,
                revoked INTEGER NOT NULL DEFAULT 0,
                last_status TEXT NOT NULL,
                last_gumroad_check_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS installations (
                install_id TEXT PRIMARY KEY,
                license_hash TEXT NOT NULL,
                application_id TEXT NOT NULL,
                version_name TEXT,
                activated_at INTEGER NOT NULL,
                last_validated_at INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (license_hash) REFERENCES licenses (license_hash)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_installations_license_hash
            ON installations (license_hash, active)
            """
        )


@contextmanager
def open_db() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(get_settings().database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def upsert_license(
    connection: sqlite3.Connection,
    *,
    license_hash: str,
    raw_license_key: str,
    product_permalink: str,
    sale_id: str | None,
    purchaser_email: str | None,
    purchaser_name: str | None,
    revoked: bool,
    last_status: str,
    checked_at_millis: int,
) -> None:
    connection.execute(
        """
        INSERT INTO licenses (
            license_hash, raw_license_key, product_permalink, sale_id,
            purchaser_email, purchaser_name, revoked, last_status,
            last_gumroad_check_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(license_hash) DO UPDATE SET
            raw_license_key = excluded.raw_license_key,
            product_permalink = excluded.product_permalink,
            sale_id = excluded.sale_id,
            purchaser_email = excluded.purchaser_email,
            purchaser_name = excluded.purchaser_name,
            revoked = excluded.revoked,
            last_status = excluded.last_status,
            last_gumroad_check_at = excluded.last_gumroad_check_at,
            updated_at = excluded.updated_at
        """,
        (
            license_hash,
            raw_license_key,
            product_permalink,
            sale_id,
            purchaser_email,
            purchaser_name,
            1 if revoked else 0,
            last_status,
            checked_at_millis,
            checked_at_millis,
            checked_at_millis,
        ),
    )


def upsert_installation(
    connection: sqlite3.Connection,
    *,
    install_id: str,
    license_hash: str,
    application_id: str,
    version_name: str | None,
    activated_at_millis: int,
    last_validated_at_millis: int,
    active: bool,
    revoked: bool = False,
) -> None:
    connection.execute(
        """
        INSERT INTO installations (
            install_id, license_hash, application_id, version_name,
            activated_at, last_validated_at, active, revoked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(install_id) DO UPDATE SET
            license_hash = excluded.license_hash,
            application_id = excluded.application_id,
            version_name = excluded.version_name,
            last_validated_at = excluded.last_validated_at,
            active = excluded.active,
            revoked = excluded.revoked
        """,
        (
            install_id,
            license_hash,
            application_id,
            version_name,
            activated_at_millis,
            last_validated_at_millis,
            1 if active else 0,
            1 if revoked else 0,
        ),
    )


def get_license(connection: sqlite3.Connection, license_hash: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM licenses WHERE license_hash = ?",
        (license_hash,),
    ).fetchone()


def get_installation(
    connection: sqlite3.Connection,
    *,
    install_id: str,
    application_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM installations
        WHERE install_id = ? AND application_id = ?
        """,
        (install_id, application_id),
    ).fetchone()


def count_active_installations(connection: sqlite3.Connection, license_hash: str) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM installations
        WHERE license_hash = ? AND active = 1 AND revoked = 0
        """,
        (license_hash,),
    ).fetchone()
    return int(row["total"]) if row else 0


def deactivate_installation(
    connection: sqlite3.Connection,
    *,
    install_id: str,
    application_id: str,
) -> None:
    connection.execute(
        """
        UPDATE installations
        SET active = 0
        WHERE install_id = ? AND application_id = ?
        """,
        (install_id, application_id),
    )


def revoke_license(connection: sqlite3.Connection, license_hash: str) -> None:
    connection.execute(
        "UPDATE licenses SET revoked = 1, updated_at = strftime('%s','now') * 1000 WHERE license_hash = ?",
        (license_hash,),
    )
    connection.execute(
        "UPDATE installations SET revoked = 1, active = 0 WHERE license_hash = ?",
        (license_hash,),
    )


def revoke_installation(connection: sqlite3.Connection, *, install_id: str, application_id: str) -> None:
    connection.execute(
        """
        UPDATE installations
        SET revoked = 1, active = 0
        WHERE install_id = ? AND application_id = ?
        """,
        (install_id, application_id),
    )
