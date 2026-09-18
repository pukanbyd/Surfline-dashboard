import os
from pathlib import Path

import pandas as pd
import psycopg2
import plotly.express as px
from dash import Dash, dcc, html
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def load_data() -> pd.DataFrame:
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=os.getenv("POSTGRES_PORT", "5433"),
            dbname=os.getenv("POSTGRES_DB", "surf_db"),
            user=os.getenv("POSTGRES_USER", "surf_user"),
            password=os.getenv("POSTGRES_PASSWORD", "surf_password"),
            connect_timeout=3,
        )
        df = pd.read_sql_query(
            """
            SELECT timestamp, wave_height_max, swell_period, wave_probability
            FROM surfline_raw
            ORDER BY timestamp
            """,
            conn,
        )
        conn.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
            return df.rename(columns={"wave_height_max": "wave_height"}).dropna(subset=["timestamp"])
    except (psycopg2.Error, OSError):
        pass

    candidates = [
        os.path.join("data", "surfline_latest.csv"),
        os.path.join("data", "surfline_20260831_105932.csv"),
    ]

    for path in candidates:
        if os.path.exists(path):
            df = pd.read_csv(path)
            if {"timestamp", "wave_height_max"}.issubset(df.columns):
                df = df.copy()
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
                df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
                return df[["timestamp", "wave_height_max", "swell_period", "wave_probability"]].rename(
                    columns={"wave_height_max": "wave_height"}
                )
            if {"timestamp", "wave_height"}.issubset(df.columns):
                df = df.copy()
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                return df[["timestamp", "wave_height", "swell_period"]].dropna(subset=["timestamp"])

    return pd.DataFrame({"timestamp": [], "wave_height": [], "swell_period": []})


def create_dashboard() -> Dash:
    df = load_data()
    app = Dash(__name__)

    fig = px.line(
        df,
        x="timestamp",
        y="wave_height",
        title="Wave Height Over Time",
        labels={"timestamp": "Time", "wave_height": "Wave Height (m)"},
    )

    app.layout = html.Div([
        html.H1("Surfline Dashboard"),
        dcc.Graph(figure=fig),
    ])
    return app


if __name__ == "__main__":
    app = create_dashboard()
    app.run(debug=True, host="0.0.0.0", port=8050)
