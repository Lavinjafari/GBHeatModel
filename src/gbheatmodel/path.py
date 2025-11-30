from __future__ import annotations
from pathlib import Path
import os


def _find_root_fallback(start: Path) -> Path:
    """
    Walk upwards from `start` until we find the project root.

    We define the project root as the directory that contains BOTH:
      - a 'src' directory
      - a 'data' directory

    i.e. your layout:
        GBHeatModel/
          data/
          src/
          Notebooks/
          pyproject.toml
    """
    cur = start.resolve()

    for _ in range(10):
        if not cur.exists():
            break

        names = {p.name for p in cur.iterdir()}

        # This should be true in GBHeatModel/, not in src/ or src/gbheatmodel/
        if "data" in names and "src" in names:
            return cur

        if cur.parent == cur:
            break

        cur = cur.parent

    # Fallback: try to go two levels up from src/gbheatmodel → GBHeatModel
    try:
        return start.resolve().parents[2]
    except IndexError:
        return start.resolve()


def get_project_root() -> Path:
    """
    Determine the project root.

    Priority:
    1. Use PROJECT_ROOT environment variable if set.
    2. Otherwise, auto-detect by walking upwards from src/ (parent of gbheatmodel).
    """
    env = os.getenv("PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    # __file__ is .../src/gbheatmodel/path.py
    # parents[1] -> .../src
    src_dir = Path(__file__).resolve().parents[1]
    return _find_root_fallback(src_dir)


# ---- Core paths -----------------------------------------------------------

PROJECT_ROOT = get_project_root()

DATA_DIR      = PROJECT_ROOT / "data"
ATILITE       = DATA_DIR / "Atilite"
AIR_TEMP      = DATA_DIR / "air_temp"
SHAPEFILE     = DATA_DIR / "LAs_shapefiles_2021"
HEAT_USAGE    = DATA_DIR / "heat_demand_profiles_patterns"
FES_DATA      = DATA_DIR / "FES_Spatial_Heat_Model"   # keep this matching your folder name
NOTEBOOKS_DIR = PROJECT_ROOT / "Notebooks"
OUTPUTS_DIR   = PROJECT_ROOT / "outputs"


# ---- Helpers --------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    """Create directory (including parents) if it does not exist, and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def path_from_root(*parts: str) -> Path:
    """Build a path relative to the project root."""
    return PROJECT_ROOT.joinpath(*parts)


def path_in_data(*parts: str) -> Path:
    """Build a path inside the data directory."""
    return DATA_DIR.joinpath(*parts)
