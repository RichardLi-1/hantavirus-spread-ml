"""SQLite persistence for API reads (synced from parquet on startup / retrain)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATA_PROCESSED, MODELS_DIR, ROOT

DB_PATH = ROOT / "data" / "app.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS outbreaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            virus_slug TEXT,
            virus_name TEXT,
            family TEXT,
            geo_id TEXT,
            geo_name TEXT,
            country TEXT,
            cases INTEGER,
            is_hantavirus INTEGER
        );
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            virus_slug TEXT,
            geo_id TEXT,
            predicted_cases REAL,
            high_risk_prob REAL,
            risk_tier TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS model_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # migrate older DBs created before family column existed
    cols = {r[1] for r in conn.execute("PRAGMA table_info(outbreaks)").fetchall()}
    if cols and "family" not in cols:
        conn.execute("ALTER TABLE outbreaks ADD COLUMN family TEXT")
    conn.commit()
    conn.close()


def sync_from_files() -> None:
    init_db()
    panel_path = DATA_PROCESSED / "multi_virus_panel.parquet"
    csv_path = DATA_PROCESSED / "multi_virus_panel.csv"
    if panel_path.exists():
        panel = pd.read_parquet(panel_path)
    elif csv_path.exists():
        panel = pd.read_csv(csv_path)
    else:
        return
    conn = get_conn()
    conn.execute("DELETE FROM outbreaks")
    cols = ["year", "virus_slug", "virus_name", "family", "geo_id", "geo_name", "country", "cases", "is_hantavirus"]
    if "family" not in panel.columns:
        panel["family"] = ""
    # to_records() leaves int64 as numpy scalars; sqlite3 stores those as BLOBs.
    rows = panel[cols].values.tolist()
    conn.executemany(
        """INSERT INTO outbreaks
           (year, virus_slug, virus_name, family, geo_id, geo_name, country, cases, is_hantavirus)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        list(rows),
    )

    metrics_path = MODELS_DIR / "metrics.json"
    if metrics_path.exists():
        conn.execute("DELETE FROM model_metrics")
        conn.execute(
            "INSERT INTO model_metrics (payload) VALUES (?)",
            (metrics_path.read_text(),),
        )

    for fc_file in DATA_PROCESSED.glob("forecast_*_summary.json"):
        continue
    for fc_file in sorted(DATA_PROCESSED.glob("forecast_*.csv")):
        if "summary" in fc_file.name:
            continue
        fc = pd.read_csv(fc_file)
        slug = (
            fc["virus_slug"].iloc[0]
            if "virus_slug" in fc.columns
            else fc_file.stem.replace("forecast_", "").rsplit("_", 1)[0]
        )
        year = int(fc["year"].iloc[0])
        conn.execute(
            "DELETE FROM forecasts WHERE virus_slug = ? AND year = ?", (slug, year)
        )
        for _, r in fc.iterrows():
            conn.execute(
                """INSERT INTO forecasts
                   (year, virus_slug, geo_id, predicted_cases, high_risk_prob, risk_tier)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    year,
                    slug,
                    r.get("geo_id", r.get("state")),
                    float(r["predicted_cases"]),
                    float(r["high_risk_prob"]),
                    str(r.get("risk_tier", "")),
                ),
            )
    conn.commit()
    conn.close()
