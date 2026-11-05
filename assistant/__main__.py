"""Command line interface for Ask BankSight.

Text-to-SQL (the model writes SQL, run read-only):
    python -m assistant ask "Which merchants bring in the most transaction value?" --show-sql
    python -m assistant eval --provider anthropic

RAG over the project documents (LangChain + ChromaDB):
    python -m assistant index --embeddings fastembed
    python -m assistant docs "What did the analysis find about cross-selling?" --embeddings fastembed

Tool-calling agent over the predefined SQL queries:
    python -m assistant agent "Which account type holds the most balance?" --provider anthropic

HTTP API:
    uvicorn assistant.api:create_app --factory
"""

from __future__ import annotations

import argparse
import json
import os

from . import REAL_DB, REPO_ROOT, BankSightAssistant, get_llm
from .sample_db import DEFAULT_PATH, build_sample_db

INDEX_DIR = REPO_ROOT / "data" / "chroma"


def resolve_db(arg: str | None):
    if arg:
        return arg
    if REAL_DB.exists():
        return REAL_DB
    db = DEFAULT_PATH if DEFAULT_PATH.exists() else build_sample_db()
    print(f"(Using the generated sample database: {db})\n")
    return db


def main() -> None:
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")  # keep Chroma from sending usage telemetry
    parser = argparse.ArgumentParser(prog="assistant", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="mock", choices=["mock", "anthropic", "openai"])
    parser.add_argument("--model", default=None, help="model name (or set BANKSIGHT_MODEL)")
    parser.add_argument("--db", default=None,
                        help="SQLite database (default: the Kaggle DB if present, else the generated sample)")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="text-to-SQL: answer one question from the database")
    ask.add_argument("question")
    ask.add_argument("--show-sql", action="store_true", help="print the SQL, retries and token usage")

    ev = sub.add_parser("eval", help="run the execution-accuracy evaluation")
    ev.add_argument("--eval-set", default=str(REPO_ROOT / "assistant" / "eval_questions.jsonl"))

    for name, helptext in (("index", "build the Chroma index of the project documents"),
                           ("docs", "RAG: answer a question from the project documents")):
        p = sub.add_parser(name, help=helptext)
        if name == "docs":
            p.add_argument("question")
        p.add_argument("--embeddings", default="fastembed", choices=["fastembed", "openai", "hashing"])

    agent = sub.add_parser("agent", help="tool-calling agent that picks a predefined SQL query")
    agent.add_argument("question")
    args = parser.parse_args()

    if args.command in ("index", "docs"):
        from .docs_rag import DocsQA, build_vectorstore, load_vectorstore
        from .models import get_chat_model, get_embeddings

        embeddings = get_embeddings(args.embeddings)
        marker = INDEX_DIR / "embeddings.txt"
        if args.command == "index" or not marker.exists() or marker.read_text() != args.embeddings:
            store = build_vectorstore(REPO_ROOT, embeddings, INDEX_DIR)
            marker.write_text(args.embeddings)
            print(f"Indexed {store._collection.count()} chunks into {INDEX_DIR} using {args.embeddings} embeddings.")
        if args.command == "index":
            return
        answer = DocsQA(load_vectorstore(INDEX_DIR, embeddings), get_chat_model(args.provider, args.model)).ask(args.question)
        print(answer.text)
        print(f"\nsources: {', '.join(answer.sources)}")
        return

    db = resolve_db(args.db)

    if args.command == "agent":
        from .models import get_chat_model
        from .sql_agent import RetrievalToolChooser, SQLToolAgent, build_tools

        chat = get_chat_model(args.provider, args.model) or RetrievalToolChooser()
        result = SQLToolAgent(chat, build_tools(REPO_ROOT, db)).ask(args.question)
        print(result.text)
        print(f"\ntools used: {', '.join(result.tools_used) or 'none'} | steps: {result.steps}")
        return

    assistant = BankSightAssistant(get_llm(args.provider, args.model), db, REPO_ROOT)
    if args.command == "ask":
        answer = assistant.ask(args.question)
        print(answer.text)
        if args.show_sql:
            print("\n--- SQL ---")
            print(answer.sql or "(no SQL needed)")
            if answer.error:
                print(f"error: {answer.error}")
            print(f"attempts: {answer.attempts} | sources: {', '.join(answer.sources)}")
            for step, u in answer.usage.items():
                print(f"{step:<7} calls={u['calls']} input={u['input']} output={u['output']}")
    else:
        from .evaluate import run_eval

        report = run_eval(assistant, args.eval_set)
        for r in report["results"]:
            print(f"[{'ok ' if r['correct'] else 'BAD'}] attempts={r['attempts']} tokens={r['tokens']:>5}  {r['question']}")
        print("\nSummary:", json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
