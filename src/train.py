"""Train on pooled multi-virus history; evaluate US hantavirus holdout separately."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from .config import DATA_PROCESSED, MODELS_DIR, RANDOM_STATE
from .features import engineer_features


def load_panel(multi: bool = True) -> pd.DataFrame:
    parquet = DATA_PROCESSED / ("multi_virus_panel.parquet" if multi else "state_year_panel.parquet")
    csv = DATA_PROCESSED / ("multi_virus_panel.csv" if multi else "cases_state_year.csv")
    if parquet.exists():
        return pd.read_parquet(parquet)
    if csv.exists():
        return pd.read_csv(csv)
    from .multi_virus_data import build_unified_panel

    build_unified_panel()
    return pd.read_parquet(parquet)


def train_models(test_years: int = 5, multi_virus: bool = True) -> dict:
    df = load_panel(multi=multi_virus)
    if "log_cases" not in df.columns:
        df["log_cases"] = np.log1p(df["cases"])

    df, feature_cols = engineer_features(df)
    df = df.dropna(subset=feature_cols + ["cases", "high_risk_year", "log_cases"])

    max_year = df["year"].max()
    train = df[df["year"] <= max_year - test_years]
    test = df[df["year"] > max_year - test_years]

    X_train, y_log_train = train[feature_cols], train["log_cases"]
    X_test, y_log_test = test[feature_cols], test["log_cases"]
    y_reg_test = test["cases"]
    y_clf_train, y_clf_test = train["high_risk_year"], test["high_risk_year"]

    reg = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                GradientBoostingRegressor(
                    n_estimators=250,
                    max_depth=5,
                    learning_rate=0.04,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    reg.fit(X_train, y_log_train)
    pred_log = reg.predict(X_test)
    pred_reg = np.expm1(pred_log).clip(0, None)

    clf = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                GradientBoostingClassifier(
                    n_estimators=180,
                    max_depth=4,
                    learning_rate=0.06,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    clf.fit(X_train, y_clf_train)
    proba = clf.predict_proba(X_test)[:, 1]

    # US Sin Nombre state-level subset metrics
    us_mask = test["virus_slug"] == "sin_nombre_us"
    us_mae = None
    if us_mask.any():
        us_mae = float(mean_absolute_error(test.loc[us_mask, "cases"], pred_reg[us_mask.values]))

    metrics = {
        "training_mode": "multi_virus_pooled" if multi_virus else "us_only",
        "train_rows": len(train),
        "test_rows": len(test),
        "viruses_in_train": sorted(train["virus_slug"].unique().tolist()),
        "regression": {
            "mae_all": float(mean_absolute_error(y_reg_test, pred_reg)),
            "rmse_all": float(np.sqrt(mean_squared_error(y_reg_test, pred_reg))),
            "mae_us_sin_nombre": us_mae,
            "test_years": list(map(int, sorted(test["year"].unique()))),
        },
        "classification": {
            "roc_auc": float(roc_auc_score(y_clf_test, proba)) if y_clf_test.nunique() > 1 else None,
        },
        "feature_importance_reg": dict(
            zip(
                feature_cols,
                reg.named_steps["model"].feature_importances_.tolist(),
            )
        ),
    }

    tscv = TimeSeriesSplit(n_splits=4)
    cv_mae = []
    for tr_idx, va_idx in tscv.split(df):
        sub, val = df.iloc[tr_idx], df.iloc[va_idx]
        m = GradientBoostingRegressor(
            n_estimators=150, max_depth=4, learning_rate=0.05, random_state=RANDOM_STATE
        )
        m.fit(sub[feature_cols], sub["log_cases"])
        p = np.expm1(m.predict(val[feature_cols])).clip(0, None)
        cv_mae.append(mean_absolute_error(val["cases"], p))
    metrics["regression"]["cv_mae_mean"] = float(np.mean(cv_mae))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(reg, MODELS_DIR / "case_regressor.joblib")
    joblib.dump(clf, MODELS_DIR / "risk_classifier.joblib")
    joblib.dump(feature_cols, MODELS_DIR / "feature_columns.joblib")

    test_out = test[
        ["year", "virus_slug", "virus_name", "geo_id", "geo_name", "country", "cases", "is_hantavirus"]
    ].copy()
    if "region" in test.columns:
        test_out["region"] = test["region"]
    test_out["predicted_cases"] = pred_reg
    test_out["high_risk_prob"] = proba
    test_out.to_csv(DATA_PROCESSED / "test_predictions.csv", index=False)

    (MODELS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    print(json.dumps(train_models(), indent=2))
