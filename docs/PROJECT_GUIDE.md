# What this project is

I built a small full-stack app that estimates **where and when rodent-borne outbreaks might tick up**, with **US Sin Nombre hantavirus (HPS)** as the main story but models trained on **other viruses’ histories** too. The point isn’t a clinical product — it’s an explorable pipeline: curated outbreak counts, weather features, gradient boosting, charts, and a deploy-anywhere Docker image.

---

## Stack (no Next/Vercel)

| Piece | Choice | Why |
|-------|--------|-----|
| API | FastAPI + Uvicorn | One process serves JSON + static files |
| UI | Vite + Chart.js | Lightweight, builds to `web/dist` |
| DB | SQLite (`data/app.db`) | Zero config; fine for demos and small deploys |
| ML | scikit-learn GBT | Interpretable, works on tabular climate + lag features |
| Ship | Docker Compose | Runs on Railway, Render, Fly, a $5 VPS, etc. |

---

## Training data — not just US hantavirus

The model learns from a **pooled panel** (`data/raw/multi_virus_historical.csv`):

**Hantaviruses (primary):**

- **Sin Nombre / HPS** — US national totals 1993–2023 (CDC), split to states using published regional weights (MacNeil, *Emerg Infect Dis* 2011).
- **Puumala (PUUV)** — Finland, Germany, Sweden annual lab-confirmed approximations from Eurosurveillance / ECDC annual reports (mast-year cycles in DE are real).
- **Andes virus** — Chile + Argentina Patagonia (PAHO / WHO DON style totals).
- **Seoul virus (HFRS)** — South Korea downward trend (KCDC summaries, rounded).
- **Dobrava-Belgrade** — Balkan HFRS (ECDC-style counts).

**Comparators (rodent / environmental emergence):**

- **Lassa** (Nigeria) — Arenaviridae, different ecology but similar “rain → rodent → human” narrative.
- **Ebola** (DRC epidemic years) — not rodent-driven; included so the model sees **large skewed counts** and doesn’t assume every pathogen scales like PUUV.

Each row is: virus × geography × year × cases, plus **Open-Meteo** monthly archive → annual precip/temp/winter/summer at that geo’s lat/lon.

---

## How training works

1. **Features** (`src/features.py`): lag-1/2 precipitation and temperature, 2-year precip mean, anomalies, case lags, one-hot virus ID, `is_hantavirus` flag.
2. **Target**: `log1p(cases)` in regression so Finland’s thousands and US tens can live in one model.
3. **Split**: last 5 years held out globally (all viruses).
4. **Reported metrics**:
   - MAE on all holdout rows
   - **Separate MAE on US Sin Nombre state rows** — the number you care about for the US dashboard

Literature alignment: precip lags matter for Sin Nombre (Engelthaler *BioScience* 2002; Glass Four Corners EID 1999) and PUUV (Nature Sci Reports 2023/2024 early-warning papers). The model won’t recover mechanistic vole dynamics; it’s a **statistical early-warning sketch**.

---

## Repo layout

```
hantavirus-spread-ml/
├── api/main.py          # REST + serves web/dist
├── web/                 # Vite frontend
├── src/
│   ├── multi_virus_data.py
│   ├── train.py
│   ├── predict.py
│   └── visualize.py
├── data/raw/            # CSV sources
├── data/processed/      # parquet panels, forecasts
├── models/              # joblib + metrics.json
├── scripts/run_pipeline.py
├── Dockerfile
└── docker-compose.yml
```

---

## Commands you’ll actually run

```bash
# rebuild data + models + sqlite sync
python scripts/run_pipeline.py

# API only
uvicorn api.main:app --reload

# production-ish
docker compose up --build
```

**Retrain from the UI**: POST `/api/retrain` (slow; hits Open-Meteo if climate cache is empty).

---

## API endpoints (for integrations)

- `GET /api/viruses` — list pathogens in DB  
- `GET /api/outbreaks?virus=puuv_fi` — raw rows  
- `GET /api/outbreaks/series/{virus_slug}` — time series  
- `GET /api/forecasts?virus=sin_nombre_us` — latest forecast  
- `GET /api/metrics` — holdout MAE, feature importance  
- `GET /api/climate/{geo_id}` — precip/temp series  

OpenAPI: `/docs`

---

## Deploy notes

1. **First boot**: run pipeline once so `multi_virus_panel.parquet` and models exist (Dockerfile tries at build; mount `data/` + `models/` volumes to persist).
2. **Climate cache**: stored under `data/raw/climate_cache_multi/` — delete to refetch.
3. **Port**: platform sets `$PORT`; use `uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}`.

---

## Honest limitations

- State-level US cases are **allocated** from national totals; CDC doesn’t publish county/state year files publicly.
- European and Andes counts are **rounded** from papers — good for ML structure, not surveillance.
- Lassa/Ebola help calibration but **must not** be interpreted as hantavirus predictors.
- No spatial spread network — independent geo-year rows.
- Fatality, seroprevalence, and rodent trapping data aren’t in the model.

---

## If you extend it

- Pull WHO DON HDX spreadsheet automatically instead of hand CSV.
- Add ONI / MEI index instead of winter-precip proxy.
- Separate heads per virus family instead of one pooled regressor.
- Replace SQLite with Postgres when you need multi-user writes.

---

## References (starting points)

- CDC Hantavirus case counts: https://www.cdc.gov/hantavirus/data-research/cases/index.html  
- MacNeil A et al. HPS US 1993–2009. *Emerg Infect Dis* 2011.  
- Engelthaler DM et al. El Niño and HPS. *BioScience* 2002.  
- Scientific Reports 2023 — ML early warning for PUUV in Germany.  
- ECDC annual hantavirus epidemiological reports (2017–2019).  
- Open-Meteo archive API: https://open-meteo.com/
