import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from api.ingest import router as ingest_router
from utils import get_version

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str | None = Security(api_key_scheme)):
    if not api_key or not secrets.compare_digest(api_key, request.app.state.api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )


__version__ = get_version()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_api_key(app)
    yield


async def load_api_key(app: FastAPI) -> None:
    import os

    key = os.environ.get("API_KEY")
    if not key:
        raise RuntimeError("API_KEY env var is required")
    app.state.api_key = key


app = FastAPI(
    title="cartwatch",
    version=__version__,
    root_path="/api",
    lifespan=lifespan,
)
app.include_router(ingest_router, dependencies=[Depends(verify_api_key)])


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
