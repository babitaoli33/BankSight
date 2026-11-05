"""FastAPI service exposing the three assistants over HTTP.

    uvicorn assistant.api:create_app --factory --reload     # then open http://127.0.0.1:8000/docs

Configuration (environment variables):
    BANKSIGHT_PROVIDER    mock | anthropic | openai     (default: mock)
    BANKSIGHT_EMBEDDINGS  hashing | fastembed | openai  (default: hashing)
    BANKSIGHT_DB          path to a SQLite database     (default: Kaggle DB if present, else the sample DB)
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import REAL_DB, REPO_ROOT, BankSightAssistant, get_llm
from .docs_rag import DocsQA, build_vectorstore
from .models import get_chat_model, get_embeddings
from .sample_db import DEFAULT_PATH, build_sample_db
from .sql_agent import RetrievalToolChooser, SQLToolAgent, build_tools


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500, examples=["Which merchants bring in the most transaction value?"])


def default_db() -> Path:
    if os.getenv("BANKSIGHT_DB"):
        return Path(os.environ["BANKSIGHT_DB"])
    if REAL_DB.exists():
        return REAL_DB
    return DEFAULT_PATH if DEFAULT_PATH.exists() else build_sample_db()


def create_app(provider: str | None = None, embeddings: str | None = None, db_path: str | Path | None = None) -> FastAPI:
    provider = provider or os.getenv("BANKSIGHT_PROVIDER", "mock")
    embeddings = embeddings or os.getenv("BANKSIGHT_EMBEDDINGS", "hashing")
    db = Path(db_path) if db_path else default_db()

    sql_assistant = BankSightAssistant(get_llm(provider), db, REPO_ROOT)
    chat = get_chat_model(provider)
    docs_qa = DocsQA(build_vectorstore(REPO_ROOT, get_embeddings(embeddings)), chat)
    agent = SQLToolAgent(chat if chat is not None else RetrievalToolChooser(), build_tools(REPO_ROOT, db))

    app = FastAPI(title="BankSight Assistant API", version="1.0",
                  description="Text-to-SQL, document RAG and a tool-calling agent over the BankSight dataset.")

    @app.get("/health")
    def health():
        return {"status": "ok", "provider": provider, "embeddings": embeddings, "database": db.name}

    @app.post("/ask")
    def ask(body: Question):
        """Text-to-SQL: retrieve example queries, let the model write SQL, run it read-only."""
        answer = sql_assistant.ask(body.question)
        rows = answer.result.head(20).to_dict(orient="records") if answer.result is not None else []
        return {"answer": answer.text, "sql": answer.sql, "rows": rows, "error": answer.error,
                "attempts": answer.attempts, "sources": answer.sources}

    @app.post("/docs/ask")
    def docs_ask(body: Question):
        """RAG over the project documents (LangChain + Chroma)."""
        answer = docs_qa.ask(body.question)
        return {"answer": answer.text, "sources": answer.sources}

    @app.post("/agent/ask")
    def agent_ask(body: Question):
        """Tool-calling agent that picks among the predefined SQL queries."""
        try:
            answer = agent.ask(body.question)
        except Exception as exc:  # surface model/API failures as a clean 502
            raise HTTPException(status_code=502, detail=f"Agent failed: {exc}") from exc
        return {"answer": answer.text, "tools_used": answer.tools_used, "steps": answer.steps}

    return app

