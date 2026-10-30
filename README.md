## Reflection

### 1. What did you learn from this project?

I learned how to build an end-to-end data pipeline that connects an external API to a database and a dashboard. I practiced working with nested JSON, normalizing forecast data into CSV rows, loading data into PostgreSQL, and orchestrating the workflow with Airflow. I also learned that API contracts, Docker networking, database ports, and environment variables can be just as important as the Python code itself.

### 2. How would you improve it?

I would improve the project by adding stronger data validation, deduplication, and monitoring for failed or stale forecasts. I would also replace the temporary local CSV fallback with a more robust storage layer, use a production metadata database for Airflow, add automated tests, and improve the dashboard with filters for surf spot, forecast time, wave height, swell period, and probability.

### 3. If you had to do it all over again, what would you do differently?

I would validate the Surfline API endpoint and response structure first, before setting up the rest of the infrastructure. I would decide early whether S3 was required or optional, document the Docker ports and service boundaries from the beginning, and design the database schema before writing the ingestion code. This would reduce rework and make it easier to test each stage independently.
