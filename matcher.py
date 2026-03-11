import json
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from math import radians, cos, sin, asin, sqrt

DATA_DIR = "data"
MAIN_OUTFILE = f"{DATA_DIR}/beaches_with_closest_tide_station.json"
DAYS_AHEAD = 90

BEACHES_URL = "https://raw.githubusercontent.com/conor3618/epa-ie-water-quality-python/main/beaches.json"

# Haversine formula to calculate distance between two lat/lon points
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

# Fetch JSON from a URL
def fetch_json_url(url):
    req = Request(url, headers={"User-Agent": "beach-tide-matcher/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

# Fetch tide stations from ERDDAP
def fetch_tide_stations():
    today = datetime.now().date()
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    url = (
        "https://erddap.marine.ie/erddap/tabledap/IMI_TidePrediction_HighLow.json"
        f"?stationID%2Clongitude%2Clatitude"
        f"&time%3E={start}T00%3A00%3A00Z"
        f"&time%3C={end}T00%3A00%3A00Z"
        "&distinct()"
    )
    payload = fetch_json_url(url)
    table = payload["table"]
    colnames = table["columnNames"]
    rows = table["rows"]
    idx = {name: i for i, name in enumerate(colnames)}
    stations = {}
    for row in rows:
        station_id = row[idx["stationID"]]
        if station_id not in stations:
            stations[station_id] = {
                "stationID": station_id,
                "longitude": float(row[idx["longitude"]]),
                "latitude": float(row[idx["latitude"]]),
            }
    return list(stations.values())

# Main logic
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    beaches = fetch_json_url(BEACHES_URL)
    tide_stations = fetch_tide_stations()
    output = {}
    for beach_name, beach_info in beaches.items():
        beach_lat = beach_info["latitude"]
        beach_lon = beach_info["longitude"]
        min_dist = float("inf")
        closest_station = None
        for station in tide_stations:
            dist = haversine(beach_lat, beach_lon, station["latitude"], station["longitude"])
            if dist < min_dist:
                min_dist = dist
                closest_station = station["stationID"]
        output[beach_name] = {
            **beach_info,
            "closest_tide_station": closest_station
        }
    with open(MAIN_OUTFILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Wrote {MAIN_OUTFILE} ({len(output)} beaches)")

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise
