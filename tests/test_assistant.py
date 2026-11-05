import json
import sqlite3

import pytest

from assistant import REPO_ROOT, BankSightAssistant
from assistant.evaluate import run_eval
from assistant.knowledge import KnowledgeBase
from assistant.llm import LLMResponse, MockLLM
from assistant.sample_db import build_sample_db
from assistant.sql_guard import SQLGuardError, describe_schema, run_readonly, validate_sql


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    return build_sample_db(tmp_path_factory.mktemp("db") / "bank.db")


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(REPO_ROOT)


class ScriptedLLM:
    """Replays a fixed list of replies, one per call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def complete(self, system, prompt, max_tokens=800):
        self.prompts.append(prompt)
        return LLMResponse(self.replies.pop(0), 10, 10)


# --- SQL guard -----------------------------------------------------------------
@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",
    "select count(*) from accounts;",
    "WITH t AS (SELECT 1 AS x) SELECT x FROM t",
    "-- comment\nSELECT REPLACE(card_type, 'a', 'b') FROM cards",
])
def test_guard_accepts_read_queries(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", [
    "DROP TABLE customers",
    "SELECT 1; DELETE FROM accounts",
    "UPDATE accounts SET balance_usd = 0",
    "PRAGMA table_info(customers)",
    "SELECT * FROM customers /* sneaky */; DROP TABLE loans",
    "ATTACH DATABASE 'x.db' AS x",
    "",
])
def test_guard_rejects_unsafe_queries(sql):
    with pytest.raises(SQLGuardError):
        validate_sql(sql)


def test_connection_is_read_only_even_if_guard_is_bypassed(db):
    from assistant.sql_guard import connect_readonly

    con = connect_readonly(db)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM customers")
    con.close()


def test_row_cap_is_applied(db):
    assert len(run_readonly(db, "SELECT * FROM transactions", max_rows=25)) == 25


def test_schema_lists_tables_and_small_value_sets(db):
    schema = describe_schema(db)
    assert "transactions (3,000 rows)" in schema
    assert "account_type TEXT [values:" in schema
    assert "merchant_name" in schema and "[values: FreshMart" not in schema  # names are not enumerated


# --- retrieval -------------------------------------------------------------------
def test_sql_examples_are_paired_with_business_questions(kb):
    examples = [d for d in kb.docs if d.kind == "sql"]
    assert len(examples) >= 8
    assert all(d.sql.rstrip().endswith(";") for d in examples)


@pytest.mark.parametrize("question, expected_table", [
    ("top merchants by transaction value", "merchants"),
    ("card product mix", "cards"),
    ("monthly transaction trend", "strftime"),
])
def test_retrieves_relevant_sql_example(kb, question, expected_table):
    assert expected_table in kb.search(question, kind="sql", k=1)[0].sql


def test_retrieves_relevant_finding(kb):
    assert kb.search("do customers hold many products? cross-sell", kind="finding", k=1)[0].id == "finding-2"


# --- agent -----------------------------------------------------------------------
def test_end_to_end_with_mock(db):
    answer = BankSightAssistant(MockLLM(), db, REPO_ROOT).ask("What is the card product mix?")
    assert answer.error is None and answer.attempts == 1
    assert set(answer.result.columns) == {"card_type", "num_cards"}
    assert "[query]" in answer.text


def test_docs_only_question_skips_sql(db):
    answer = BankSightAssistant(MockLLM(), db, REPO_ROOT).ask("Why does it matter that customers hold few products?")
    assert answer.sql is None and answer.result is None
    assert "finding-2" in answer.text


def test_self_corrects_after_sql_error(db):
    llm = ScriptedLLM([
        json.dumps({"needs_sql": True, "sql": "SELECT card_kind FROM cards"}),  # wrong column
        json.dumps({"needs_sql": True, "sql": "SELECT card_type, COUNT(*) AS n FROM cards GROUP BY card_type"}),
        "Debit cards lead. [query]",
    ])
    answer = BankSightAssistant(llm, db, REPO_ROOT).ask("card mix?")
    assert answer.attempts == 2 and answer.error is None
    assert "no such column" in llm.prompts[1]  # the error was fed back to the model


def test_blocks_destructive_sql_from_model(db):
    llm = ScriptedLLM([
        json.dumps({"needs_sql": True, "sql": "DELETE FROM customers"}),
        json.dumps({"needs_sql": True, "sql": "DROP TABLE customers"}),
        "I could not run a safe query.",
    ])
    answer = BankSightAssistant(llm, db, REPO_ROOT).ask("remove all customers")
    assert answer.result is None and "allowed" in answer.error
    assert run_readonly(db, "SELECT COUNT(*) AS n FROM customers")["n"][0] == 200


def test_eval_runs(db):
    report = run_eval(BankSightAssistant(MockLLM(), db, REPO_ROOT), REPO_ROOT / "assistant" / "eval_questions.jsonl")
    assert report["summary"]["questions"] == 6
    assert report["summary"]["execution_accuracy"] >= 0.5
