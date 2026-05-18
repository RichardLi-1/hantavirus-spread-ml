#!/usr/bin/env python3
"""End-to-end: multi-virus panel, train, forecast, sync DB."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.multi_virus_data import build_unified_panel
from src.predict import forecast_all_hantaviruses, forecast_year
from src.train import train_models
from src.visualize import generate_all


def main():
    print("== Building multi-virus panel (cases + Open-Meteo) ==")
    panel = build_unified_panel(refetch_climate=False)
    print(f"   {len(panel)} rows, viruses: {panel['virus_slug'].nunique()}")

    print("== Training (pooled historical viruses) ==")
    metrics = train_models(test_years=5, multi_virus=True)
    print(f"   holdout MAE (all): {metrics['regression']['mae_all']:.2f}")
    if metrics["regression"].get("mae_us_sin_nombre"):
        print(f"   holdout MAE (US Sin Nombre): {metrics['regression']['mae_us_sin_nombre']:.2f}")

    print("== Forecasting hantavirus strains ==")
    forecast_year(virus_slug="sin_nombre_us")
    forecast_all_hantaviruses()

    print("== Figures ==")
    try:
        for p in generate_all():
            print(f"   {p}")
    except Exception as e:
        print(f"   (figures skipped: {e})")

    try:
        from api.database import sync_from_files

        sync_from_files()
        print("== SQLite synced ==")
    except Exception as e:
        print(f"   (db sync skipped: {e})")


if __name__ == "__main__":
    main()
