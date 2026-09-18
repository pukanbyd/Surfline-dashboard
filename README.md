# Surfline Dashboard

A local ETL project that fetches live wave forecast data from Surfline, stores the latest CSV locally, and renders a small Dash dashboard.

## Architecture

- Surfline API -> raw forecast JSON
- fetch_surfline.py -> CSV export
- upload_to_s3.py -> upload latest CSV to S3 when credentials are available
- load_latest_s3_to_postgres.py -> load data into Postgres when available, otherwise SQLite fallback
- dashboard/app.py -> Plotly Dash dashboard
- dags/surfline_pipeline.py -> Airflow DAG for orchestration

## Current verified status

The data pipeline is working end-to-end in local development mode:

- Surfline API request succeeds with HTTP 200
- CSV files are generated in the data folder
- dashboard reads the latest CSV and renders real wave-height data
- Postgres stores the forecast rows and is used by the dashboard
- Airflow DAG runs successfully
- SQLite fallback is available when Postgres is unavailable

## Project structure

- scripts/fetch_surfline.py
- scripts/upload_to_s3.py
- scripts/load_latest_s3_to_postgres.py
- dashboard/app.py
- dags/surfline_pipeline.py
- data/
- docker-compose.yml

## Local run

1. Activate the virtual environment
2. Run the fetch step:
   python scripts/fetch_surfline.py
3. Run the dashboard:
   python dashboard/app.py
4. Open http://localhost:8050

## Optional warehouse path

This project is designed for:

- S3 upload for file storage
- Postgres as the warehouse
- Airflow for scheduled ETL

S3 is optional for this local version. When AWS credentials are not configured, the pipeline uses the latest CSV from the local `data/` directory before loading it into Postgres.

## Important note

The Surfline API requires the correct endpoint format:

https://services.surfline.com/kbyg/spots/forecasts/wave?spotId=YOUR_SPOT_ID&days=1&intervalHours=1

The older path-based pattern with a URL slug instead of a `spotId` query param returns errors.

## Reflection

### 1. What did you learn from this project?

I learned how to build an end-to-end data pipeline that connects an external API to a database and a dashboard. I practiced working with nested JSON, normalizing forecast data into CSV rows, loading data into PostgreSQL, and orchestrating the workflow with Airflow. I also learned that API contracts, Docker networking, database ports, and environment variables can be just as important as the Python code itself.

### 2. How would you improve it?

I would improve the project by adding stronger data validation, deduplication, and monitoring for failed or stale forecasts. I would also replace the temporary local CSV fallback with a more robust storage layer, use a production metadata database for Airflow, add automated tests, and improve the dashboard with filters for surf spot, forecast time, wave height, swell period, and probability.

### 3. If you had to do it all over again, what would you do differently?

I would validate the Surfline API endpoint and response structure first, before setting up the rest of the infrastructure. I would decide early whether S3 was required or optional, document the Docker ports and service boundaries from the beginning, and design the database schema before writing the ingestion code. This would reduce rework and make it easier to test each stage independently.

## Known environment notes

The Surfline API may occasionally return a 403 or 404 from its edge protection. In that case, the pipeline uses the latest local CSV when `ALLOW_LOCAL_FALLBACK=true`, so the dashboard and Postgres ingestion can continue during local development.
