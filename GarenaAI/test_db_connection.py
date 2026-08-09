from __future__ import annotations

import sys

try:
    from db import DatabaseConfigError, check_connection
except ImportError:  # Allows `python -m GarenaAI.test_db_connection` from repo root.
    from GarenaAI.db import DatabaseConfigError, check_connection


def main() -> int:
    try:
        info = check_connection()
    except DatabaseConfigError as exc:
        print(f"Database configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Database connection failed: {exc}", file=sys.stderr)
        print(
            "If the server requires a password, set GARENA_DB_PASSWORD, DB_PASSWORD, or PGPASSWORD.",
            file=sys.stderr,
        )
        return 1

    version_line = str(info["version"]).splitlines()[0]
    print("Database connection OK")
    print(
        "server={host}:{port} database={database} user={username} sslmode={sslmode}".format(
            **info
        )
    )
    print(f"postgres={version_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
