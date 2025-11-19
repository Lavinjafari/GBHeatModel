import pandas as pd
import geopandas as gpd
import numpy as np
import FES_heat_supply_data
import pprint



def heat_demand_for_one_pattern_for_one_day(heating_pattern, Td):
    """
    Calculate the heat demand for one day for a given number of dwellings, heating pattern, and average day temperature.
    """
    if heating_pattern == 'daytime':
        C = {'TBp':14.3, 'mp1':-5.39, 'cp1':88.8, 'mp2':-0.94, 'cp2':25.0, 'R2':0.97}
    elif heating_pattern == 'bi-modal':
        C = {'TBp':13.9, 'mp1':-5.22, 'cp1':83.7, 'mp2':-0.82, 'cp2':22.4, 'R2':0.97}
    elif heating_pattern == 'continuous':
        C = {'TBp':14.3, 'mp1':-6.18, 'cp1':102.6, 'mp2':-1.24, 'cp2':31.8, 'R2':0.98}
    elif heating_pattern == 'ASHP':
        C = {'TBp':14.3, 'mp1':-5.85, 'cp1':96.7, 'mp2':-1.1, 'cp2':28.7}
    elif heating_pattern == 'GSHP':
        C = {'TBp':14.3, 'mp1':-5.96, 'cp1':98.7, 'mp2':-1.15, 'cp2':29.8}

    # given a number of buildings using a heating pattern, calculate the heat demand using coefficients
    if Td < C['TBp']:
        HD = C['mp1'] * Td + C['cp1']
    elif Td >= C['TBp']:
        HD = C['mp2'] * Td + C['cp2']

    # calculate the heat demand for the given number of dwellings
    return HD



