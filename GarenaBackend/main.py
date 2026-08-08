from fastapi import FastAPI, HTTPException

from db import getconnection

app = FastAPI()

@app.get("/")
def readroot():
    return {"status": "ok"}


@app.get("/health/db")
def healthdb():
    try:
        conn = getconnection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}")
    return {"status": "ok"}
