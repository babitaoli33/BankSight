"""Command line interface for Ask BankSight.

    python -m assistant ask "Which merchants bring in the most transaction value?" --show-sql
    python -m assistant ask "Why should the bank care about product count?" --provider anthropic
    python -m assistant eval --provider anthropic
"""

from __future__ import annotations

import argparse
import json

from . import REAL_DB, REPO_ROOT, BankSightAssistant, get_llm
from .sample_db import DEFAULT_PATH, build_sample_db


def main() -> None:
    parser = argparse.ArgumentParser(prog="assistant", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="mock", choices=["mock", "anthropic", "openai"])
    parser.add_argument("--model", default=None, help="model name (or set BANKSIGHT_MODEL)")
    parser.add_argument("--db", default=None,
                        help="SQLite database (default: the Kaggle DB if present, else the generated sample)")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--show-sql", action="store_true", help="print the SQL, retries and token usage")
    ev = sub.add_parser("eval", help="run the execution-accuracy evaluation")
    ev.add_argument("--eval-set", default=str(REPO_ROOT / "assistant" / "eval_questions.jsonl"))
    args = parser.parse_args()

    db = args.db
    if db is None:
        if REAL_DB.exists():
            db = REAL_DB
        else:
            db = DEFAULT_PATH if DEFAULT_PATH.exists() else build_sample_db()
            print(f"(Using the generated sample database: {db})\n")

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
