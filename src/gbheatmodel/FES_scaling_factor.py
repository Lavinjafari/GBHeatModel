# src/gbheatmodel/FES_scaling_factor.py

from __future__ import annotations
from pathlib import Path
import pandas as pd

from .path import FES_DATA


# ---------------------------------------------------------------------------
# Scenario name mapping (FES short codes → long names used in CSVs)
# ---------------------------------------------------------------------------

SCENARIO_MAP = {
    "LW": "Leading the Way",
    "CT": "Consumer Transformation",
    "ST": "System Transformation",
    "FS": "Falling Short",
    "SP": "Steady Progression"
}


def FES_scaling_factor_calc(
    future_year: int,
    FES: str,
    scenario: str
) -> float:
    """
    Calculate the scaling factor applied to heating profiles for a given:
    - future_year      (e.g. 2050)
    - FES dataset      (e.g. "2022")
    - scenario         (e.g. "LW", "CT", "ST", "FS")

    The scaling factor is:
        FES future heat demand / baseline 2020 heat demand

    Returns
    -------
    float
        Scalar multiplier
    """
    FES = str(FES)
    scenario = scenario.upper()

    # Convert scenario code → long format expected by the CSV
    if scenario not in SCENARIO_MAP:
        raise ValueError(
            f"Unknown FES scenario '{scenario}'. "
            f"Expected one of {list(SCENARIO_MAP.keys())}"
        )

    scenario_long = SCENARIO_MAP[scenario]

    # File name follows pattern:
    #   Annual Heat Demand - FESYY.csv
    # Example for FES 2022:
    #   Annual Heat Demand - FES22.csv
    short_fes = FES[-2:]
    filename = f"Annual Heat Demand - FES{short_fes}.csv"

    file_path: Path = Path(FES_DATA) / FES / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"❌ Could not find FES heat demand file:\n {file_path}\n"
            f"Check your directory structure under data/FES_Spatial_Heat_Model/{FES}/"
        )

    # Load heat demand CSV
    data = pd.read_csv(file_path, index_col=0)

    # Extract numbers
    try:
        future_heat_demand = data.loc[scenario_long, str(future_year)]
    except KeyError:
        raise KeyError(
            f"❌ Missing data for scenario '{scenario_long}' or year '{future_year}' "
            f"in file: {file_path}"
        )

    # Baseline: 2020 HISTORY value
    try:
        RHPP_heat_demand = data.loc["History", "2020"]
    except KeyError:
        raise KeyError(
            f"❌ CSV is missing baseline History / 2020 row."
            f" Needed to compute FES scaling factor."
        )

    # Final scaling factor
    return float(future_heat_demand / RHPP_heat_demand)


# ---------------------------------------------------------------------------
# Self-test (only when executed directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Example test
    scale = FES_scaling_factor_calc(2050, "2022", "LW")
    print("Scaling factor (LW, 2050, FES 2022):", scale)
