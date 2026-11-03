"""Ensure GBHeat weather-year inputs exist before a notebook model run.

Uses the unchanged GBHeat data directory and the Zenodo archive downloader.
No scientific model functions or parameters are modified.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .path import path_in_data
from . import zenodo_inputs


def _grid_ids(air_file: Path) -> set[str]:
    """Read only the header of GBHeat's half-hourly air-temperature CSV."""
    with air_file.open("r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    if len(header) < 2:
        raise ValueError(f"Invalid air-temperature CSV header: {air_file}")
    ids = [value.strip() for value in header[1:]]
    if not ids or any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Invalid or duplicate grid IDs in {air_file}")
    return set(ids)


def check_weather_inputs(weather_year: int, *, data_root: Path | None = None) -> dict:
    """Read-only availability and layout check for one historical weather year."""
    year = int(weather_year)
    if not 2010 <= year <= 2024:
        raise ValueError("weather_year must be in 2010..2024")
    root = Path(data_root) if data_root is not None else path_in_data()
    temperature = root / "air_temp" / f"air_temp_{year}.csv"
    daily = root / "air_temp" / f"average_day_air_temp_{year}.csv"
    patterns = root / "heat_demand_profiles_patterns" / f"HD_heat_patterns_{year}"
    temp_ok = temperature.is_file() and temperature.stat().st_size > 0
    daily_ok = daily.is_file() and daily.stat().st_size > 0
    expected = {f"({g})_{year}.csv" for g in _grid_ids(temperature)} if temp_ok else None
    existing = {f.name for f in patterns.glob(f"(*)_{year}.csv") if f.is_file() and f.stat().st_size > 0} if patterns.is_dir() else set()
    patterns_ok = expected is not None and expected == existing
    return {
        "year": year, "root": root, "temperature": temperature, "daily": daily,
        "patterns": patterns, "temperature_ok": temp_ok, "daily_ok": daily_ok,
        "patterns_ok": patterns_ok, "expected_grids": len(expected) if expected is not None else None,
        "found_patterns": len(existing),
    }


def ensure_weather_inputs(weather_year: int, *, data_root: Path | None = None,
                          download_missing: bool = True, verbose: bool = True) -> dict:
    """Prepare GBHeat's temperature and heating-pattern inputs automatically.

    A completely present year does not invoke Zenodo or access the network.
    Missing input kinds are obtained from the two Zenodo ZIPs, cached once,
    and extracted directly to the existing GBHeat data layout.
    Existing differing files are never overwritten.
    """
    state = check_weather_inputs(weather_year, data_root=data_root)
    root, year = state["root"], state["year"]
    needs_temp = not (state["temperature_ok"] and state["daily_ok"])
    needs_patterns = not state["patterns_ok"]
    if not (needs_temp or needs_patterns):
        if verbose:
            print(f"GBHeat {year}: both temperature CSVs and {state['found_patterns']} grid patterns ready; no download.")
        return state
    if not download_missing:
        raise FileNotFoundError(f"GBHeat weather inputs are incomplete for {year}: {state}")

    # A missing daily file is expected to be present in the Zenodo archive.
    # Don't fetch the large patterns ZIP if only temperature data is missing.
    manifest = None
    for kind in ("temperature", "patterns"):
        if (kind == "temperature" and not needs_temp) or (kind == "patterns" and not needs_patterns):
            continue
        archive = root / ("air_temp" if kind == "temperature" else "heat_demand_profiles_patterns") / "_zenodo_downloads" / zenodo_inputs.FULL_ARCHIVE_NAMES[kind]
        if not archive.is_file():
            if manifest is None:
                manifest = zenodo_inputs.get_manifest()
            entry = zenodo_inputs.select_archive(manifest, kind)
            if verbose:
                print(f"GBHeat {year}: downloading full {kind} ZIP once ({entry.get('size')} bytes).")
            zenodo_inputs.download(entry, archive)
        else:
            if verbose:
                print(f"GBHeat {year}: using cached {kind} ZIP.")
        count = zenodo_inputs.extract_weather_year(archive, kind, year, root)
        if verbose:
            print(f"GBHeat {year}: installed {count} {kind} file(s).")

    result = check_weather_inputs(year, data_root=root)
    if not (result["temperature_ok"] and result["daily_ok"] and result["patterns_ok"]):
        raise RuntimeError(f"Weather inputs still incomplete after extraction for {year}: {result}")
    if verbose:
        print(f"GBHeat {year}: ready ({result['expected_grids']} grid patterns).")
    return result
