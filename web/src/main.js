import Chart from "chart.js/auto";

const API = "";

const COLOR = {
  ink: "#181d23",
  inkSoft: "#2c333b",
  muted: "#756f63",
  rule: "#d8cfbb",
  blue: "#2c5f7c",
  teal: "#386a73",
  sage: "#4f7a5c",
  ochre: "#c68b3a",
  rust: "#b5483a",
};

// Theme Chart.js defaults to match the editorial palette
Chart.defaults.font.family =
  "'Inter', system-ui, -apple-system, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = COLOR.inkSoft;
Chart.defaults.borderColor = COLOR.rule;
Chart.defaults.plugins.legend.labels.color = COLOR.inkSoft;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.boxHeight = 8;
Chart.defaults.plugins.tooltip.backgroundColor = "#181d23";
Chart.defaults.plugins.tooltip.titleFont = { family: "'JetBrains Mono', monospace", size: 11, weight: "500" };
Chart.defaults.plugins.tooltip.bodyFont = { family: "'Inter', sans-serif", size: 12 };
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 6;
Chart.defaults.plugins.tooltip.displayColors = false;

const gridOpts = {
  color: "rgba(120, 110, 90, 0.12)",
  drawTicks: false,
};
const axisOpts = {
  border: { display: false, color: COLOR.rule },
  ticks: {
    color: COLOR.muted,
    font: { family: "'JetBrains Mono', monospace", size: 11 },
    padding: 6,
  },
  grid: gridOpts,
};

let chart;
let modelsReady = false;

const virusSelect = document.getElementById("virus-select");
const refreshBtn = document.getElementById("refresh-btn");
const trainBtn = document.getElementById("train-btn");
const modelsBanner = document.getElementById("models-banner");
const chartTitle = document.getElementById("chart-title");
const chartEyebrow = document.getElementById("chart-eyebrow");
const virusList = document.getElementById("virus-list");
const kpiStrip = document.getElementById("kpi-strip");
const viewSegmented = document.getElementById("view-segmented");
const riskLegend = document.getElementById("risk-legend");
const statusPill = document.getElementById("status-pill");
const statusText = document.getElementById("status-text");

let currentView = "cases";

async function api(path, options) {
  const r = await fetch(`${API}${path}`, options);
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try { detail = JSON.parse(text).detail ?? text; } catch { /* */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json();
}

function destroyChart() {
  if (chart) chart.destroy();
}

function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const v = Number(n);
  if (!Number.isFinite(v)) return "—";
  return digits === 0
    ? v.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function renderKPIs(items) {
  // items: [{ label, value, sub?, tone?, mono? }]
  kpiStrip.innerHTML = items
    .map(
      (it) => `
      <div class="kpi" ${it.tone ? `data-tone="${it.tone}"` : ""}>
        <div class="k">${it.label}</div>
        <div class="v${it.mono ? " mono" : ""}">${it.value ?? "—"}</div>
        ${it.sub ? `<div class="sub">${it.sub}</div>` : ""}
      </div>`
    )
    .join("");
}

function setBanner(message, kind = "") {
  modelsBanner.textContent = message;
  modelsBanner.classList.remove("hidden", "ok", "error");
  if (kind) modelsBanner.classList.add(kind);
}

function hideBanner() {
  modelsBanner.classList.add("hidden");
}

function setStatus(state, message) {
  statusPill.classList.remove("ready", "error");
  if (state === "ready") statusPill.classList.add("ready");
  if (state === "error") statusPill.classList.add("error");
  statusText.textContent = message;
}

function updateModelGatedViews() {
  viewSegmented.querySelectorAll("[data-needs-models]").forEach((btn) => {
    btn.disabled = !modelsReady;
  });
  if (!modelsReady && ["forecast", "metrics"].includes(currentView)) {
    setActiveView("cases");
  }
}

function setActiveView(view) {
  currentView = view;
  viewSegmented.querySelectorAll("button").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
  });
}

async function loadModelsStatus() {
  try {
    const status = await api("/api/models/status");
    modelsReady = status.ready;
    updateModelGatedViews();
    if (!modelsReady) {
      setStatus("warn", "models not trained");
      setBanner(
        "Models are not trained yet. Run ./scripts/train.sh locally, or use Train models (full pipeline, several minutes).",
      );
    } else {
      setStatus("ready", "models ready");
      hideBanner();
    }
  } catch (e) {
    setStatus("error", "api unreachable");
    throw e;
  }
}

