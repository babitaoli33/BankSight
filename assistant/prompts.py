"""Prompts for the two LLM steps: writing SQL, then answering from the result."""

SQL_SYSTEM = """ROLE: sql
You are a careful SQLite analyst for a retail banking database.
Decide whether the question needs data from the database. Reply with ONLY JSON:
{"needs_sql": true, "sql": "<one SQLite SELECT statement>"}
or {"needs_sql": false, "sql": ""} when the question is about meaning, recommendations or the written findings.
Rules:
- One SELECT (or WITH ... SELECT) statement. Never modify data.
- Use only tables and columns from the schema. Follow the style of the example queries.
- Aggregate instead of returning raw rows when the question asks for totals, trends or rankings.
- Round money to 2 decimals. Add ORDER BY and LIMIT for rankings."""

ANSWER_SYSTEM = """ROLE: answer
You answer a bank analyst's question using ONLY the query result and the findings provided.
- Lead with the direct answer, using exact numbers from the result. Do not invent numbers.
- Cite the query result as [query] and findings by id, e.g. [finding-2].
- If the query failed or returned nothing, say so plainly.
- The dataset is synthetic: do not present results as real-world banking facts.
- At most 120 words."""


def sql_prompt(question: str, schema: str, examples, error: str | None = None, failed_sql: str | None = None) -> str:
    shots = "\n\n".join(f"Example question: {e.title}\nSQL:\n{e.sql}" for e in examples)
    retry = f"\n\nYour previous query failed.\nSQL:\n{failed_sql}\nERROR: {error}\nWrite a corrected query." if error else ""
    return f"SCHEMA:\n{schema}\n\nEXAMPLES:\n{shots}\n\nQuestion: {question}{retry}"


def answer_prompt(question: str, sql: str | None, result_csv: str | None, n_rows: int,
                  findings, error: str | None = None) -> str:
    parts = [f"Question: {question}"]
    if sql:
        parts.append(f"SQL USED:\n{sql}")
    if error:
        parts.append(f"QUERY ERROR: {error}")
    elif result_csv is not None:
        parts.append(f"RESULT ({n_rows} rows):\n{result_csv}")
    parts.append("FINDINGS:\n" + "\n".join(f"[{f.id}] {f.text[:700]}" for f in findings))
    return "\n\n".join(parts)
