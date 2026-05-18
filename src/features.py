"""Lag and climate features for multi-virus geo-year panels."""
from __future__ import annotations

import numpy as np
import pandas as pd

GROUP_COLS = ["virus_slug", "geo_id"]


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.sort_values(GROUP_COLS + ["year"]).copy()
    g = out.groupby(GROUP_COLS, group_keys=False)

    for lag in (1, 2):
        out[f"precip_lag{lag}"] = g["precip_annual_mm"].shift(lag)
        out[f"temp_lag{lag}"] = g["temp_annual_c"].shift(lag)

    out["precip_2yr_mean"] = g["precip_annual_mm"].transform(
        lambda s: s.shift(1).rolling(2, min_periods=1).mean()
    )
    out["temp_anomaly"] = out["temp_annual_c"] - g["temp_annual_c"].transform("mean")
    out["precip_anomaly"] = out["precip_annual_mm"] - g["precip_annual_mm"].transform("mean")
    out["cases_lag1"] = g["cases"].shift(1)
    out["cases_roll3"] = g["cases"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    out["log_cases_lag1"] = g["log_cases"].shift(1) if "log_cases" in out.columns else np.log1p(out["cases_lag1"])

    # virus identity (model learns scale differences across pathogens)
    for slug in sorted(out["virus_slug"].unique()):
        out[f"v_{slug}"] = (out["virus_slug"] == slug).astype(int)

    out["is_hantavirus_feat"] = out.get("is_hantavirus", (out["family"] == "Hantaviridae").astype(int))

    climate_cols = [
        "precip_annual_mm",
        "temp_annual_c",
        "precip_winter_mm",
        "precip_summer_mm",
        "precip_lag1",
        "precip_lag2",
        "temp_lag1",
        "temp_lag2",
        "precip_2yr_mean",
        "temp_anomaly",
        "precip_anomaly",
        "cases_lag1",
        "cases_roll3",
        "log_cases_lag1",
        "is_hantavirus_feat",
    ]
    virus_cols = [c for c in out.columns if c.startswith("v_")]
    feature_cols = climate_cols + virus_cols
    return out, feature_cols
