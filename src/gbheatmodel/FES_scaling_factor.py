# src/gbheatmodel/FES_scaling_factor.py

from __future__ import annotations
from pathlib import Path
import pandas as pd

from .path import FES_DATA


def FES_scaling_factor_calc(future_year, FES, scenario):
    """
    Calculate the scaling factor for the heat demand data for a given year, FES year, and FES scenario.
    Needed due to large assumptions around fabric upgrades, building standards, and behavioural change in FES
    which drives down heat demand dramatically.
    """
    
    file = 'data/FES Spatial Heat Model/' + FES + '/' + 'Annual Heat Demand - FES' + FES[-2:] + '.csv'
    if scenario == 'LW':
        scenario = 'Leading the Way'
    elif scenario == 'CT':
        scenario = 'Consumer Transformation'
    elif scenario == 'ST':
        scenario = 'System Transformation'
    elif scenario == 'FS':
        scenario = 'Falling Short'
    elif scenario == 'SP':
        scenario = 'Steady Progression'
    data = pd.read_csv(file, index_col=0)
    future_heat_demand = data.loc[scenario, str(future_year)]
    # RHPP dataset is from 2014-2016 so using 2015 demand levels to scale against
    # However, the modelling predicts historic heat demand in 2020 exactly. So going with that as baseline fabric level.
    RHPP_heat_demand = data.loc['History', '2020']

    return future_heat_demand / RHPP_heat_demand

# ---------------------------------------------------------------------------
# Self-test (only when executed directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Example test
    scale = FES_scaling_factor_calc(2050, "2022", "LW")
    print("Scaling factor (LW, 2050, FES 2022):", scale)
