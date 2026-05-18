#!/usr/bin/env python3
"""Build panel without network (synthetic climate). Use when disk/API unavailable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.config import DATA_PROCESSED, DATA_RAW, STATE_COORDS, STATE_TO_REGION, STATE_CASE_WEIGHTS


def main():
    raw = pd.read_csv(DATA_RAW / "multi_virus_historical.csv")
    national = pd.read_csv(DATA_RAW / "national_cases_by_year.csv")

    # simple US state allocation
    weights = pd.Series(STATE_CASE_WEIGHTS) / sum(STATE_CASE_WEIGHTS.values())
    us_rows = []
    for _, row in national.iterrows():
        y, total = int(row["year"]), int(row["cases_national"])
        alloc = (weights * total).round().astype(int)
        diff = total - alloc.sum()
        alloc.iloc[0] += diff
        for st, c in alloc.items():
            us_rows.append(
                {
                    "virus_slug": "sin_nombre_us",
                    "virus_name": "Sin Nombre (HPS)",
                    "family": "Hantaviridae",
                    "geo_id": st,
                    "geo_name": st,
                    "geo_type": "state",
                    "country": "USA",
                    "year": y,
                    "cases": int(c),
                    "region": STATE_TO_REGION[st],
                    "is_hantavirus": 1,
                }
            )

    intl = raw[~((raw["virus_slug"] == "sin_nombre_us") & (raw["geo_type"] == "national"))].copy()
    intl = intl.rename(columns={"source": "source_note"})
    intl["is_hantavirus"] = intl["virus_slug"].str.startswith(("sin_", "puuv_", "andes_", "seoul_", "dobrava_")).astype(int)
    intl["region"] = None

    panel = pd.concat([pd.DataFrame(us_rows), intl], ignore_index=True)

    # synthetic climate from lat/lon + year (deterministic)
    coords = raw.drop_duplicates("geo_id").set_index("geo_id")[["lat", "lon"]]
    for st, (la, lo) in STATE_COORDS.items():
        coords.loc[st] = [la, lo]

    def synth_climate(row):
        la = coords.loc[row["geo_id"], "lat"] if row["geo_id"] in coords.index else 40.0
        y = row["year"]
        precip = 400 + 80 * np.sin(y / 3.5) + 30 * (la / 50)
        temp = 8 + 0.15 * la + 0.5 * np.cos(y / 4)
        return pd.Series(
            {
                "precip_annual_mm": precip,
                "temp_annual_c": temp,
                "precip_winter_mm": precip * 0.35,
                "precip_summer_mm": precip * 0.25,
                "precip_other_mm": precip * 0.4,
            }
        )

    climate = panel.apply(synth_climate, axis=1)
    panel = pd.concat([panel, climate], axis=1)
    panel["log_cases"] = np.log1p(panel["cases"])
    panel["high_risk_year"] = (
        panel["cases"] >= panel.groupby(["virus_slug", "geo_id"])["cases"].transform("mean")
    ).astype(int)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.to_csv(DATA_PROCESSED / "multi_virus_panel.csv", index=False)
    try:
        panel.to_parquet(DATA_PROCESSED / "multi_virus_panel.parquet", index=False)
    except Exception:
        pass
    us = panel[panel["virus_slug"] == "sin_nombre_us"].rename(columns={"geo_id": "state"})
    us[["year", "state", "cases", "region"]].to_csv(DATA_PROCESSED / "cases_state_year.csv", index=False)
    try:
        us.to_parquet(DATA_PROCESSED / "state_year_panel.parquet", index=False)
    except Exception:
        pass
    print(f"Wrote {len(panel)} rows (offline climate)")


if __name__ == "__main__":
    main()
