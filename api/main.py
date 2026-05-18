"""
FastAPI app — serves JSON API + built Vite frontend.
Deploy: Docker, Railway, Render, Fly.io, any VPS with `docker compose up`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.database import get_conn, init_db, sync_from_files
from api.schemas import HealthResponse, RetrainResponse
from src.config import DATA_PROCESSED, MODELS_DIR, ROOT

WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title="Hantavirus Spread ML", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    sync_from_files()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@app.get("/api/viruses")
def list_viruses() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT virus_slug, virus_name, family, is_hantavirus,
                  COUNT(*) AS records, SUM(cases) AS total_cases
           FROM outbreaks GROUP BY virus_slug ORDER BY virus_slug"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/outbreaks")
def outbreaks(
    virus: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    hantavirus_only: bool = False,
) -> list[dict]:
    conn = get_conn()
    q = "SELECT * FROM outbreaks WHERE 1=1"
    params: list = []
    if virus:
        q += " AND virus_slug = ?"
        params.append(virus)
    if year_from:
        q += " AND year >= ?"
        params.append(year_from)
    if year_to:
        q += " AND year <= ?"
        params.append(year_to)
    if hantavirus_only:
        q += " AND is_hantavirus = 1"
    q += " ORDER BY year, virus_slug, geo_id"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/outbreaks/series/{virus_slug}")
def outbreak_series(virus_slug: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT year, geo_id, geo_name, SUM(cases) AS cases
           FROM outbreaks WHERE virus_slug = ?
           GROUP BY year, geo_id ORDER BY year""",
        (virus_slug,),
    ).fetchall()
    conn.close()
    if not rows:
        raise HTTPException(404, "virus not found")
    return [dict(r) for r in rows]


@app.get("/api/forecasts")
def forecasts(virus: str = Query("sin_nombre_us")) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM forecasts WHERE virus_slug = ?
           ORDER BY predicted_cases DESC""",
        (virus,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/metrics")
def metrics() -> dict:
    path = MODELS_DIR / "metrics.json"
    if path.exists():
        return json.loads(path.read_text())
    conn = get_conn()
    row = conn.execute("SELECT payload FROM model_metrics ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return json.loads(row["payload"])
    raise HTTPException(404, "model not trained yet")


@app.get("/api/climate/{geo_id}")
def climate_series(geo_id: str) -> list[dict]:
    import pandas as pd

    panel_path = DATA_PROCESSED / "multi_virus_panel.parquet"
    csv_path = DATA_PROCESSED / "multi_virus_panel.csv"
    if panel_path.exists():
        panel = pd.read_parquet(panel_path)
    elif csv_path.exists():
        panel = pd.read_csv(csv_path)
    else:
        raise HTTPException(404, "panel missing — run scripts/build_offline_panel.py")
    sub = panel[panel["geo_id"] == geo_id][
        ["year", "precip_annual_mm", "temp_annual_c", "precip_winter_mm"]
    ].drop_duplicates()
    return sub.to_dict(orient="records")


@app.post("/api/retrain", response_model=RetrainResponse)
def retrain() -> RetrainResponse:
    """Run full pipeline (slow; needs network for climate cache miss)."""
    script = ROOT / "scripts" / "run_pipeline.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise HTTPException(500, proc.stderr[-2000:] or "pipeline failed")
    sync_from_files()
    return RetrainResponse(ok=True, metrics=json.loads((MODELS_DIR / "metrics.json").read_text()))


# static frontend
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(404)
        index = WEB_DIST / "index.html"
        if full_path and (WEB_DIST / full_path).is_file():
            return FileResponse(WEB_DIST / full_path)
        if index.exists():
            return FileResponse(index)
        raise HTTPException(404, "frontend not built — run npm run build in web/")

else:

    @app.get("/")
    def root():
        return {
            "message": "API running. Build frontend: cd web && npm install && npm run build",
            "docs": "/docs",
        }
