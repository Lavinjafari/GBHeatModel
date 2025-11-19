from __future__ import annotations
from pathlib import Path
import os

_MARKERS = {"data", "gbheatmodel", ".git", ".env"}

def _find_root_fallback(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        names = {p.name for p in cur.iterdir()} if cur.exists() else set()
        if _MARKERS.intersection(names) >= {"data", "gbheatmodel"}:
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start

def get_project_root() -> Path:
    env = os.getenv("PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _find_root_fallback(Path(__file__).resolve().parents[1])

PROJECT_ROOT = get_project_root()

DATA_DIR      = PROJECT_ROOT / "data"
ATILITE       = DATA_DIR / "Atilite"
AIR_TEMP   = DATA_DIR / "air_temp"
SHAPEFILE = DATA_DIR / "LAs_shapefiles_2021"
HEAT_USAGE  = DATA_DIR / "heat_demand_profiles_patterns"
FES_DATA    = DATA_DIR / "FES Spatial Heat Model"
NOTEBOOKS_DIR = PROJECT_ROOT / "Notebooks"
OUTPUTS_DIR   = PROJECT_ROOT / "outputs"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def path_from_root(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)

def path_in_data(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
