from fastapi import FastAPI

from app.utils import get_version

__version__ = get_version()

app = FastAPI(title="cartwatch", version=__version__)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
