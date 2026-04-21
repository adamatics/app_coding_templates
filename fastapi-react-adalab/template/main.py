from fastapi import FastAPI

from app.api.main import include_all_routers
from app.core.db import init_db

app = FastAPI(title="fastapi-react-adalab")


@app.on_event("startup")
def startup() -> None:
    init_db()


include_all_routers(app, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
