"""API smoke tests (no network)."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import database as db
from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_models_status_not_ready_before_train(client):
    r = client.get("/api/models/status")
    assert r.status_code == 200
    body = r.json()
    assert "ready" in body
    assert "has_metrics" in body


def test_outbreak_series_year_is_integer(client):
    r = client.get("/api/outbreaks/series/andes_ar")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row["year"], int)
        assert isinstance(row["cases"], (int, float))


def test_sync_stores_integer_years(tmp_path, monkeypatch):
    db_path = tmp_path / "sync.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.sync_from_files()
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT typeof(year), year FROM outbreaks WHERE virus_slug='andes_ar' LIMIT 1"
    ).fetchone()
    conn.close()
    assert row[0] == "integer"
    assert row[1] == 1996