async function loadViruses() {
  const viruses = await api("/api/viruses");
  virusSelect.innerHTML = viruses
    .map((v) => `<option value="${v.virus_slug}">${v.virus_name}</option>`)
    .join("");
  virusList.innerHTML = viruses
    .map(
      (v) => `
      <li>
        <span class="name">${v.virus_name}</span>
        <span class="meta">${v.records} geo-yrs · ${fmt(v.total_cases)} cases</span>
      </li>`
    )
    .join("");
  if (!virusSelect.value && viruses.length) {
    virusSelect.value =
      viruses.find((v) => v.virus_slug === "sin_nombre_us")?.virus_slug ||
      viruses[0].virus_slug;
  }
}

function virusLabel() {
  return virusSelect.options[virusSelect.selectedIndex]?.text || virusSelect.value;
}

async function showCases() {
  const virus = virusSelect.value;
  const series = await api(`/api/outbreaks/series/${virus}`);
  const byYear = {};
  series.forEach((r) => { byYear[r.year] = (byYear[r.year] || 0) + r.cases; });
  const years = Object.keys(byYear).map(Number).sort((a, b) => a - b);
  const totals = years.map((y) => byYear[y]);

  chartEyebrow.textContent = "Figure 01 · time series";
  chartTitle.textContent = `Reported cases · ${virusLabel()}`;
  riskLegend.classList.add("hidden");

  destroyChart();
  const ctx = document.getElementById("main-chart").getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 380);
  grad.addColorStop(0, "rgba(44, 95, 124, 0.85)");
  grad.addColorStop(1, "rgba(44, 95, 124, 0.55)");

  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: years,
      datasets: [{
        label: "Cases",
        data: totals,
        backgroundColor: grad,
        borderRadius: 3,
        borderSkipped: false,
        maxBarThickness: 28,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: axisOpts, y: { ...axisOpts, beginAtZero: true } },
    },
  });

  const peakIdx = totals.indexOf(Math.max(...totals));
  const last = totals[totals.length - 1] ?? 0;
  const total = totals.reduce((s, n) => s + n, 0);
  renderKPIs([
    { label: "Pathogen", value: virusLabel() },
    { label: "Latest year", value: years[years.length - 1] ?? "—", sub: `${fmt(last)} cases` },
    { label: "Peak year", value: years[peakIdx] ?? "—", sub: `${fmt(totals[peakIdx] ?? 0)} cases`, tone: "rust" },
    { label: "All-time total", value: fmt(total), sub: `${years.length} years on record`, tone: "sage" },
  ]);
}

async function showClimate() {
  const virus = virusSelect.value;
  const outbreaks = await api(`/api/outbreaks?virus=${virus}`);
  const geo = outbreaks[0]?.geo_id;
  if (!geo) {
    chartEyebrow.textContent = "Figure 02";
    chartTitle.textContent = "No climate data available";
    destroyChart();
    renderKPIs([{ label: "Status", value: "—", sub: "no geography to plot" }]);
    return;
  }
  const climate = await api(`/api/climate/${geo}`);

  chartEyebrow.textContent = "Figure 02 · environmental drivers";
  chartTitle.textContent = `Climate signal · ${geo}`;
  riskLegend.classList.add("hidden");

  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
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
        y: { ...axisOpts, position: "left", title: { display: true, text: "mm precip", color: COLOR.muted, font: { size: 11 } } },
        y1: { ...axisOpts, position: "right", title: { display: true, text: "°C", color: COLOR.muted, font: { size: 11 } }, grid: { drawOnChartArea: false } },
      },
    },
  });

  const precipMean = climate.reduce((s, c) => s + (c.precip_annual_mm || 0), 0) / Math.max(climate.length, 1);
  const tempMean = climate.reduce((s, c) => s + (c.temp_annual_c || 0), 0) / Math.max(climate.length, 1);
  renderKPIs([
    { label: "Location", value: geo, mono: true },
    { label: "Years of climate", value: climate.length },
    { label: "Mean precip", value: `${fmt(precipMean, 0)} mm`, sub: "annual avg" },
    { label: "Mean temp", value: `${fmt(tempMean, 1)} °C`, sub: "annual avg", tone: "rust" },
  ]);
}

