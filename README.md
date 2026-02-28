# taoide-data

Automated tide predictions for Irish coastal stations, updated daily from the [Irish Marine Institute](https://www.marine.ie/) via their ERDDAP API.

## Data

The `data/` directory is updated every morning at 06:00 UTC with predictions for the next 6 days.

| File | Description |
|------|-------------|
| `data/tide_sites_latest.json` | All stations combined |
| `data/<stationID>_tides.json` | Per-station: next 8 upcoming highs & lows |

### Example station entry

```json
{
  "stationID": "MACE_HEAD",
  "longitude": -9.9,
  "latitude": 53.33,
  "next_8_high_tides_utc": ["2025-06-01T06:42", "2025-06-01T19:01", "..."],
  "next_8_low_tides_utc":  ["2025-06-01T13:05", "2025-06-01T23:48", "..."],
  "generated_at_utc": "2025-06-01T06:00:00Z",
  "source_url": "https://erddap.marine.ie/..."
}
```

All times are UTC.

## Running locally

```bash
python fetch_tides.py
```

## Source

- **Provider:** [Irish Marine Institute](https://www.marine.ie/)
- **Dataset:** `IMI_TidePrediction_HighLow` via [ERDDAP](https://erddap.marine.ie/erddap/tabledap/IMI_TidePrediction_HighLow.html)

> **Disclaimer:** The Irish Marine Institute does not endorse this project and makes no guarantee as to the accuracy or completeness of the data. Use at your own risk.

## License

MIT
