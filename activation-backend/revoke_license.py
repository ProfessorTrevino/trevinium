from __future__ import annotations

import argparse

from db import hash_license_key, init_db, open_db, revoke_installation, revoke_license


def main() -> None:
    parser = argparse.ArgumentParser(description="Revoke a stored license or install.")
    parser.add_argument("--license-key", help="The raw Gumroad license key to revoke.")
    parser.add_argument("--install-id", help="The install id to revoke.")
    parser.add_argument("--application-id", help="Required with --install-id.")
    args = parser.parse_args()

    init_db()

    if args.license_key:
        with open_db() as connection:
            revoke_license(connection, hash_license_key(args.license_key))
        print("License revoked.")
        return

    if args.install_id and args.application_id:
        with open_db() as connection:
            revoke_installation(
                connection,
                install_id=args.install_id,
                application_id=args.application_id,
            )
        print("Installation revoked.")
        return

    parser.error("Use --license-key or both --install-id and --application-id.")


if __name__ == "__main__":
    main()
