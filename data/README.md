# GBHeat input data catalogue

This folder contains small, version-controlled model inputs. Large weather and weather-derived pattern datasets are **not included** in the repository archive. Keep the directory names unchanged: the Python modules and notebooks reference these paths.

| Location | Purpose | Availability |
|---|---|---|
| `FES_Spatial_Heat_Model/{2021,2022,2024,2025}/` | FES local-area heating-technology stocks, historical/future demand and scenario mapping | In repository; verify source redistribution conditions |
| `LAs_shapefile_2021/` | LAD December 2021 GB boundaries and required `.shp/.shx/.dbf/.prj/.cpg` components | In repository; document ONS source and attribution |
| `UK_Atlite_Grid_sq.gpkg` | ERA5-derived weather-grid geometry | In repository |
| `Scenario_Alignment/heat_techs_distribution_grid_square.csv` | Baseline spatial stock distribution for custom-scenario notebook | In repository |
| `spatial_operators/` | Precomputed grid/LA spatial-mapping metadata and matrix | In repository |
| `normalised_half_hourly_profiles.xlsx` | Heating-use profiles workbook | In repository; verify data licence and provenance |
| `air_temp/` | Weather-year temperatures, including `average_day_air_temp_<year>.csv` for COP | External dataset; final Zenodo DOI not yet confirmed |
| `heat_demand_profiles_patterns/` | Per-grid temperature-dependent heating-pattern profiles 2010–2024 | External dataset; final Zenodo DOI not yet confirmed |
| `Atlite/` | ERA5/Atlite source weather archives | External dataset; final Zenodo DOI not yet confirmed |
| `outputs/` | Recomputed heating/electricity/LA outputs and figures | Local, ignored by Git |

## Configuration and reproduction

1. Clone the repository and install `python -m pip install -e ".[notebooks]"`.
2. Obtain the external dataset versions matching your study and place them in the directories above, retaining filenames and nested directories.
3. Record weather year, FES vintage, pathway, future year and any COP/insulation assumptions.
4. Run the notebooks using their documented order and inspect conservation checks and units.

No verified automated dataset downloader or Zenodo DOI is included in the supplied archive. Do not claim a one-command fully reproducible installation until these are released and tested. When publishing Zenodo datasets, record **version/DOI, files, licence, source provenance, SHA-256 checksums, extraction paths and preprocessing scripts**.

## Output units

GBHeat input and output profiles should be checked at the file level. The saved modelled half-hourly heat and electric demand is in **kWh per half hour**. Annual total (TWh) = summed kWh / 1e9; half-hour mean power (GW) = kWh × 2 / 1e6.

## Geography caveat

The manuscript says 371 Local Authorities; the released LAD 2021 boundary set and Notebook 04 workflow use 363. Confirm which dataset/vintage each figure or computation uses before publishing equivalence claims.