async function showForecast() {
  const virus = virusSelect.value;
  const rows = await api(`/api/forecasts?virus=${virus}`);
  if (!rows.length) {
    chartEyebrow.textContent = "Figure 03";
    chartTitle.textContent = "No forecast — train models to populate";
    riskLegend.classList.add("hidden");
    destroyChart();
    renderKPIs([{ label: "Status", value: "—", sub: "run ./scripts/train.sh" }]);
    return;
  }
  rows.sort((a, b) => b.predicted_cases - a.predicted_cases);
  const top = rows.slice(0, 15);

  chartEyebrow.textContent = `Figure 03 · forecast ${rows[0].year}`;
  chartTitle.textContent = `Top geographies · predicted cases`;
  riskLegend.classList.remove("hidden");

  const colorFor = (tier) =>
    tier === "elevated" ? COLOR.rust : tier === "moderate" ? COLOR.ochre : COLOR.sage;

  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
    type: "bar",
    data: {
      labels: top.map((r) => r.geo_id),
      datasets: [{
        label: "Predicted cases",
        data: top.map((r) => r.predicted_cases),
        backgroundColor: top.map((r) => colorFor(r.risk_tier)),
        borderRadius: 3,
        borderSkipped: false,
        maxBarThickness: 22,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ...axisOpts, beginAtZero: true }, y: axisOpts },
    },
  });

  const total = rows.reduce((s, r) => s + r.predicted_cases, 0);
  const elevated = rows.filter((r) => r.risk_tier === "elevated").length;
  const moderate = rows.filter((r) => r.risk_tier === "moderate").length;
  renderKPIs([
    { label: "Forecast year", value: rows[0].year, mono: true },
    { label: "Predicted total", value: fmt(total, 1), sub: `${rows.length} geographies` },
    { label: "Elevated risk", value: elevated, sub: "geos flagged", tone: "rust" },
    { label: "Moderate risk", value: moderate, sub: "geos watching", tone: "warm" },
  ]);
}

async function showMetrics() {
  const m = await api("/api/metrics");
  chartEyebrow.textContent = "Figure 04 · model interpretation";
  chartTitle.textContent = "Feature importance · regressor";
  riskLegend.classList.add("hidden");

  const imp = m.feature_importance_reg || {};
  const sorted = Object.entries(imp).sort((a, b) => b[1] - a[1]).slice(0, 12);

  destroyChart();
  chart = new Chart(document.getElementById("main-chart"), {
    type: "bar",
    data: {
      labels: sorted.map(([k]) => k),
      datasets: [{
        label: "Importance",
        data: sorted.map(([, v]) => v),
        backgroundColor: COLOR.teal,
        borderRadius: 3,
        borderSkipped: false,
        maxBarThickness: 22,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ...axisOpts, beginAtZero: true }, y: axisOpts },
    },
  });

  renderKPIs([
    { label: "Training mode", value: m.training_mode || "—", mono: true },
    { label: "MAE (all)", value: fmt(m.regression?.mae_all, 2), sub: "holdout", tone: "sage" },
    { label: "MAE (US HPS)", value: fmt(m.regression?.mae_us_sin_nombre, 2), sub: "holdout subset" },
    { label: "Risk AUC", value: fmt(m.classification?.roc_auc, 3), sub: "ROC area", tone: "warm" },
  ]);
}

async function refresh() {
  try {
    if (currentView === "cases") await showCases();
    else if (currentView === "climate") await showClimate();
    else if (currentView === "forecast") await showForecast();
    else await showMetrics();
  } catch (e) {
    setBanner(`Could not load view: ${e.message}`, "error");
  }
}

async function runTrain() {
  trainBtn.disabled = true;
  refreshBtn.disabled = true;
  setBanner("Training in progress — this can take several minutes. Keep the tab open.", "ok");
  try {
    await api("/api/retrain", { method: "POST" });
    await loadModelsStatus();
    setBanner("Training complete. Forecast and metrics views are now unlocked.", "ok");
    await refresh();
  } catch (e) {
    setBanner(`Training failed: ${e.message}`, "error");
  } finally {
    trainBtn.disabled = false;
    refreshBtn.disabled = false;
  }
}

viewSegmented.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (!btn || btn.disabled) return;
  if (btn.dataset.view === currentView) return;
  setActiveView(btn.dataset.view);
  refresh();
});

refreshBtn.addEventListener("click", refresh);
trainBtn.addEventListener("click", runTrain);
virusSelect.addEventListener("change", refresh);

loadModelsStatus()
  .then(() => loadViruses())
  .then(refresh)
  .catch((e) => {
    setBanner(`API unreachable: ${e.message}. Start it with ./scripts/start.sh`, "error");
    renderKPIs([{ label: "Status", value: "Offline", sub: e.message, tone: "rust" }]);
  });
