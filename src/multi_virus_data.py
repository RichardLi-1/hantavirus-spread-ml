"""
Merge historical case series for multiple rodent-borne / zoonotic viruses,
attach climate from Open-Meteo, and build a unified training panel.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .config import DATA_PROCESSED, DATA_RAW, END_YEAR, START_YEAR
from .data_collection import OPEN_METEO, _allocate_state_cases, build_climate_panel

HANTAVIRUS_SLUGS = {
    "sin_nombre_us",
    "puuv_fi",
    "puuv_de",
    "puuv_se",
    "andes_cl",
    "andes_ar",
    "seoul_kr",
    "dobrava_balk",
}


def load_multi_virus_raw() -> pd.DataFrame:
    return pd.read_csv(DATA_RAW / "multi_virus_historical.csv")


def _fetch_climate_geo(geo_id: str, lat: float, lon: float, cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"climate_{geo_id}.parquet"
    if cache_file.exists():
        return pd.read_parquet(cache_file)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "monthly": "precipitation_sum,temperature_2m_mean",
        "timezone": "auto",
    }
    resp = requests.get(OPEN_METEO, params=params, timeout=60)
    resp.raise_for_status()
    monthly = resp.json()["monthly"]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(monthly["time"]),
            "precip_mm": monthly["precipitation_sum"],
            "temp_c": monthly["temperature_2m_mean"],
        }
    )
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["geo_id"] = geo_id
    df.to_parquet(cache_file, index=False)
    time.sleep(0.25)
    return df


def _climate_yearly(climate: pd.DataFrame) -> pd.DataFrame:
    climate = climate.copy()
    climate["season"] = climate["month"].map(
        lambda m: "winter" if m in (12, 1, 2) else ("summer" if m in (6, 7, 8) else "other")
    )
    season = climate.groupby(["geo_id", "year", "season"])["precip_mm"].sum().unstack(fill_value=0)
    season.columns = [f"precip_{c}_mm" for c in season.columns]
    yearly = climate.groupby(["geo_id", "year"]).agg(
        precip_annual_mm=("precip_mm", "sum"),
        temp_annual_c=("temp_c", "mean"),
    )
    return yearly.join(season, how="left").reset_index()


def build_us_state_panel() -> pd.DataFrame:
    """US state-year panel (Sin Nombre) — same logic as data_collection."""
    national = pd.read_csv(DATA_RAW / "national_cases_by_year.csv")
    cases = _allocate_state_cases(national)
    cases = cases.rename(columns={"state": "geo_id"})
    cases["geo_name"] = cases["geo_id"]
    cases["geo_type"] = "state"
    cases["virus_slug"] = "sin_nombre_us"
    cases["virus_name"] = "Sin Nombre (HPS)"
    cases["family"] = "Hantaviridae"
    cases["is_hantavirus"] = 1
    cases["country"] = "USA"
    return cases


def build_unified_panel(refetch_climate: bool = False) -> pd.DataFrame:
    raw = load_multi_virus_raw()
    raw["is_hantavirus"] = raw["virus_slug"].isin(HANTAVIRUS_SLUGS).astype(int)

    us_states = build_us_state_panel()
    # drop national US row from multi-virus CSV to avoid duplicate
    intl = raw[~((raw["virus_slug"] == "sin_nombre_us") & (raw["geo_type"] == "national"))].copy()
    intl = intl.rename(columns={"source": "source_note"})

    # align columns
    base_cols = [
        "virus_slug", "virus_name", "family", "geo_id", "geo_name", "geo_type",
        "country", "year", "cases", "is_hantavirus",
    ]
    intl_panel = intl[base_cols]

    us_panel = us_states[
        base_cols + ["region"]
    ]

    panel = pd.concat([us_panel, intl_panel], ignore_index=True)

    # geo coordinates for climate fetch
    geo_coords = (
        raw.drop_duplicates("geo_id")[["geo_id", "lat", "lon"]]
        .set_index("geo_id")
    )
    from .config import STATE_COORDS

    for st, (lat, lon) in STATE_COORDS.items():
        if st not in geo_coords.index:
            geo_coords.loc[st] = [lat, lon]
    geo_coords.loc["US_national"] = [39.8, -98.5]

    cache_dir = DATA_RAW / "climate_cache_multi"
    if refetch_climate and cache_dir.exists():
        for f in cache_dir.glob("*.parquet"):
            f.unlink()

    geos_needed = panel["geo_id"].unique()
    climate_frames = []
    for gid in geos_needed:
        if gid in geo_coords.index:
            lat, lon = float(geo_coords.loc[gid, "lat"]), float(geo_coords.loc[gid, "lon"])
        elif gid in STATE_COORDS:
            lat, lon = STATE_COORDS[gid]
        else:
            continue
        climate_frames.append(_fetch_climate_geo(gid, lat, lon, cache_dir))

    climate = pd.concat(climate_frames, ignore_index=True)
    yearly = _climate_yearly(climate)
    panel = panel.merge(yearly, on=["geo_id", "year"], how="left")

    panel["high_risk_year"] = (
        panel["cases"] >= panel.groupby(["virus_slug", "geo_id"])["cases"].transform("mean")
    ).astype(int)
    panel["log_cases"] = np.log1p(panel["cases"])

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(DATA_PROCESSED / "multi_virus_panel.parquet", index=False)
  # keep US-only panel for backward compat
    us_only = panel[panel["virus_slug"] == "sin_nombre_us"].copy()
    us_only = us_only.rename(columns={"geo_id": "state"})
    us_only.to_parquet(DATA_PROCESSED / "state_year_panel.parquet", index=False)
    us_only[["year", "state", "cases", "region"]].to_csv(
        DATA_PROCESSED / "cases_state_year.csv", index=False
    )

    meta = {
        "viruses": sorted(panel["virus_slug"].unique().tolist()),
        "rows": len(panel),
        "hantavirus_rows": int(panel["is_hantavirus"].sum()),
        "years": [int(panel["year"].min()), int(panel["year"].max())],
        "training_note": "Pooled rodent-borne zoonoses; Lassa/Ebola included as climate-driven outbreak comparators",
    }
    (DATA_PROCESSED / "multi_virus_meta.json").write_text(json.dumps(meta, indent=2))
    return panel
