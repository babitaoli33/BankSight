"""Safe execution of LLM-written SQL.

Three layers of defence:
1. `validate_sql` only accepts a single SELECT (or WITH ... SELECT) statement.
2. The database is opened read-only (`mode=ro`), so writes fail even if a check is missed.
3. Every query gets a row cap and a time limit.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import pandas as pd

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex|truncate)\b",
    re.IGNORECASE,
)


class SQLGuardError(ValueError):
    """Raised when a query is rejected before it reaches the database."""


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def validate_sql(sql: str) -> str:
    """Return a cleaned single SELECT statement, or raise SQLGuardError."""
    if not sql or not sql.strip():
        raise SQLGuardError("Empty query.")
    cleaned = _strip_comments(sql).strip().rstrip(";").strip()
    if ";" in cleaned:
        raise SQLGuardError("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise SQLGuardError("Only SELECT queries are allowed.")
    match = FORBIDDEN.search(cleaned)
    if match:
        raise SQLGuardError(f"Keyword '{match.group(1).upper()}' is not allowed.")
    return cleaned


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def run_readonly(db_path: str | Path, sql: str, max_rows: int = 200, timeout_s: float = 10.0) -> pd.DataFrame:
    """Validate and run a query on a read-only connection, capped by rows and time."""
    cleaned = validate_sql(sql)
    con = connect_readonly(db_path)
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        return pd.read_sql_query(f"SELECT * FROM ({cleaned}) LIMIT {int(max_rows)}", con)
    except (sqlite3.OperationalError, pd.errors.DatabaseError) as exc:
        if "interrupted" in str(exc).lower():
            raise TimeoutError(f"Query took longer than {timeout_s}s and was stopped.") from exc
        raise
    finally:
        con.close()


def describe_schema(db_path: str | Path, sample_rows: int = 10_000, max_values: int = 10) -> str:
    """Compact schema for the prompt: tables, columns, row counts and small value lists.

    Listing the few distinct values of short text columns (e.g. account_type) helps the
    model write correct WHERE clauses instead of guessing spellings.
    """
    con = connect_readonly(db_path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        lines = []
        for table in tables:
            count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            cols = []
            for _, name, col_type, *_ in con.execute(f'PRAGMA table_info("{table}")'):
                desc = f"{name} {col_type}".strip()
                if col_type.upper() in ("TEXT", "") and not name.endswith(("_id", "name", "date", "_at")):
                    values = [r[0] for r in con.execute(
                        f'SELECT DISTINCT "{name}" FROM (SELECT "{name}" FROM "{table}" LIMIT {sample_rows}) '
                        f"LIMIT {max_values + 1}"
                    )]
                    if 0 < len(values) <= max_values:
                        desc += " [values: " + ", ".join(map(str, values)) + "]"
                cols.append(desc)
            lines.append(f"{table} ({count:,} rows): " + ", ".join(cols))
        return "\n".join(lines)
    finally:
        con.close()
