import Chart from "chart.js/auto";

const API = "";

let chart;

const virusSelect = document.getElementById("virus-select");
const viewSelect = document.getElementById("view-select");
const refreshBtn = document.getElementById("refresh-btn");
const statsDl = document.getElementById("stats-dl");
const chartTitle = document.getElementById("chart-title");
const virusList = document.getElementById("virus-list");

async function api(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function destroyChart() {
  if (chart) chart.destroy();
}

function renderStats(pairs) {
  statsDl.innerHTML = pairs
    .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
    .join("");
}

async function loadViruses() {
  const viruses = await api("/api/viruses");
  virusSelect.innerHTML = viruses
    .map((v) => `<option value="${v.virus_slug}">${v.virus_name}</option>`)
    .join("");
  virusList.innerHTML = viruses
    .map(
      (v) =>
        `<li><strong>${v.virus_name}</strong> — ${v.records} geo-years, ${v.total_cases} cases total</li>`
    )
    .join("");
  if (!virusSelect.value && viruses.length) {
    virusSelect.value = viruses.find((v) => v.virus_slug === "sin_nombre_us")?.virus_slug || viruses[0].virus_slug;
  }
}

async function showCases() {
  const virus = virusSelect.value;
  const series = await api(`/api/outbreaks/series/${virus}`);
  const byYear = {};
  series.forEach((r) => {
    byYear[r.year] = (byYear[r.year] || 0) + r.cases;
  });
  const years = Object.keys(byYear).map(Number).sort((a, b) => a - b);
  const totals = years.map((y) => byYear[y]);
  chartTitle.textContent = "Cases over time";
  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
    type: "bar",
    data: {
      labels: years,
      datasets: [{ label: "Cases", data: totals, backgroundColor: "#3d6b8f" }],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });
  const last = totals[totals.length - 1];
  renderStats([
    ["Pathogen", virus],
    ["Years", years.length],
    ["Latest year", years[years.length - 1]],
    ["Latest cases", last],
    ["Peak year", years[totals.indexOf(Math.max(...totals))]],
  ]);
}

async function showClimate() {
  const virus = virusSelect.value;
  const outbreaks = await api(`/api/outbreaks?virus=${virus}`);
  const geo = outbreaks[0]?.geo_id;
  if (!geo) return;
  const climate = await api(`/api/climate/${geo}`);
  chartTitle.textContent = `Climate at ${geo}`;
  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
    type: "line",
    data: {
      labels: climate.map((c) => c.year),
      datasets: [
        {
          label: "Precip (mm)",
          data: climate.map((c) => c.precip_annual_mm),
          borderColor: "#3d6b8f",
          yAxisID: "y",
        },
        {
          label: "Temp (°C)",
          data: climate.map((c) => c.temp_annual_c),
          borderColor: "#c45c4a",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { position: "left", title: { display: true, text: "mm" } },
        y1: { position: "right", grid: { drawOnChartArea: false } },
      },
    },
  });
  renderStats([["Location", geo], ["Climate points", climate.length]]);
}

async function showForecast() {
  const virus = virusSelect.value;
  const rows = await api(`/api/forecasts?virus=${virus}`);
  if (!rows.length) {
    chartTitle.textContent = "No forecast — run pipeline";
    destroyChart();
    renderStats([["Status", "Train models first"]]);
    return;
  }
  rows.sort((a, b) => b.predicted_cases - a.predicted_cases);
  chartTitle.textContent = `Forecast ${rows[0].year}`;
  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
    type: "bar",
    data: {
      labels: rows.slice(0, 15).map((r) => r.geo_id),
      datasets: [
        {
          label: "Predicted cases",
          data: rows.slice(0, 15).map((r) => r.predicted_cases),
          backgroundColor: rows.slice(0, 15).map((r) =>
            r.risk_tier === "elevated" ? "#c45c4a" : r.risk_tier === "moderate" ? "#d4a05a" : "#3d6b8f"
          ),
        },
      ],
    },
    options: { indexAxis: "y", responsive: true },
  });
  renderStats([
    ["Year", rows[0].year],
    ["Predicted total", rows.reduce((s, r) => s + r.predicted_cases, 0).toFixed(1)],
    ["Elevated geos", rows.filter((r) => r.risk_tier === "elevated").length],
  ]);
}

async function showMetrics() {
  const m = await api("/api/metrics");
  chartTitle.textContent = "Feature importance (regression)";
  destroyChart();
  const imp = m.feature_importance_reg || {};
  const sorted = Object.entries(imp).sort((a, b) => b[1] - a[1]).slice(0, 12);
  chart = new Chart(document.getElementById("main-chart"), {
    type: "bar",
    data: {
      labels: sorted.map(([k]) => k),
      datasets: [{ label: "Importance", data: sorted.map(([, v]) => v), backgroundColor: "#5a8f6b" }],
    },
    options: { indexAxis: "y", responsive: true },
  });
  renderStats([
    ["Training", m.training_mode],
    ["Holdout MAE (all)", m.regression?.mae_all?.toFixed(2)],
    ["Holdout MAE (US HPS)", m.regression?.mae_us_sin_nombre?.toFixed(2) ?? "—"],
    ["CV MAE", m.regression?.cv_mae_mean?.toFixed(2)],
    ["Risk AUC", m.classification?.roc_auc?.toFixed(3) ?? "—"],
  ]);
}

async function refresh() {
  const view = viewSelect.value;
  if (view === "cases") await showCases();
  else if (view === "climate") await showClimate();
  else if (view === "forecast") await showForecast();
  else await showMetrics();
}

refreshBtn.addEventListener("click", refresh);
virusSelect.addEventListener("change", refresh);
viewSelect.addEventListener("change", refresh);

loadViruses().then(refresh).catch((e) => {
  statsDl.innerHTML = `<dt>Error</dt><dd>${e.message}. Start API: uvicorn api.main:app</dd>`;
});
