from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from api.ingest import router as ingest_router
from utils import get_version


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":       # allow unauthenticated health checks
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        expected = request.app.state.api_key
        if not api_key or not secrets.compare_digest(api_key, expected):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return await call_next(request)

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
    lifespan=lifespan
    )
app.add_middleware(APIKeyMiddleware)
app.include_router(ingest_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
