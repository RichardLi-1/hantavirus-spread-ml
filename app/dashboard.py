"""
Interactive dashboard — run: streamlit run app/dashboard.py
"""
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "outputs" / "figures"


@st.cache_data
def load_cases():
    return pd.read_csv(PROCESSED / "cases_state_year.csv")


@st.cache_data
def load_panel():
    return pd.read_parquet(PROCESSED / "state_year_panel.parquet")


def main():
    st.set_page_config(page_title="Hantavirus spread model", layout="wide")
    st.title("Hantavirus case burden — exploration & forecasts")

    cases = load_cases()
    panel = load_panel()

    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Climate drivers", "Model output", "Figures"])

    with tab1:
        nat = cases.groupby("year")["cases"].sum().reset_index()
        fig = px.bar(nat, x="year", y="cases", title="US cases by year (project dataset)")
        st.plotly_chart(fig, use_container_width=True)

        by_region = cases.groupby(["year", "region"])["cases"].sum().reset_index()
        st.plotly_chart(
            px.line(by_region, x="year", y="cases", color="region", markers=True),
            use_container_width=True,
        )

        st.subheader("State totals (1993–2023)")
        state_tot = cases.groupby("state")["cases"].sum().sort_values(ascending=False)
        st.dataframe(state_tot.reset_index().rename(columns={"cases": "total_cases"}))

    with tab2:
        st.markdown(
            "Prior-year precipitation is the main ecological lever in Southwest Sin Nombre systems "
            "(Engelthaler et al., *BioScience* 2002; Glass et al., EID 1999)."
        )
        sw = panel[panel["region"] == "Southwest"].copy()
        sw["precip_lag1"] = sw.groupby("state")["precip_annual_mm"].shift(1)
        sw = sw.dropna(subset=["precip_lag1"])
        st.plotly_chart(
            px.scatter(
                sw,
                x="precip_lag1",
                y="cases",
                color="state",
                trendline="ols",
                title="Southwest: lag-1 precipitation vs cases",
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            px.imshow(
                panel.pivot_table(index="state", columns="year", values="precip_annual_mm"),
                aspect="auto",
                color_continuous_scale="Blues",
                title="Annual precipitation (mm) by state",
            ),
            use_container_width=True,
        )

    with tab3:
        pred_file = PROCESSED / "test_predictions.csv"
        if pred_file.exists():
            pred = pd.read_csv(pred_file)
            st.plotly_chart(
                px.scatter(pred, x="cases", y="predicted_cases", color="region", hover_data=["state", "year"]),
                use_container_width=True,
            )
        fc_files = sorted(PROCESSED.glob("forecast_*.csv"))
        fc_files = [f for f in fc_files if "summary" not in f.name]
        if fc_files:
            fc = pd.read_csv(fc_files[-1])
            st.subheader(f"Forecast year {fc['year'].iloc[0]}")
            st.plotly_chart(
                px.bar(fc.sort_values("predicted_cases"), x="predicted_cases", y="state", orientation="h", color="risk_tier"),
                use_container_width=True,
            )
        metrics_path = ROOT / "models" / "metrics.json"
        if metrics_path.exists():
            st.json(metrics_path.read_text())

    with tab4:
        if FIGURES.exists():
            for img in sorted(FIGURES.glob("*.png")):
                st.image(str(img), caption=img.name)
        else:
            st.info("Run `python scripts/run_pipeline.py` to generate figures.")


if __name__ == "__main__":
    main()
