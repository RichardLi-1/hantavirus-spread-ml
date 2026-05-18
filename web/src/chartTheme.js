import Chart from "chart.js/auto";

export const COLOR = {
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

const gridOpts = {
  color: "rgba(120, 110, 90, 0.12)",
  drawTicks: false,
};

export const axisOpts = {
  border: { display: false, color: COLOR.rule },
  ticks: {
    color: COLOR.muted,
    font: { family: "'JetBrains Mono', monospace", size: 11 },
    padding: 6,
  },
  grid: gridOpts,
};

export function configureChartDefaults() {
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
  Chart.defaults.plugins.tooltip.titleFont = {
    family: "'JetBrains Mono', monospace",
    size: 11,
    weight: "500",
  };
  Chart.defaults.plugins.tooltip.bodyFont = {
    family: "'Inter', sans-serif",
    size: 12,
  };
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 6;
  Chart.defaults.plugins.tooltip.displayColors = false;
}
