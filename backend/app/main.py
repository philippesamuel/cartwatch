from importlib.metadata import version

from fastapi import FastAPI

__version__ = version("carwatch_backend")

app = FastAPI(title="cartwatch", version=__version__)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
