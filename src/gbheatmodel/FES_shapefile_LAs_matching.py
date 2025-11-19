import geopandas as gpd
import pandas as pd
import numpy as np
import atlite

import matplotlib.pyplot as plt
import heat_pattern
import FES_heat_supply_data
from shapely.geometry import Point
from sklearn.neighbors import NearestNeighbors

def find_mismatch_FES_shapefile(LAs_FES, LA_shapefile):
    
    LA_shapefile = gpd.read_file('data/LA_UK/new_version/UK_LAs_Boundaries_files/LAs_shapefile_2021/LAD_DEC_2021_GB_BFC.shp')
    

    # Get unique LA names
    shapefile_LAs = LA_shapefile[['LAD21NM',
                                  'LONG',
                                  'LAT',
                                  'LAD21CD']].drop_duplicates()
    
    shapefile_LAs.columns = ['name',
                             'LONG',
                             'LAT',
                             'LAD21CD']
    
    shapefile_LAs['name'] = shapefile_LAs['name'].str.lower()

    LAs_FES = pd.read_csv('data/LA_UK/new_version/uk_LA_locations_FES.csv', index_col=0)
    LAs_FES['name'] = LAs_FES['name'].str.lower()

    # Find matching Local Authorities
    matching_LAs = set(shapefile_LAs['name']).intersection(set(LAs_FES['name']))

    # Find mismatching Local Authorities (present in one but not the other)
    only_in_shapefile_LAs = set(shapefile_LAs['name']) - set(LAs_FES['name'])
    only_in_LAs_FES = set(LAs_FES['name']) - set(shapefile_LAs['name'])

    # First get the maximum length needed
    max_length = max(len(matching_LAs), 
                     len(only_in_shapefile_LAs),
                     len(only_in_LAs_FES))

    # Create padded lists
    matching_padded = list(matching_LAs) + [None] * (max_length - len(matching_LAs))
    shapefile_padded = list(only_in_shapefile_LAs) + [None] * (max_length - len(only_in_shapefile_LAs))
    fes_padded = list(only_in_LAs_FES) + [None] * (max_length - len(only_in_LAs_FES))
    
    # Create DataFrame
    list_of_LAs = pd.DataFrame({
                                'matching_LAs': matching_padded,
                                'only_in_shapefile_LAs': shapefile_padded,
                                'only_in_LAs_FES': fes_padded
                                })

    # Add longitude and latitude for matching LAs
    LAs_FES.set_index('name', inplace=True)
    list_of_LAs['matching_long'] = list_of_LAs['matching_LAs'].map(LAs_FES['x'])
    list_of_LAs['matching_lat'] = list_of_LAs['matching_LAs'].map(LAs_FES['y'])

    # Add longitude and latitude for LAs only in FES
    list_of_LAs['fes_long'] = list_of_LAs['only_in_LAs_FES'].map(LAs_FES['x'])
    list_of_LAs['fes_lat'] = list_of_LAs['only_in_LAs_FES'].map(LAs_FES['y'])

    # Add longitude and latitude for LAs only in shapefile
    shapefile_LAs.set_index('name', inplace=True)
    list_of_LAs['shapefile_long'] = list_of_LAs['only_in_shapefile_LAs'].map(shapefile_LAs['LONG'])
    list_of_LAs['shapefile_lat'] = list_of_LAs['only_in_shapefile_LAs'].map(shapefile_LAs['LAT'])
    list_of_LAs['CODE_x'] = list_of_LAs['only_in_shapefile_LAs'].map(shapefile_LAs['LAD21CD'])
    
    # Reorder the columns manually
    list_of_LAs = list_of_LAs[['matching_LAs',
                               'matching_long',
                               'matching_lat',
                               'only_in_shapefile_LAs',
                               'shapefile_long',
                               'shapefile_lat',
                               'CODE_x',
                               'only_in_LAs_FES',
                               'fes_long', 'fes_lat']
                              ]
    
    # Save to CSV for inspection
    # list_of_LAs.to_csv('data/LA_UK/new_version/list_of_LAs_comparison.csv', index=False)
    
    return list_of_LAs


