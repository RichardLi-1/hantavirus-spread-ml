export function KpiStrip({ items }) {
  return (
    <section className="kpi-strip" id="kpi-strip" aria-label="Summary statistics">
      {items.map((it) => (
        <div key={it.label} className="kpi" data-tone={it.tone || undefined}>
          <div className="k">{it.label}</div>
          <div className={`v${it.mono ? " mono" : ""}`}>{it.value ?? "—"}</div>
          {it.sub ? <div className="sub">{it.sub}</div> : null}
        </div>
      ))}
    </section>
  );
}
