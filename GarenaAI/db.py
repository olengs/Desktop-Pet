from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

try:
    from config import ENV_PATH, config_value
except ImportError:  # Allows `python -m GarenaAI.test_db_connection` from repo root.
    from GarenaAI.config import ENV_PATH, config_value


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PGCONNECT_PATH = REPO_ROOT / "pgConnect.json"


class DatabaseConfigError(RuntimeError):
    """Raised when PostgreSQL connection settings are missing or invalid."""


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str | None = None
    sslmode: str = "require"
    connect_timeout: int = 10

    def connect_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
        }
        if self.password:
            kwargs["password"] = self.password
        return kwargs


def load_postgres_config(
    pgconnect_path: str | Path | None = None,
    server_name: str | None = None,
) -> PostgresConfig:
    """Load PostgreSQL settings from .config/.env, with pgConnect.json fallback."""
    load_dotenv(ENV_PATH)
    load_dotenv(REPO_ROOT / ".env")

    config_path = Path(
        _setting_first("GARENA_PGCONNECT_PATH")
        or pgconnect_path
        or DEFAULT_PGCONNECT_PATH
    )
    server = (
        _load_pgconnect_server(
            config_path,
            _setting_first("GARENA_PGCONNECT_SERVER") or server_name,
        )
        if config_path.exists()
        else {}
    )

    host = _setting_first("GARENA_DB_HOST", "DB_HOST", "PGHOST") or _server_value(server, "Host")
    port = _int_value(
        _setting_first("GARENA_DB_PORT", "DB_PORT", "PGPORT") or _server_value(server, "Port") or 5432,
        "database port",
    )
    dbname = (
        _setting_first("GARENA_DB_NAME", "DB_NAME", "PGDATABASE")
        or _server_value(server, "MaintenanceDB", "Database", "DBName")
    )
    user = _setting_first("GARENA_DB_USER", "DB_USER", "PGUSER") or _server_value(
        server,
        "Username",
        "User",
    )
    password = _setting_first("GARENA_DB_PASSWORD", "DB_PASSWORD", "PGPASSWORD") or _server_value(
        server,
        "Password",
    )
    sslmode = _setting_first("GARENA_DB_SSLMODE", "DB_SSLMODE", "PGSSLMODE") or _server_value(
        server,
        "SSLMode",
    ) or "require"
    connect_timeout = _int_value(
        _setting_first("GARENA_DB_CONNECT_TIMEOUT", "DB_CONNECT_TIMEOUT", "PGCONNECT_TIMEOUT") or 10,
        "database connect timeout",
    )

    missing = [
        name
        for name, value in {
            "host": host,
            "dbname": dbname,
            "user": user,
        }.items()
        if not value
    ]
    if missing:
        raise DatabaseConfigError(f"missing PostgreSQL setting(s): {', '.join(missing)}")

    return PostgresConfig(
        host=str(host),
        port=port,
        dbname=str(dbname),
        user=str(user),
        password=str(password) if password else None,
        sslmode=str(sslmode),
        connect_timeout=connect_timeout,
    )


def get_connection(config: PostgresConfig | None = None) -> psycopg.Connection:
    """Open a psycopg3 connection using the project PostgreSQL settings."""
    postgres_config = config or load_postgres_config()
    return psycopg.connect(**postgres_config.connect_kwargs(), row_factory=dict_row)


def check_connection() -> dict[str, Any]:
    """Run a tiny DB query and return basic non-secret server metadata."""
    config = load_postgres_config()
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    1 AS ok,
                    current_database() AS database,
                    current_user AS username,
                    version() AS version
                """
            )
            row = cur.fetchone()

    if row is None:
        raise RuntimeError("PostgreSQL health query returned no rows")

    return {
        "ok": row["ok"],
        "host": config.host,
        "port": config.port,
        "database": row["database"],
        "username": row["username"],
        "sslmode": config.sslmode,
        "version": row["version"],
    }


def _load_pgconnect_server(path: Path, server_name: str | None) -> Mapping[str, Any]:
    if not path.exists():
        raise DatabaseConfigError(f"PostgreSQL connection file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatabaseConfigError(f"invalid PostgreSQL connection JSON in {path}: {exc}") from exc

    servers = payload.get("Servers")
    if not isinstance(servers, Mapping) or not servers:
        raise DatabaseConfigError(f"no Servers entries found in {path}")

    if server_name:
        selected = servers.get(server_name)
        if selected is None:
            selected = next(
                (
                    server
                    for server in servers.values()
                    if isinstance(server, Mapping) and server.get("Name") == server_name
                ),
                None,
            )
        if not isinstance(selected, Mapping):
            raise DatabaseConfigError(f"server {server_name!r} not found in {path}")
        return selected

    first_key = sorted(servers.keys(), key=str)[0]
    first_server = servers[first_key]
    if not isinstance(first_server, Mapping):
        raise DatabaseConfigError(f"server {first_key!r} in {path} is not an object")
    return first_server


def _setting_first(*keys: str) -> str | None:
    for key in keys:
        value = config_value(key, "")
        if value:
            return value
    return None


def _server_value(server: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = server.get(key)
        if value not in (None, ""):
            return value
    return None


def _int_value(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseConfigError(f"invalid {label}: {value!r}") from exc
