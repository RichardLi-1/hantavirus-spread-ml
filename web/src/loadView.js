import { api } from "./api";
import { axisOpts, COLOR } from "./chartTheme";
import { fmt } from "./format";

/** @typedef {{ label: string, value: string, sub?: string, tone?: string, mono?: boolean }} Kpi */

/**
 * @returns {Promise<{ eyebrow: string, title: string, showRiskLegend: boolean, kpis: Kpi[], chartConfig: import('chart.js').ChartConfiguration | null }>}
 */
export async function loadViewData(view, virusSlug, virusLabel) {
  if (view === "cases") return loadCases(virusSlug, virusLabel);
  if (view === "climate") return loadClimate(virusSlug);
  if (view === "forecast") return loadForecast(virusSlug);
  return loadMetrics();
}

async function loadCases(virus, virusLabel) {
  const series = await api(`/api/outbreaks/series/${virus}`);
  const byYear = {};
  series.forEach((r) => {
    byYear[r.year] = (byYear[r.year] || 0) + r.cases;
  });
  const years = Object.keys(byYear).map(Number).sort((a, b) => a - b);
  const totals = years.map((y) => byYear[y]);

  const peakIdx = totals.indexOf(Math.max(...totals));
  const last = totals[totals.length - 1] ?? 0;
  const total = totals.reduce((s, n) => s + n, 0);

  return {
    eyebrow: "Figure 01 · time series",
    title: `Reported cases · ${virusLabel}`,
    showRiskLegend: false,
    kpis: [
      { label: "Pathogen", value: virusLabel },
      {
        label: "Latest year",
        value: String(years[years.length - 1] ?? "—"),
        sub: `${fmt(last)} cases`,
      },
      {
        label: "Peak year",
        value: String(years[peakIdx] ?? "—"),
        sub: `${fmt(totals[peakIdx] ?? 0)} cases`,
        tone: "rust",
      },
      {
        label: "All-time total",
        value: fmt(total),
        sub: `${years.length} years on record`,
        tone: "sage",
      },
    ],
    chartConfig: {
      type: "bar",
      data: {
        labels: years,
        datasets: [
          {
            label: "Cases",
            data: totals,
            backgroundColor: (ctx) => {
              const { chart } = ctx;
              const { ctx: canvasCtx, chartArea } = chart;
              if (!chartArea) return "rgba(44, 95, 124, 0.7)";
              const grad = canvasCtx.createLinearGradient(
                0,
                chartArea.top,
                0,
                chartArea.bottom,
              );
              grad.addColorStop(0, "rgba(44, 95, 124, 0.85)");
              grad.addColorStop(1, "rgba(44, 95, 124, 0.55)");
              return grad;
            },
            borderRadius: 3,
            borderSkipped: false,
            maxBarThickness: 28,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: axisOpts, y: { ...axisOpts, beginAtZero: true } },
      },
    },
  };
}

async function loadClimate(virus) {
  const outbreaks = await api(`/api/outbreaks?virus=${virus}`);
  const geo = outbreaks[0]?.geo_id;
  if (!geo) {
    return {
      eyebrow: "Figure 02",
      title: "No climate data available",
      showRiskLegend: false,
      kpis: [{ label: "Status", value: "—", sub: "no geography to plot" }],
      chartConfig: null,
    };
  }
  const climate = await api(`/api/climate/${geo}`);
  const precipMean =
    climate.reduce((s, c) => s + (c.precip_annual_mm || 0), 0) /
    Math.max(climate.length, 1);
  const tempMean =
    climate.reduce((s, c) => s + (c.temp_annual_c || 0), 0) /
    Math.max(climate.length, 1);

  return {
    eyebrow: "Figure 02 · environmental drivers",
    title: `Climate signal · ${geo}`,
    showRiskLegend: false,
    kpis: [
      { label: "Location", value: geo, mono: true },
      { label: "Years of climate", value: String(climate.length) },
      {
        label: "Mean precip",
        value: `${fmt(precipMean, 0)} mm`,
        sub: "annual avg",
      },
      {
        label: "Mean temp",
        value: `${fmt(tempMean, 1)} °C`,
        sub: "annual avg",
        tone: "rust",
      },
    ],
    chartConfig: {
      type: "line",
      data: {
        labels: climate.map((c) => c.year),
        datasets: [
          {
            label: "Precipitation (mm)",
            data: climate.map((c) => c.precip_annual_mm),
            borderColor: COLOR.blue,
            backgroundColor: "rgba(44,95,124,0.08)",
            fill: true,
            borderWidth: 1.75,
            tension: 0.3,
            pointRadius: 2.5,
            pointBackgroundColor: COLOR.blue,
            yAxisID: "y",
          },
          {
            label: "Temperature (°C)",
            data: climate.map((c) => c.temp_annual_c),
            borderColor: COLOR.rust,
            backgroundColor: "rgba(181,72,58,0.05)",
            borderWidth: 1.75,
            tension: 0.3,
            pointRadius: 2.5,
            pointBackgroundColor: COLOR.rust,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: axisOpts,
          y: {
            ...axisOpts,
            position: "left",
            title: {
              display: true,
              text: "mm precip",
              color: COLOR.muted,
              font: { size: 11 },
            },
          },
          y1: {
            ...axisOpts,
            position: "right",
            title: {
              display: true,
              text: "°C",
              color: COLOR.muted,
              font: { size: 11 },
            },
            grid: { drawOnChartArea: false },
          },
        },
      },
    },
  };
}

async function loadForecast(virus) {
  const rows = await api(`/api/forecasts?virus=${virus}`);
  if (!rows.length) {
    return {
      eyebrow: "Figure 03",
      title: "No forecast — train models to populate",
      showRiskLegend: false,
      kpis: [{ label: "Status", value: "—", sub: "run ./scripts/train.sh" }],
      chartConfig: null,
    };
  }
  rows.sort((a, b) => b.predicted_cases - a.predicted_cases);
  const top = rows.slice(0, 15);
  const colorFor = (tier) =>
    tier === "elevated"
      ? COLOR.rust
      : tier === "moderate"
        ? COLOR.ochre
        : COLOR.sage;
  const total = rows.reduce((s, r) => s + r.predicted_cases, 0);
  const elevated = rows.filter((r) => r.risk_tier === "elevated").length;
  const moderate = rows.filter((r) => r.risk_tier === "moderate").length;

  return {
    eyebrow: `Figure 03 · forecast ${rows[0].year}`,
    title: "Top geographies · predicted cases",
    showRiskLegend: true,
    kpis: [
      { label: "Forecast year", value: String(rows[0].year), mono: true },
      {
        label: "Predicted total",
        value: fmt(total, 1),
        sub: `${rows.length} geographies`,
      },
      {
        label: "Elevated risk",
        value: String(elevated),
        sub: "geos flagged",
        tone: "rust",
      },
      {
        label: "Moderate risk",
        value: String(moderate),
        sub: "geos watching",
        tone: "warm",
      },
    ],
    chartConfig: {
      type: "bar",
      data: {
        labels: top.map((r) => r.geo_id),
        datasets: [
          {
            label: "Predicted cases",
            data: top.map((r) => r.predicted_cases),
            backgroundColor: top.map((r) => colorFor(r.risk_tier)),
            borderRadius: 3,
            borderSkipped: false,
            maxBarThickness: 22,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ...axisOpts, beginAtZero: true },
          y: axisOpts,
        },
      },
    },
  };
}

async function loadMetrics() {
  const m = await api("/api/metrics");
  const imp = m.feature_importance_reg || {};
  const sorted = Object.entries(imp)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  return {
    eyebrow: "Figure 04 · model interpretation",
    title: "Feature importance · regressor",
    showRiskLegend: false,
    kpis: [
      { label: "Training mode", value: m.training_mode || "—", mono: true },
      {
        label: "MAE (all)",
        value: fmt(m.regression?.mae_all, 2),
        sub: "holdout",
        tone: "sage",
      },
      {
        label: "MAE (US HPS)",
        value: fmt(m.regression?.mae_us_sin_nombre, 2),
        sub: "holdout subset",
      },
      {
        label: "Risk AUC",
        value: fmt(m.classification?.roc_auc, 3),
        sub: "ROC area",
        tone: "warm",
      },
    ],
    chartConfig: {
      type: "bar",
      data: {
        labels: sorted.map(([k]) => k),
        datasets: [
          {
            label: "Importance",
            data: sorted.map(([, v]) => v),
            backgroundColor: COLOR.teal,
            borderRadius: 3,
            borderSkipped: false,
            maxBarThickness: 22,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ...axisOpts, beginAtZero: true },
          y: axisOpts,
        },
      },
    },
  };
}
