from __future__ import annotations

from pathlib import Path

try:
    from db import get_connection
except ImportError:  # Allows `python -m GarenaAI.initialize_db` from repo root.
    from GarenaAI.db import get_connection


SQL_PATH = Path(__file__).resolve().parent / "initializedb.sql"


def main() -> int:
    sql = SQL_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

    print(f"Database initialized from {SQL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
