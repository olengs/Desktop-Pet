import os
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as pgconnection
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def getconnection() -> pgconnection:
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
