"""
fetch_tides.py

Pulls high/low tide predictions from the Irish Marine Institute's ERDDAP API
and writes them to JSON — one aggregated file and one per station.

Output files (written to data/):
    tide_sites_latest.json      — all stations combined
    <stationID>_tides.json      — per-station, next 8 highs & lows (UTC)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = "data"
MAIN_OUTFILE = f"{DATA_DIR}/tide_sites_latest.json"
NUM_TIDES = None     # unlimited upcoming highs/lows per station
DAYS_AHEAD = 90      # forecast window sent to ERDDAP (3 months)


# ---------------------------------------------------------------------------
# ERDDAP helpers
# ---------------------------------------------------------------------------

def build_erddap_url(days_ahead: int = DAYS_AHEAD) -> str:
    """Return the ERDDAP tabledap URL for the next `days_ahead` days of predictions."""
    today = datetime.now().date()
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return (
        "https://erddap.marine.ie/erddap/tabledap/IMI_TidePrediction_HighLow.json"
        f"?stationID%2Ctime%2Clongitude%2Clatitude%2Ctide_time_category"
        f"&time%3E={start}T00%3A00%3A00Z"
        f"&time%3C={end}T00%3A00%3A00Z"
        "&distinct()"
    )


def fetch_json(url: str) -> dict:
    """Fetch a URL and return the parsed JSON body."""
    req = Request(url, headers={"User-Agent": "tide-sites-script/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_utc_z(ts: str) -> datetime:
    """Parse an ISO-8601 Zulu timestamp (e.g. '2025-06-01T06:42:00Z') to UTC datetime."""
    if not ts.endswith("Z"):
        raise ValueError(f"Expected Zulu timestamp ending with 'Z', got: {ts!r}")
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_tide_time(dt: datetime) -> str:
    """Format a datetime as 'YYYY-MM-DDTHH:MM' (minute precision, no seconds)."""
    return dt.strftime("%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_stations(rows: list, idx: dict, now_utc: datetime) -> list[dict]:
    """
    Walk the ERDDAP rows and build a per-station dict containing the next
    NUM_TIDES upcoming high and low tide times.

    Rows in the past (relative to `now_utc`) are skipped so the output
    always reflects future predictions only.
    """
    stations: dict[str, dict] = {}

    for row in rows:
        station_id = row[idx["stationID"]]
        t = parse_utc_z(row[idx["time"]])

        # Skip tides that have already passed
        if t <= now_utc:
            continue

        cat = row[idx["tide_time_category"]].upper()  # "HIGH" or "LOW"
        ts_str = format_tide_time(t)

        # Initialise station entry on first encounter
        st = stations.setdefault(
            station_id,
            {
                "stationID": station_id,
                "longitude": float(row[idx["longitude"]]),
                "latitude": float(row[idx["latitude"]]),
                "high_tides_utc": [],
                "low_tides_utc": [],
            },
        )

        # Append to the appropriate list, keeping it sorted and unlimited
        bucket: List[str] = (
            st["high_tides_utc"] if cat == "HIGH" else st["low_tides_utc"]
        )
        if ts_str not in bucket:
            bucket.append(ts_str)
            bucket.sort()

    return sorted(stations.values(), key=lambda d: d["stationID"])


def write_json(path: str, data: dict) -> None:
    """Write `data` as pretty-printed JSON to `path`."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    now_utc = datetime.now(timezone.utc)
    url = build_erddap_url()

    print(f"Fetching: {url}")
    payload = fetch_json(url)

    # ERDDAP returns a 'table' object with parallel columnNames / rows arrays
    table = payload["table"]
    colnames = table["columnNames"]
    rows = table["rows"]

    # Build a column-name → index map and validate required columns exist
    idx = {name: i for i, name in enumerate(colnames)}
    required = ["stationID", "time", "longitude", "latitude", "tide_time_category"]
    missing = [c for c in required if c not in idx]
    if missing:
        raise KeyError(f"Missing expected columns: {missing} (got {colnames})")

    os.makedirs(DATA_DIR, exist_ok=True)

    stations = collect_stations(rows, idx, now_utc)

    # Shared metadata written into every output file
    meta = {
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_url": url,
    }

    # Write the aggregated file
    write_json(MAIN_OUTFILE, {**meta, "count": len(stations), "stations": stations})

    # Write one file per station
    for st in stations:
        write_json(f"{DATA_DIR}/{st['stationID']}_tides.json", {**st, **meta})

    print(f"Wrote {MAIN_OUTFILE} ({len(stations)} stations)")
    print(f"Wrote {len(stations)} individual files to {DATA_DIR}/")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise
