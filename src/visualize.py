"""Static figures for reports and the Streamlit app."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .config import DATA_PROCESSED, MODELS_DIR, OUTPUTS
from .train import load_panel

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("colorblind")


def _save(fig, name: str) -> Path:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_national_trend() -> Path:
    cases = pd.read_csv(DATA_PROCESSED / "cases_state_year.csv")
    nat = cases.groupby("year")["cases"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(nat["year"], nat["cases"], color="#4a6fa5", edgecolor="white", linewidth=0.4)
    ax.plot(nat["year"], nat["cases"].rolling(3, center=True, min_periods=1).mean(), color="#c44e52", lw=2)
    ax.set_title("Reported hantavirus cases (allocated national totals), 1993–2023")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cases")
    ax.set_xlim(nat["year"].min() - 0.5, nat["year"].max() + 0.5)
    return _save(fig, "01_national_cases.png")


def plot_state_heatmap() -> Path:
    cases = pd.read_csv(DATA_PROCESSED / "cases_state_year.csv")
    pivot = cases.pivot(index="state", columns="year", values="cases")
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(pivot, cmap="YlOrRd", ax=ax, cbar_kws={"label": "Cases"})
    ax.set_title("State × year case counts")
    return _save(fig, "02_state_year_heatmap.png")


def plot_regional_comparison() -> Path:
    cases = pd.read_csv(DATA_PROCESSED / "cases_state_year.csv")
    reg = cases.groupby(["year", "region"])["cases"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    for region, sub in reg.groupby("region"):
        ax.plot(sub["year"], sub["cases"], marker="o", ms=3, label=region)
    ax.set_title("Cases by CDC surveillance region")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cases")
    ax.legend()
    return _save(fig, "03_regional_trends.png")


def plot_precip_vs_cases() -> Path:
    panel = load_panel().sort_values(["geo_id", "year"])
    panel["precip_lag1"] = panel.groupby("geo_id")["precip_annual_mm"].shift(1)
    sw = panel[(panel.get("region") == "Southwest") | (panel["geo_id"].isin(["CO", "NM", "AZ"]))]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(sw["precip_lag1"], sw["cases"], alpha=0.6)
    ax.set_xlabel("Prior-year precipitation (mm)")
    ax.set_ylabel("Cases")
    ax.set_title("Southwest: lagged precipitation vs cases")
    return _save(fig, "04_precip_lag_scatter.png")


def plot_feature_importance() -> Path:
    metrics = json.loads((MODELS_DIR / "metrics.json").read_text())
    imp = pd.Series(metrics["regression"]["feature_importance_reg"]).sort_values()
    fig, ax = plt.subplots(figsize=(8, 6))
    imp.tail(12).plot(kind="barh", ax=ax, color="#55a868")
    ax.set_title("Gradient boosting: top predictors of case count")
    ax.set_xlabel("Importance")
    return _save(fig, "05_feature_importance.png")


def plot_predictions() -> Path:
    pred_path = DATA_PROCESSED / "test_predictions.csv"
    if not pred_path.exists():
        return OUTPUTS / "06_pred_vs_actual.png"
    pred = pd.read_csv(pred_path)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(pred["cases"], pred["predicted_cases"], alpha=0.7, edgecolor="k", linewidth=0.3)
    lim = max(pred["cases"].max(), pred["predicted_cases"].max()) + 1
    ax.plot([0, lim], [0, lim], "--", color="gray")
    ax.set_xlabel("Observed cases (holdout years)")
    ax.set_ylabel("Predicted cases")
    ax.set_title("Holdout: predicted vs observed (state-year)")
    return _save(fig, "06_pred_vs_actual.png")


def plot_forecast_map() -> Path:
    forecasts = sorted(DATA_PROCESSED.glob("forecast_*.csv"))
    forecasts = [f for f in forecasts if "summary" not in f.name]
    if not forecasts:
        return OUTPUTS / "07_forecast_by_state.png"
    us_fc = [f for f in forecasts if "sin_nombre" in f.name]
    fc = pd.read_csv((us_fc or forecasts)[-1])
    fc = fc.sort_values("predicted_cases", ascending=True)
    geo_col = "geo_id" if "geo_id" in fc.columns else "state"
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(fc[geo_col], fc["predicted_cases"], color=np.where(
        fc["risk_tier"] == "elevated", "#c44e52",
        np.where(fc["risk_tier"] == "moderate", "#dd8452", "#4c72b0"),
    ))
    ax.set_xlabel("Predicted cases")
    ax.set_title(f"Forecast: {int(fc['year'].iloc[0])}")
    return _save(fig, "07_forecast_by_state.png")


def generate_all() -> list[Path]:
    paths = [
        plot_national_trend(),
        plot_state_heatmap(),
        plot_regional_comparison(),
        plot_feature_importance(),
        plot_predictions(),
        plot_forecast_map(),
    ]
    # precip scatter needs lag column
    paths.insert(3, plot_precip_vs_cases())
    return paths


def _us_panel():
    p = load_panel()
    return p[p["virus_slug"] == "sin_nombre_us"]


if __name__ == "__main__":
    for p in generate_all():
        print(p)
