"""Ask BankSight: plain-English questions -> retrieved context -> SQL -> grounded answer.

    question
      ├─ retrieve similar SQL examples + relevant findings   (RAG)
      ├─ LLM writes one SELECT (or decides no SQL is needed)
      ├─ guard + run read-only; on error, send the error back once to self-correct
      └─ LLM answers from the result table and findings, with citations
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import prompts
from .knowledge import KnowledgeBase
from .sql_guard import SQLGuardError, describe_schema, run_readonly

MAX_RESULT_ROWS_IN_PROMPT = 20


@dataclass
class AssistantAnswer:
    question: str
    text: str
    sql: str | None = None
    result: pd.DataFrame | None = None
    sources: list[str] = field(default_factory=list)
    attempts: int = 0
    error: str | None = None
    usage: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return sum(u["input"] + u["output"] for u in self.usage.values())


def parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start : end + 1])


class BankSightAssistant:
    def __init__(self, llm, db_path: str | Path, repo_root: str | Path, max_attempts: int = 2):
        self.llm = llm
        self.db_path = Path(db_path)
        self.kb = KnowledgeBase(repo_root)
        self.schema = describe_schema(self.db_path)  # read once; it does not change between questions
        self.max_attempts = max_attempts

    def _track(self, usage: dict, step: str, resp) -> None:
        entry = usage.setdefault(step, {"calls": 0, "input": 0, "output": 0})
        entry["calls"] += 1
        entry["input"] += resp.input_tokens
        entry["output"] += resp.output_tokens

    def ask(self, question: str) -> AssistantAnswer:
        usage: dict[str, dict[str, int]] = {}
        examples = self.kb.search(question, kind="sql", k=3)
        findings = self.kb.search(question, kind="finding", k=2)

        sql, result, error, attempts = None, None, None, 0
        failed_sql = None
        while attempts < self.max_attempts:
            attempts += 1
            resp = self.llm.complete(
                prompts.SQL_SYSTEM,
                prompts.sql_prompt(question, self.schema, examples, error, failed_sql),
                max_tokens=500,
            )
            self._track(usage, "sql", resp)
            try:
                plan = parse_json(resp.text)
            except (ValueError, json.JSONDecodeError) as exc:
                error, failed_sql = f"Reply was not valid JSON: {exc}", resp.text[:500]
                continue
            if not plan.get("needs_sql"):
                sql, error = None, None
                break
            sql = str(plan.get("sql", ""))
            try:
                result = run_readonly(self.db_path, sql)
                error = None
                break
            except (SQLGuardError, sqlite3.Error, pd.errors.DatabaseError, TimeoutError) as exc:
                error, failed_sql, result = str(exc), sql, None

        result_csv = (
            result.head(MAX_RESULT_ROWS_IN_PROMPT).to_csv(index=False) if result is not None else None
        )
        resp = self.llm.complete(
            prompts.ANSWER_SYSTEM,
            prompts.answer_prompt(question, sql, result_csv, 0 if result is None else len(result), findings, error),
            max_tokens=400,
        )
        self._track(usage, "answer", resp)

        sources = [f.id for f in findings] + [e.id for e in examples]
        return AssistantAnswer(question, resp.text.strip(), sql, result, sources, attempts, error, usage)
