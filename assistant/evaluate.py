"""Execution-accuracy evaluation for the text-to-SQL step.

For each question, the generated SQL and a hand-written gold query are both run.
The answer counts as correct when they return the same values (column names and
row order are ignored, numbers rounded to 2 decimals). This is the standard way
text-to-SQL systems are scored, because many different queries can be correct.
"""

from __future__ import annotations

import json
from pathlib import Path

from .agent import BankSightAssistant
from .sql_guard import run_readonly


def _normalize(df) -> list[tuple]:
    rows = []
    for row in df.itertuples(index=False):
        rows.append(tuple(round(v, 2) if isinstance(v, float) else v for v in row))
    return sorted(rows, key=lambda r: tuple(str(v) for v in r))


def run_eval(assistant: BankSightAssistant, eval_path: str | Path) -> dict:
    cases = [json.loads(line) for line in Path(eval_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for case in cases:
        answer = assistant.ask(case["question"])
        gold = run_readonly(assistant.db_path, case["gold_sql"])
        correct = answer.result is not None and _normalize(answer.result) == _normalize(gold)
        results.append({
            "question": case["question"],
            "correct": correct,
            "attempts": answer.attempts,
            "error": answer.error,
            "tokens": answer.total_tokens,
            "sql": answer.sql,
        })
    n = len(results)
    return {
        "summary": {
            "questions": n,
            "execution_accuracy": round(sum(r["correct"] for r in results) / n, 3),
            "needed_retry": sum(r["attempts"] > 1 for r in results),
            "mean_tokens": round(sum(r["tokens"] for r in results) / n, 1),
        },
        "results": results,
    }
