"""Download weather-year GBHeat input data from a Zenodo record.

Standard-library only; no changes to the GBheat Conda environment.

The public record's file list is the source of truth. Ambiguous selections fail
closed; never guess a remote filename or silently download the full record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .path import path_in_data

RECORD_ID = "23734614"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
KINDS = ("patterns", "temperature")
PATTERNS_ROOT = "heat_demand_profiles_patterns"
TEMPERATURE_ROOT = "air_temp"


def _request(url: str, token: str | None = None):
    """Make a request. Never put the access token in the URL or log it."""
    headers = {"User-Agent": "GBHeatModel-zenodo-inputs/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def get_manifest(record_id: str = RECORD_ID) -> list[dict[str, Any]]:
    token = os.environ.get("ZENODO_ACCESS_TOKEN")
    url = f"https://zenodo.org/api/records/{record_id}"
    try:
        with urllib.request.urlopen(_request(url, token), timeout=30) as res:
            data = json.load(res)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Zenodo metadata returned HTTP {exc.code}. The record may not be "
            "publicly published, or your account may lack access. "
            "Use the public record link once published, or set "
            "ZENODO_ACCESS_TOKEN locally if permitted."
        ) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot contact Zenodo: {exc.reason}") from None
    files = data.get("files", [])
    if isinstance(files, dict):
        files = list(files.values())
    if not isinstance(files, list) or not files:
        raise RuntimeError("Zenodo metadata does not contain a downloadable file list.")
    result = []
    for entry in files:
        key = entry.get("key") or entry.get("filename")
        links = entry.get("links") or {}
        url = links.get("self") or links.get("content") or links.get("download")
        if key and url:
            checksum = entry.get("checksum", "")
            if isinstance(checksum, str) and checksum.startswith("md5:"):
                checksum = checksum[4:]
            result.append({"key": key, "url": url, "size": entry.get("size"), "md5": checksum})
    if not result:
        raise RuntimeError("No Zenodo files with usable download URLs were found.")
    return result


def file_matches(file_key: str, kind: str, year: int) -> bool:
    """Conservative filename matching: explicit year and known type indicator."""
    name = Path(file_key).name.lower()
    year_match = re.search(r"(?<!\d)" + str(year) + r"(?!\d)", name) is not None
    if not year_match:
        return False
    if kind == "patterns":
        return bool(re.search(r"heat.{0,12}pattern|hd.{0,12}pattern|usage.{0,12}pattern", name))
    if kind == "temperature":
        return bool(re.search(r"air.{0,8}temp|daily.{0,8}temp|temperature", name))
    raise ValueError(f"Unsupported kind: {kind}")


def select_file(files: list[dict[str, Any]], kind: str, year: int,
                exact_key: str | None = None) -> dict[str, Any]:
    if exact_key:
        matches = [f for f in files if f["key"] == exact_key]
        if len(matches) != 1:
            raise ValueError(f"Filename {exact_key!r} not found in the Zenodo manifest.")
    else:
        matches = [f for f in files if file_matches(f["key"], kind, year)]
    if len(matches) != 1:
        available = "\n".join("  " + f["key"] for f in files)
        raise ValueError(
            f"Expected one {kind} file for {year}, found {len(matches)}. "
            "Inspect --list and explicitly select a filename using --file.\n"
            f"Available:\n{available}"
        )
    return matches[0]


def _safe_path(folder: Path, entry: str) -> Path:
    posix = PurePosixPath(entry.replace("\\", "/"))
    if posix.is_absolute() or any(part in ("..", "") for part in posix.parts) or ":" in posix.parts[0]:
        raise ValueError(f"Unsafe archive member: {entry!r}")
    return folder.joinpath(*posix.parts)


def download(file: dict[str, Any], destination: Path) -> Path:
    """Download atomically, verify size/MD5 when provided, do not overwrite."""
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("ZENODO_ACCESS_TOKEN")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".gbheat_", suffix=".part", dir=destination.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            digest = hashlib.md5()
            length = 0
            with urllib.request.urlopen(_request(file["url"], token), timeout=120) as res:
                while True:
                    chunk = res.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    digest.update(chunk)
                    length += len(chunk)
        if file.get("size") is not None and length != int(file["size"]):
            raise ValueError(f"Download size mismatch: expected {file['size']}, received {length}")
        expected = file.get("md5")
        if expected and re.fullmatch(r"[0-9a-fA-F]{32}", expected) and digest.hexdigest().lower() != expected.lower():
            raise ValueError("Checksum mismatch: Zenodo MD5 does not match downloaded file")
        temp_path.replace(destination)
        return destination
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def extract_zip(archive: Path, target: Path) -> None:
    """Extract a ZIP safely, preserving its original internal layout."""
    if target.exists():
        raise FileExistsError(f"Extract directory already exists: {target}")
    with zipfile.ZipFile(archive) as zf:
        entries = zf.infolist()
        paths = [_safe_path(target, item.filename) for item in entries]
        if not any(not item.is_dir() for item in entries):
            raise ValueError("ZIP contains no files")
        # Refuse symlinks to avoid writes outside the extraction directory.
        for info in entries:
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"Symlink member not supported: {info.filename}")
        target.mkdir(parents=True)
        for info, out in zip(entries, paths):
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(out, "xb") as dest:
                    import shutil
                    shutil.copyfileobj(source, dest)


# The published GBHeat record bundles all weather years in two ZIP files.
FULL_ARCHIVE_NAMES = {
    "patterns": "heat_demand_profiles_patterns.zip",
    "temperature": "air_temp.zip",
}


def select_archive(files: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """Require the exact published archive name; never guess a year-specific file."""
    key = FULL_ARCHIVE_NAMES[kind]
    matches = [item for item in files if item["key"] == key]
    if len(matches) != 1:
        raise ValueError(f"Expected one Zenodo archive named {key!r}; found {len(matches)}")
    return matches[0]


def _archive_members_for_year(zf: zipfile.ZipFile, kind: str, year: int):
    """Select only unambiguous, known GBHeat filenames, regardless of ZIP root."""
    selected = []
    for info in zf.infolist():
        # Validate *every* member, not just those selected.
        _safe_path(Path("/tmp/gbheat_validate"), info.filename)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f"ZIP symlinks are not supported: {info.filename}")
        if info.is_dir():
            continue
        name = PurePosixPath(info.filename.replace("\\", "/")).name
        if kind == "temperature":
            if name in (f"air_temp_{year}.csv", f"average_day_air_temp_{year}.csv"):
                selected.append((info, name))
        else:
            # Files expected by tech_half_hourly_profile.py: (Grid_ID)_YEAR.csv
            # Require an HD_heat_patterns_YEAR ancestor to avoid unrelated CSVs.
            parents = PurePosixPath(info.filename.replace("\\", "/")).parts[:-1]
            if (f"HD_heat_patterns_{year}" in parents
                    and re.fullmatch(r"\(.+\)_" + str(year) + r"\.csv", name)):
                selected.append((info, name))
    if kind == "temperature":
        names = {name for _, name in selected}
        if f"air_temp_{year}.csv" not in names:
            raise ValueError(f"Missing air_temp_{year}.csv inside the ZIP")
        # The published archive contents have not been inspected in this environment.
        # Install average_day_air_temp_YEAR.csv when it is present; never invent it.

    if kind == "patterns" and not selected:
        raise ValueError(f"No (Grid_ID)_{year}.csv files under HD_heat_patterns_{year}/")
    names = [name for _, name in selected]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate year-specific basenames in ZIP; refusing ambiguous extraction")
    return selected


def extract_weather_year(archive: Path, kind: str, year: int, data_root: Path) -> int:
    """Install selected year CSVs into GBHeat's unchanged input layout.

    Existing matching files are skipped. Different existing files cause an error.
    Return number of newly installed files (zero means already available).
    """
    if kind not in KINDS:
        raise ValueError(f"Unknown kind: {kind}")
    target = (data_root / PATTERNS_ROOT / f"HD_heat_patterns_{year}"
              if kind == "patterns" else data_root / TEMPERATURE_ROOT)
    with zipfile.ZipFile(archive) as zf:
        members = _archive_members_for_year(zf, kind, year)
        # Preflight every existing file before making ANY changes.
        pending = []
        for info, name in members:
            dest = target / name
            if dest.is_file():
                digest_zip = hashlib.sha256()
                digest_local = hashlib.sha256()
                with zf.open(info) as src:
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        digest_zip.update(chunk)
                with dest.open("rb") as src:
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        digest_local.update(chunk)
                if digest_zip.digest() != digest_local.digest():
                    raise FileExistsError(f"Existing file differs from Zenodo: {dest}")
            elif dest.exists():
                raise FileExistsError(f"Destination is not a regular file: {dest}")
            else:
                pending.append((info, dest))
        target.mkdir(parents=True, exist_ok=True)
        for info, dest in pending:
            with tempfile.NamedTemporaryFile(prefix=".gbheat_", suffix=".part", dir=target,
                                             delete=False) as tmp:
                temp_path = Path(tmp.name)
                try:
                    import shutil
                    with zf.open(info) as src:
                        shutil.copyfileobj(src, tmp, length=1024 * 1024)
                except BaseException:
                    temp_path.unlink(missing_ok=True)
                    raise
            temp_path.replace(dest)
    return len(pending)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", default=RECORD_ID, help="Zenodo record ID")
    parser.add_argument("--list", action="store_true", help="List actual Zenodo archive filenames")
    parser.add_argument("--year", type=int, help="Weather year (e.g. 2012)")
    parser.add_argument("--kind", choices=(*KINDS, "both"), default="both")
    parser.add_argument("--download", action="store_true", help="Download whole archive(s) if not cached")
    parser.add_argument("--extract", action="store_true", help="Extract only the chosen year's CSVs")
    parser.add_argument("--archive", help="Use a locally stored ZIP (requires --kind patterns or temperature)")
    parser.add_argument("--data-root", type=Path, default=None,
                        help="Alternative data directory for safe testing; default is GBHeatModel/data")
    args = parser.parse_args(argv)
    if args.archive and args.kind == "both":
        parser.error("--archive requires --kind patterns or --kind temperature")
    if not args.list and (args.year is None or not 2010 <= args.year <= 2024):
        parser.error("Specify a weather year in 2010..2024, or use --list")
    if args.extract and not args.download and not args.archive:
        # Cached archives are supported without --download.
        pass
    files = get_manifest(args.record) if not args.archive else []
    if args.list:
        for f in files:
            print(f"{f['key']} ({f.get('size', 'unknown')} bytes)")
        return 0
    data_root = args.data_root.expanduser().resolve() if args.data_root else path_in_data()
    kinds = KINDS if args.kind == "both" else (args.kind,)
    for kind in kinds:
        entry = None if args.archive else select_archive(files, kind)
        archive = Path(args.archive) if args.archive else (data_root /
            (PATTERNS_ROOT if kind == "patterns" else TEMPERATURE_ROOT) /
            "_zenodo_downloads" / FULL_ARCHIVE_NAMES[kind])
        if entry:
            print(f"{kind}: {entry['key']} ({entry.get('size')} bytes) -> {archive}")
        else:
            print(f"{kind}: using local ZIP {archive}")
        if not archive.is_file():
            if not args.download or args.archive:
                print("Not cached. Add --download to fetch the FULL archive." if not args.archive
                      else f"Local ZIP does not exist: {archive}")
                if args.extract:
                    raise FileNotFoundError(str(archive))
                continue
            print("Downloading full archive; Zenodo contains no separate yearly files.")
            download(entry, archive)
        else:
            print("Using cached archive (not downloading again).")
        if args.extract:
            n = extract_weather_year(archive, kind, args.year, data_root)
            print(f"Installed {n} new {kind} CSV file(s) for {args.year} into {data_root}.")
    if not args.download and not args.extract:
        print("Preview only. Add --download --extract (or --extract for cached ZIPs).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, FileExistsError, FileNotFoundError,
            zipfile.BadZipFile, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
