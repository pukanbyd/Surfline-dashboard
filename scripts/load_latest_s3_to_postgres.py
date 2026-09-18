import os
import sqlite3
from pathlib import Path

import boto3
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data"))

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "surf_db")
DB_USER = os.getenv("POSTGRES_USER", "surf_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "surf_password")


def get_latest_local_csv() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTPUT_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {OUTPUT_DIR}")
    return files[-1]


def get_latest_s3_key(bucket_name: str = S3_BUCKET) -> str:
    if not bucket_name:
        return get_latest_local_csv().name

    s3 = boto3.client("s3", region_name=AWS_REGION)
    response = s3.list_objects_v2(Bucket=bucket_name)
    contents = response.get("Contents", [])
    if not contents:
        raise FileNotFoundError(f"No files found in bucket {bucket_name}")
    latest = sorted(contents, key=lambda x: x["LastModified"])[-1]
    return latest["Key"]


def download_latest_file(bucket_name: str = S3_BUCKET, destination_dir: Path = OUTPUT_DIR) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    if not bucket_name:
        local_path = get_latest_local_csv()
        print(f"Using local CSV fallback: {local_path}")
        return local_path

    key = get_latest_s3_key(bucket_name)
    local_path = destination_dir / Path(key).name

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.download_file(bucket_name, key, str(local_path))
    return local_path


def insert_into_sqlite(df: pd.DataFrame) -> None:
    db_path = OUTPUT_DIR / "surfline.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS surfline_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            spot_id TEXT,
            wave_height_min REAL,
            wave_height_max REAL,
            swell_period REAL,
            swell_height REAL,
            swell_direction REAL,
            power REAL,
            wave_probability REAL,
            raw TEXT,
            source TEXT
        )
        """
    )
    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO surfline_raw (
                timestamp, spot_id, wave_height_min, wave_height_max,
                swell_period, swell_height, swell_direction, power,
                wave_probability, raw, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("timestamp"),
                row.get("spot_id"),
                row.get("wave_height_min"),
                row.get("wave_height_max"),
                row.get("swell_period"),
                row.get("swell_height"),
                row.get("swell_direction"),
                row.get("power"),
                row.get("wave_probability"),
                row.get("raw"),
                row.get("source"),
            ),
        )
    conn.commit()
    conn.close()
    print(f"Inserted {len(df)} rows into SQLite at {db_path}")


def load_csv_to_postgres(csv_path: Path) -> None:
    df = pd.read_csv(csv_path)

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS surfline_raw (
                id SERIAL PRIMARY KEY,
                timestamp BIGINT,
                spot_id TEXT,
                wave_height_min DOUBLE PRECISION,
                wave_height_max DOUBLE PRECISION,
                swell_period DOUBLE PRECISION,
                swell_height DOUBLE PRECISION,
                swell_direction DOUBLE PRECISION,
                power DOUBLE PRECISION,
                wave_probability DOUBLE PRECISION,
                raw TEXT,
                source TEXT,
                ingested_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

        for _, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO surfline_raw (
                    timestamp, spot_id, wave_height_min, wave_height_max,
                    swell_period, swell_height, swell_direction, power,
                    wave_probability, raw, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row.get("timestamp"),
                    row.get("spot_id"),
                    row.get("wave_height_min"),
                    row.get("wave_height_max"),
                    row.get("swell_period"),
                    row.get("swell_height"),
                    row.get("swell_direction"),
                    row.get("power"),
                    row.get("wave_probability"),
                    row.get("raw"),
                    row.get("source"),
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()
        print(f"Inserted {len(df)} rows from {csv_path.name} into Postgres")
        return
    except Exception as exc:
        print(f"Postgres unavailable: {exc}")
        print("Falling back to SQLite for local development.")
        insert_into_sqlite(df)


def main() -> None:
    csv_path = download_latest_file()
    load_csv_to_postgres(csv_path)


if __name__ == "__main__":
    main()
