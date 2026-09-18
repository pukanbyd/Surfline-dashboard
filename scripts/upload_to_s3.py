import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data"))


def upload_latest_csv(bucket_name: str = S3_BUCKET, directory: Path = OUTPUT_DIR) -> str | None:
    if not bucket_name:
        files = sorted(directory.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"No CSV files found in {directory}")
        latest_file = files[-1]
        print(f"S3_BUCKET_NAME not set. Skipping upload and keeping local file: {latest_file}")
        return None

    files = sorted(directory.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {directory}")

    latest_file = files[-1]
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = latest_file.name
    s3.upload_file(str(latest_file), bucket_name, key)
    print(f"Uploaded {latest_file.name} to s3://{bucket_name}/{key}")
    return key


if __name__ == "__main__":
    upload_latest_csv()
