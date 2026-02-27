import tomllib
from pathlib import Path


def get_version() -> str:
    with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]
