import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SURFLINE_API_URL = os.getenv("SURFLINE_API_URL")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data"))


def fetch_surfline_data() -> dict:
    if not SURFLINE_API_URL:
        raise ValueError(
            "SURFLINE_API_URL is not set. Example: "
            "https://services.surfline.com/kbyg/spots/forecasts/wave?spotId=YOUR_SPOT_ID&days=1&intervalHours=1"
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(SURFLINE_API_URL, timeout=30, headers=headers)
    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(response.text[:1000])
        if os.getenv("ALLOW_LOCAL_FALLBACK", "false").lower() == "true":
            latest_path = OUTPUT_DIR / "surfline_latest.csv"
            if latest_path.exists():
                print(f"Using existing local CSV because Surfline returned HTTP {response.status_code}: {latest_path}")
                return {"_local_csv": str(latest_path)}
        raise RuntimeError(
            "Surfline API request failed. This usually means the spotId is invalid or the endpoint is wrong. "
            "Check SURFLINE_API_URL in .env."
        )

    payload = response.json()
    print("JSON keys:", list(payload.keys())[:20])
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:2000])
    return payload


def extract_forecast_rows(payload: dict) -> list[dict]:
    parsed_url = urlparse(SURFLINE_API_URL or "")
    query_params = parse_qs(parsed_url.query)
    spot_id = (query_params.get("spotId") or [None])[0]

    wave_entries = payload.get("data", {}).get("wave") or []
    if wave_entries:
        rows = []
        for entry in wave_entries:
            surf = entry.get("surf") or {}
            swells = entry.get("swells") or []
            primary_swell = next((s for s in swells if (s.get("period") or 0) > 0), {})

            rows.append({
                "timestamp": entry.get("timestamp"),
                "spot_id": spot_id,
                "wave_height_min": surf.get("min") or surf.get("raw", {}).get("min"),
                "wave_height_max": surf.get("max") or surf.get("raw", {}).get("max"),
                "swell_period": primary_swell.get("period"),
                "swell_height": primary_swell.get("height"),
                "swell_direction": primary_swell.get("direction"),
                "power": entry.get("power"),
                "wave_probability": entry.get("probability"),
                "raw": json.dumps(entry, ensure_ascii=False),
                "source": "surfline",
            })
        return rows

    if isinstance(payload, list):
        return [{
            "timestamp": datetime.utcnow().isoformat(),
            "spot_id": spot_id,
            "raw": json.dumps(item, ensure_ascii=False),
            "source": "surfline",
        } for item in payload]

    return [{
        "timestamp": datetime.utcnow().isoformat(),
        "spot_id": spot_id,
        "raw": json.dumps(payload, ensure_ascii=False),
        "source": "surfline",
    }]


def normalize_rows(rows: list[dict]) -> pd.DataFrame:
    columns = [
        "timestamp",
        "spot_id",
        "wave_height_min",
        "wave_height_max",
        "swell_period",
        "swell_height",
        "swell_direction",
        "power",
        "wave_probability",
        "raw",
        "source",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[columns]


def save_csv(df: pd.DataFrame, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"surfline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path = output_dir / filename
    latest_path = output_dir / "surfline_latest.csv"
    df.to_csv(output_path, index=False)
    df.to_csv(latest_path, index=False)
    return output_path


def main() -> None:
    payload = fetch_surfline_data()
    if "_local_csv" in payload:
        print(f"Fetch fallback complete: {payload['_local_csv']}")
        return
    rows = extract_forecast_rows(payload)
    df = normalize_rows(rows)
    output_path = save_csv(df)
    print(f"Saved CSV: {output_path}")
    print(df.head())


if __name__ == "__main__":
    main()