def match_FES_and_shapefile_LAs(df, future_year, FES, scenario):
    # Get FES heat supply data
    df = FES_heat_supply_data.year_FES_heat_supply(future_year, FES, scenario)
    df.columns = df.columns.str.replace(r'stock ', '', regex=False)
    df.index = df.index.str.replace(r'Chiltern District', 'Chiltern')
    df.index = df.index.str.replace(r'South Bucks District', 'South Bucks')
    df.index = df.index.str.replace(r'Wycombe District', 'Wycombe')
    df.index = df.index.str.replace(r'Aylesbury Vale District', 'Aylesbury Vale')

    aggregation = {
        'North Northamptonshire': ['East Northamptonshire',
                                   'Corby',
                                   'Wellingborough',
                                   'Kettering'],
        'West Northamptonshire': ['Daventry',
                                  'Northampton',
                                  'South Northamptonshire'],
        'Buckinghamshire': ['South Bucks',
                            'Chiltern', 
                            'Aylesbury Vale', 
                            'Wycombe']
    }

    non_sum = ['CODE_x',
               'Year', 
               'Scenario',
               'Sector']
    
    aggregated_rows = []

    for new_LA, org_LA in aggregation.items():
        try:
            group_df = df.loc[org_LA]
        except KeyError as e:
            print(f"Missing LAs in original data: {e}")
            continue

        base_info = group_df.iloc[0][non_sum].copy()
        base_info['index'] = new_LA  # store new name explicitly

        numeric_sum = group_df.drop(columns=non_sum, errors='ignore').apply(pd.to_numeric, errors='coerce').sum()
        full_row = pd.concat([base_info, numeric_sum])
        aggregated_rows.append(full_row)

    aggregated_df = pd.DataFrame(aggregated_rows)
    aggregated_df.set_index("index", inplace=True)
    
    # Drop original LAs
    all_originals = [la for group in aggregation.values() for la in group]
    df = df.drop(index=all_originals, errors='ignore')

    # Append aggregated LAs
    df = pd.concat([df, aggregated_df], axis=0)
    
    new_codes = {
                'North Northamptonshire': 'E06000061',
                'West Northamptonshire': 'E06000062',
                'Buckinghamshire': 'E06000060'
                }
    new_LAs_mask = df.index.isin(new_codes.keys())
    df.loc[new_LAs_mask, 'CODE_x'] = df.loc[new_LAs_mask].index.map(new_codes)

    df.index = df.index.map(str)
    df = df.sort_index()
    # df.reset_index(inplace=True)
    df.rename(columns={'index': 'Local_Authority'}, inplace=True)
    # df.to_csv('data/LA_UK/new_version/matched_FES_heating.csv', index=False)

    return df





if __name__ == "__main__":
    # # Load the shapefile and FES data
    LA_shapefile = gpd.read_file('data/LA_UK/new_version/UK_LAs_Boundaries_files/LAs_shapefile_2021/LAD_DEC_2021_GB_BFC.shp')
    LAs_FES = pd.read_csv('data/LA_UK/new_version/uk_LA_locations_FES.csv', index_col=0)

    # # Match LAs
    list_of_LAs = match_list_of_LAs(LAs_FES, LA_shapefile)
    
    # # Map unmatched LAs to closest matched LAs
    # FES_to_matched, shapefile_to_matched = map_unmatched_LAs_to_closest(list_of_LAs)
    
    # # Map shapefile-only LAs to FES-only LAs
    # shapefile_only_to_FES_only(list_of_LAs)
    weather_year = 2024
    FES = '2022'
    future_year = 2050
    scenario = "LW"
    df = FES_heat_supply_data.year_FES_heat_supply(future_year, FES, scenario)
    matched_FES = match_FES_and_shapefile_LAs(df, future_year, FES, scenario)