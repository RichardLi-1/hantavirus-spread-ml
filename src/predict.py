"""Forecast next-year burden for a virus/geo or all US states."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, MODELS_DIR
from .features import engineer_features
from .train import load_panel


def forecast_year(
    target_year: int | None = None,
    virus_slug: str = "sin_nombre_us",
) -> pd.DataFrame:
    df = load_panel(multi=True)
    df, feature_cols = engineer_features(df)
    reg = joblib.load(MODELS_DIR / "case_regressor.joblib")
    clf = joblib.load(MODELS_DIR / "risk_classifier.joblib")

    if target_year is None:
        target_year = int(df["year"].max()) + 1

    sub = df[df["virus_slug"] == virus_slug]
    latest_year = sub["year"].max()
    latest = sub[sub["year"] == latest_year].copy()
    latest["year"] = target_year
    X = latest[feature_cols].fillna(0)
    latest["predicted_cases"] = np.expm1(reg.predict(X)).clip(0, None)
    latest["high_risk_prob"] = clf.predict_proba(X)[:, 1]
    latest["risk_tier"] = pd.cut(
        latest["high_risk_prob"],
        bins=[-0.01, 0.35, 0.55, 1.0],
        labels=["low", "moderate", "elevated"],
    )

    out_path = DATA_PROCESSED / f"forecast_{virus_slug}_{target_year}.csv"
    latest.to_csv(out_path, index=False)

    summary = {
        "forecast_year": target_year,
        "virus_slug": virus_slug,
        "predicted_total": float(latest["predicted_cases"].sum()),
        "top_geos": latest.nlargest(5, "predicted_cases")[["geo_id", "predicted_cases"]]
        .set_index("geo_id")["predicted_cases"]
        .to_dict(),
    }
    (DATA_PROCESSED / f"forecast_{virus_slug}_{target_year}_summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    return latest


def forecast_all_hantaviruses(target_year: int | None = None) -> dict[str, pd.DataFrame]:
    df = load_panel(multi=True)
    slugs = df[df["is_hantavirus"] == 1]["virus_slug"].unique()
    return {slug: forecast_year(target_year, slug) for slug in slugs}


if __name__ == "__main__":
    fc = forecast_year()
    print(fc[["geo_id", "predicted_cases", "risk_tier"]].head())
