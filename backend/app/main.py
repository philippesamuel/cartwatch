from fastapi import FastAPI

__version__ = "0.1.0"

app = FastAPI(title="cartwatch", version=__version__)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "version": __version__}
