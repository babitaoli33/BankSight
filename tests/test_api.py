"""FastAPI endpoints, run fully offline (mock model, hashing embeddings, sample database)."""

import pytest
from fastapi.testclient import TestClient

from assistant.api import create_app
from assistant.sample_db import build_sample_db


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db = build_sample_db(tmp_path_factory.mktemp("db") / "bank.db")
    return TestClient(create_app(provider="mock", embeddings="hashing", db_path=db))


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["provider"] == "mock"


def test_text_to_sql_endpoint(client):
    body = client.post("/ask", json={"question": "What is our card product mix?"}).json()
    assert body["error"] is None and "card_type" in body["sql"]
    assert body["rows"] and "card_type" in body["rows"][0]


def test_docs_endpoint_returns_cited_sources(client):
    body = client.post("/docs/ask", json={"question": "What did the analysis find about cross-selling?"}).json()
    assert body["sources"] and body["answer"]


def test_agent_endpoint(client):
    body = client.post("/agent/ask", json={"question": "Which merchants bring in the most transaction value?"}).json()
    assert body["tools_used"] and "merchant" in body["tools_used"][0]


def test_rejects_empty_question(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
