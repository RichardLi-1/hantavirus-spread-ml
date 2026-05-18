#!/usr/bin/env bash
# Train models + forecasts on the existing panel (no climate refetch).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "Run ./scripts/setup.sh first"
  exit 1
fi

export PYTHONPATH="${PWD}"
echo "== Training on processed panel =="
.venv/bin/python -c "
from api.database import sync_from_files
from src.predict import forecast_all_hantaviruses, forecast_year
from src.train import train_models

metrics = train_models(test_years=5, multi_virus=True)
print(f\"   holdout MAE (all): {metrics['regression']['mae_all']:.2f}\")
us = metrics['regression'].get('mae_us_sin_nombre')
if us is not None:
    print(f\"   holdout MAE (US Sin Nombre): {us:.2f}\")
print('== Forecasting hantavirus strains ==')
forecast_year(virus_slug='sin_nombre_us')
forecast_all_hantaviruses()
sync_from_files()
print('== Done — restart or refresh the dashboard ==')
"
