import tomllib
from pathlib import Path


def get_version() -> str:
    with open(_find_file("pyproject.toml"), "rb") as f:
        return tomllib.load(f)["project"]["version"]


def find_env() -> Path:
    return _find_file(".env")


def _find_file(filename: str) -> Path:
    for parent in Path(__file__).parents:
        f = parent / filename
        if f.exists():
            return f
    return Path(filename)
