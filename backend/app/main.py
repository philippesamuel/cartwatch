from fastapi import FastAPI

from app.api.ingest import router as ingest_router
from app.utils import get_version

__version__ = get_version()


app = FastAPI(title="cartwatch", version=__version__)
app.include_router(ingest_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
