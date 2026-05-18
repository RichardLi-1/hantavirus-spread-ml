# Hantavirus spread ML (full stack)

Rodent-borne outbreak modeling with **multi-virus historical training** (Puumala, Andes, Seoul HFRS, plus Lassa/Ebola as climate-driven comparators), a **FastAPI** backend, and a **Vite** dashboard.

## Quick start (local)

Your shell may not have `python` / `pip` on PATH (pyenv not initialized). Use the project venv scripts instead of pasting comments into the terminal.

```bash
cd ~/dev/hantavirus-spread-ml
chmod +x scripts/setup.sh scripts/start.sh
./scripts/setup.sh
./scripts/start.sh
```

Then open http://localhost:8000

Optional full retrain with live weather (network + ~500MB disk):

```bash
cd ~/dev/hantavirus-spread-ml
.venv/bin/python scripts/run_pipeline.py
```

Frontend only (already built if you ran `npm run build` in `web/`):

```bash
cd web && npm run dev
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
