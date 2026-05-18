# Hantavirus spread ML (full stack)

Rodent-borne outbreak modeling with **multi-virus historical training** (Puumala, Andes, Seoul HFRS, plus Lassa/Ebola as climate-driven comparators), a **FastAPI** backend, and a **Vite** dashboard.

## Quick start (browse data)

Your shell may not have `python` / `pip` on PATH (pyenv not initialized). Use the project venv scripts instead of pasting comments into the terminal.

```bash
cd ~/dev/hantavirus-spread-ml
chmod +x scripts/setup.sh scripts/start.sh scripts/train.sh
./scripts/setup.sh
./scripts/start.sh
```

Open http://localhost:8000 — historical cases and climate views work immediately.

## Train models (forecasts + metrics)

`setup.sh` builds an offline data panel only. **Forecasts and model metrics need a one-time train:**

```bash
./scripts/train.sh
```

Uses the existing `data/processed/multi_virus_panel.*` (fast, no network). Writes `models/*.joblib`, forecast CSVs, and refreshes SQLite. Refresh the browser after it finishes.

**Full pipeline** (refetch Open-Meteo climate if cache is empty; network + disk):

```bash
.venv/bin/python scripts/run_pipeline.py
```

Or from the dashboard: **Train models** (POST `/api/retrain`, same as full pipeline).

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## Frontend dev (optional)

```bash
cd web && npm run dev
```

Production build (also run after UI changes if you use `./scripts/start.sh`):

```bash
cd web && npm install && npm run build
```

## If you want `python` / `pip` globally

Add to `~/.zshrc` (then `source ~/.zshrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null && eval "$(pyenv init -)"
```

Or always use explicit paths:

```bash
~/.pyenv/versions/3.11.9/bin/python3 -m venv .venv
source .venv/bin/activate
```

## Docker (Railway, Render, Fly, VPS)

```bash
docker compose up --build
```

## Deploy elsewhere

- **Railway / Render**: start command `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Fly.io**: `fly deploy` with the included Dockerfile

See `docs/PROJECT_GUIDE.md` for methodology and data sources.
