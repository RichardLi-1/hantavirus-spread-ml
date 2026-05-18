import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { loadViewData } from "./loadView";
import { fmt } from "./format";
import { KpiStrip } from "./components/KpiStrip";
import { MainChart } from "./components/MainChart";

const VIEWS = [
  { id: "cases", label: "Cases", needsModels: false },
  { id: "climate", label: "Climate", needsModels: false },
  { id: "forecast", label: "Forecast", needsModels: true },
  { id: "metrics", label: "Metrics", needsModels: true },
];

export default function App() {
  const [viruses, setViruses] = useState([]);
  const [virusSlug, setVirusSlug] = useState("");
  const [modelsReady, setModelsReady] = useState(false);
  const [statusState, setStatusState] = useState("loading");
  const [statusMessage, setStatusMessage] = useState("checking models…");
  const [banner, setBanner] = useState({ message: "", kind: "", hidden: true });
  const [currentView, setCurrentView] = useState("cases");
  const [busy, setBusy] = useState(false);
  const [viewState, setViewState] = useState({
    eyebrow: "Figure 01",
    title: "Cases over time",
    showRiskLegend: false,
    kpis: [],
    chartConfig: null,
  });

  const virusLabel = useMemo(() => {
    const v = viruses.find((x) => x.virus_slug === virusSlug);
    return v?.virus_name || virusSlug;
  }, [viruses, virusSlug]);

  const setBannerMsg = useCallback((message, kind = "", hidden = false) => {
    setBanner({ message, kind, hidden });
  }, []);

  const hideBanner = useCallback(() => {
    setBanner((b) => ({ ...b, hidden: true }));
  }, []);

  const loadModelsStatus = useCallback(async () => {
    const status = await api("/api/models/status");
    const ready = status.ready;
    setModelsReady(ready);
    if (!ready) {
      setStatusState("warn");
      setStatusMessage("models not trained");
      setBannerMsg(
        "Models are not trained yet. Run ./scripts/train.sh locally, or use Train models (full pipeline, several minutes).",
      );
    } else {
      setStatusState("ready");
      setStatusMessage("models ready");
      hideBanner();
    }
    return ready;
  }, [hideBanner, setBannerMsg]);

  const loadViruses = useCallback(async () => {
    const list = await api("/api/viruses");
    setViruses(list);
    if (!virusSlug && list.length) {
      const preferred =
        list.find((v) => v.virus_slug === "sin_nombre_us")?.virus_slug ||
        list[0].virus_slug;
      setVirusSlug(preferred);
    }
  }, [virusSlug]);

  const refresh = useCallback(async () => {
    if (!virusSlug) return;
    try {
      const data = await loadViewData(currentView, virusSlug, virusLabel);
      setViewState(data);
    } catch (e) {
      setBannerMsg(`Could not load view: ${e.message}`, "error");
    }
  }, [currentView, virusSlug, virusLabel, setBannerMsg]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadModelsStatus();
        await loadViruses();
      } catch (e) {
        if (cancelled) return;
        setStatusState("error");
        setStatusMessage("api unreachable");
        setBannerMsg(
          `API unreachable: ${e.message}. Start it with ./scripts/start.sh`,
          "error",
        );
        setViewState((s) => ({
          ...s,
          kpis: [{ label: "Status", value: "Offline", sub: e.message, tone: "rust" }],
        }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadModelsStatus, loadViruses, setBannerMsg]);

  useEffect(() => {
    if (!virusSlug) return;
    refresh();
  }, [virusSlug, currentView, refresh]);

  useEffect(() => {
    if (!modelsReady && ["forecast", "metrics"].includes(currentView)) {
      setCurrentView("cases");
    }
  }, [modelsReady, currentView]);

  const onViewChange = (view) => {
    if (view === currentView) return;
    setCurrentView(view);
  };

  const onTrain = async () => {
    setBusy(true);
    setBannerMsg(
      "Training in progress — this can take several minutes. Keep the tab open.",
      "ok",
    );
    try {
      await api("/api/retrain", { method: "POST" });
      await loadModelsStatus();
      setBannerMsg(
        "Training complete. Forecast and metrics views are now unlocked.",
        "ok",
      );
      await refresh();
    } catch (e) {
      setBannerMsg(`Training failed: ${e.message}`, "error");
    } finally {
      setBusy(false);
    }
  };

  const statusClass =
    statusState === "ready"
      ? "ready"
      : statusState === "error"
        ? "error"
        : "";

  const bannerClass = [
    "banner",
    banner.hidden ? "hidden" : "",
    banner.kind,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="paper">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 32 32" width="22" height="22">
                <circle
                  cx="16"
                  cy="16"
                  r="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.25"
                />
                <circle
                  cx="16"
                  cy="16"
                  r="9"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  opacity="0.55"
                />
                <circle cx="16" cy="16" r="4" fill="currentColor" />
                <path
                  d="M16 2 L16 30 M2 16 L30 16"
                  stroke="currentColor"
                  strokeWidth="0.6"
                  opacity="0.35"
                />
              </svg>
            </span>
            <div>
              <div className="brand-name">Spillover</div>
              <div className="brand-sub">a rodent-borne outbreak model</div>
            </div>
          </div>
          <div className={`status-pill ${statusClass}`} id="status-pill">
            <span className="dot" />
            <span id="status-text">{statusMessage}</span>
          </div>
        </div>
      </header>

      <main className="page">
        <section className="hero">
          <div className="eyebrow">
            <span className="rule" />
            <span>Vol. 01 · forecast desk</span>
          </div>
          <h1 className="display">
            Where will the next
            <br />
            <em>hantavirus</em> outbreak surface?
          </h1>
          <p className="deck">
            A joint training across hantavirus, Lassa, and Ebola comparators,
            focused on US <span className="smallcaps">Sin Nombre</span>{" "}
            forecasts. Climate drivers, rodent ecology, and a decade of case
            history — distilled into one editable view.
          </p>
        </section>

        <section className="controls">
          <div className="control-group pathogen-control">
            <span className="control-label">Pathogen</span>
            <div className="select-wrap">
              <select
                id="virus-select"
                aria-label="Pathogen"
                value={virusSlug}
                onChange={(e) => setVirusSlug(e.target.value)}
              >
                {viruses.map((v) => (
                  <option key={v.virus_slug} value={v.virus_slug}>
                    {v.virus_name}
                  </option>
                ))}
              </select>
              <svg
                className="chev"
                viewBox="0 0 12 12"
                width="12"
                height="12"
                aria-hidden="true"
              >
                <path
                  d="M3 4.5 L6 7.5 L9 4.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>

          <div className="control-group view-control">
            <span className="control-label">View</span>
            <div className="segmented" id="view-segmented" role="tablist">
              {VIEWS.map((v) => {
                const disabled = v.needsModels && !modelsReady;
                return (
                  <button
                    key={v.id}
                    type="button"
                    role="tab"
                    data-view={v.id}
                    data-needs-models={v.needsModels ? true : undefined}
                    className={currentView === v.id ? "active" : ""}
                    disabled={disabled}
                    onClick={() => onViewChange(v.id)}
                  >
                    <span>{v.label}</span>
                    {v.needsModels ? (
                      <span className="lock" aria-hidden="true">
                        ·
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="control-group actions">
            <button
              id="refresh-btn"
              type="button"
              className="btn ghost"
              disabled={busy}
              onClick={refresh}
            >
              <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                <path
                  d="M2 8a6 6 0 0 1 10.5-4M14 8a6 6 0 0 1-10.5 4M12.5 2v3h-3M3.5 14v-3h3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Refresh</span>
            </button>
            <button
              id="train-btn"
              type="button"
              className="btn solid"
              title="Runs full pipeline — several minutes"
              disabled={busy}
              onClick={onTrain}
            >
              <span className="btn-glyph">▶</span>
              <span>Train models</span>
            </button>
          </div>
        </section>

        <p id="models-banner" className={bannerClass} role="status">
          {banner.message}
        </p>

        <KpiStrip items={viewState.kpis} />

        <section className="chart-card card">
          <div className="card-head">
            <div>
              <div className="card-eyebrow" id="chart-eyebrow">
                {viewState.eyebrow}
              </div>
              <h2 className="card-title" id="chart-title">
                {viewState.title}
              </h2>
            </div>
            <div
              className={`legend${viewState.showRiskLegend ? "" : " hidden"}`}
              id="risk-legend"
            >
              <span>
                <i style={{ background: "#4F7A5C" }} />
                baseline
              </span>
              <span>
                <i style={{ background: "#C68B3A" }} />
                moderate
              </span>
              <span>
                <i style={{ background: "#B5483A" }} />
                elevated
              </span>
            </div>
          </div>
          <MainChart
            key={`${currentView}-${virusSlug}`}
            chartConfig={viewState.chartConfig}
          />
        </section>

        <section className="card sources-card">
          <div className="card-head">
            <div>
              <div className="card-eyebrow">Appendix</div>
              <h2 className="card-title">Training data sources</h2>
            </div>
          </div>
          <ul id="virus-list" className="sources">
            {viruses.map((v) => (
              <li key={v.virus_slug}>
                <span className="name">{v.virus_name}</span>
                <span className="meta">
                  {v.records} geo-yrs · {fmt(v.total_cases)} cases
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="colophon">
        <div className="colophon-inner">
          <p className="set-italic">
            Not for clinical use. A research artefact — read{" "}
            <code>docs/PROJECT_GUIDE.md</code> before drawing conclusions.
          </p>
          <p className="folio">— №01 · forecast desk —</p>
        </div>
      </footer>
    </div>
  );
}
