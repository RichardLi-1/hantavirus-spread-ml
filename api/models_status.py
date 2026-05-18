"""Whether trained artifacts exist for forecast/metrics views."""
from __future__ import annotations

from src.config import DATA_PROCESSED, MODELS_DIR

_MODEL_FILES = (
    "case_regressor.joblib",
    "risk_classifier.joblib",
    "feature_columns.joblib",
)


def models_ready() -> bool:
    return all((MODELS_DIR / name).exists() for name in _MODEL_FILES)


def models_status() -> dict:
    return {
        "ready": models_ready(),
        "has_metrics": (MODELS_DIR / "metrics.json").exists(),
        "has_forecasts": any(DATA_PROCESSED.glob("forecast_*.csv")),
    }
