from __future__ import annotations

from typing import Literal


Heating_Pattern = Literal["daytime", "bi-modal", "continuous", "ASHP", "GSHP"]


def heat_demand_for_one_pattern_for_one_day(
    heating_pattern: Heating_Pattern,
    Td: float,
) -> float:
    """
    Calculate the daily heat demand for one dwelling
    for a given heating pattern and average daily temperature.

    Parameters
    ----------
    heating_pattern : {"daytime", "bi-modal", "continuous", "ASHP", "GSHP"}
        Type of heating pattern / technology.
    Td : float
        Average daily external temperature [°C].

    Returns
    -------
    float
        Daily heat demand per dwelling [kWh/day] for the given pattern.
    """
    if heating_pattern == "daytime":
        C = {"TBp": 14.3, "mp1": -5.39, "cp1": 88.8, "mp2": -0.94, "cp2": 25.0, "R2": 0.97}
    elif heating_pattern == "bi-modal":
        C = {"TBp": 13.9, "mp1": -5.22, "cp1": 83.7, "mp2": -0.82, "cp2": 22.4, "R2": 0.97}
    elif heating_pattern == "continuous":
        C = {"TBp": 14.3, "mp1": -6.18, "cp1": 102.6, "mp2": -1.24, "cp2": 31.8, "R2": 0.98}
    elif heating_pattern == "ASHP":
        C = {"TBp": 14.3, "mp1": -5.85, "cp1": 96.7, "mp2": -1.1, "cp2": 28.7}
    elif heating_pattern == "GSHP":
        C = {"TBp": 14.3, "mp1": -5.96, "cp1": 98.7, "mp2": -1.15, "cp2": 29.8}
    else:
        raise ValueError(f"Unknown heating_pattern: {heating_pattern!r}")

    # Piecewise linear model
    if Td < C["TBp"]:
        HD = C["mp1"] * Td + C["cp1"]
    else:
        HD = C["mp2"] * Td + C["cp2"]

    return float(HD)


if __name__ == "__main__":
    # Tiny sanity check
    for pattern in ["daytime", "bi-modal", "continuous", "ASHP", "GSHP"]:
        val = heat_demand_for_one_pattern_for_one_day(pattern, Td=5.0)
        print(pattern, "→", val)
