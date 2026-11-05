"""A tool-calling agent that chooses among the project's predefined SQL queries.

Each business question in sql/queries.sql becomes a LangChain tool. The model sees the
tool names and descriptions, decides which one(s) to call, the tool runs its fixed query
read-only, and the model answers from the returned rows. Because the SQL is predefined,
the model can never write or change a query here; it can only pick one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import StructuredTool
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .knowledge import load_sql_examples, tokenize
from .sql_guard import run_readonly

SYSTEM = (
    "You are an analyst for the BankSight banking dataset (synthetic data). Each tool runs one predefined, "
    "read-only SQL query and returns CSV rows. Call the tool(s) that answer the question, then answer briefly "
    "using exact numbers from the results. If no tool fits, say so instead of guessing."
)
MAX_ROWS = 20


def _tool_name(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return ("q_" + slug)[:60]


def _runner(db_path: str | Path, sql: str):
    """A zero-argument function, so the tool schema the model sees has no parameters it could misuse."""
    def run() -> str:
        df = run_readonly(db_path, sql, max_rows=MAX_ROWS)
        return df.to_csv(index=False) if len(df) else "(no rows)"
    return run


def build_tools(repo_root: str | Path, db_path: str | Path) -> list[StructuredTool]:
    tools, seen = [], set()
    for example in load_sql_examples(Path(repo_root) / "sql" / "queries.sql"):
        name = _tool_name(example.title)
        if name in seen:
            continue
        seen.add(name)
        tools.append(StructuredTool.from_function(func=_runner(db_path, example.sql), name=name,
                                                  description=example.title))
    return tools


@dataclass
class AgentAnswer:
    question: str
    text: str
    tools_used: list[str] = field(default_factory=list)
    steps: int = 0


class SQLToolAgent:
    def __init__(self, chat_model: BaseChatModel, tools: list[StructuredTool], max_steps: int = 3):
        self.tools = {t.name: t for t in tools}
        self.model = chat_model.bind_tools(tools)
        self.max_steps = max_steps

    def ask(self, question: str) -> AgentAnswer:
        messages: list = [SystemMessage(SYSTEM), HumanMessage(question)]
        used: list[str] = []
        for step in range(1, self.max_steps + 1):
            reply = self.model.invoke(messages)
            messages.append(reply)
            if not reply.tool_calls:
                return AgentAnswer(question, _text(reply), used, step)
            for call in reply.tool_calls:
                tool = self.tools.get(call["name"])
                if tool is None:
                    result = f"Error: there is no tool named {call['name']}."
                else:
                    used.append(call["name"])
                    # Predefined queries take no arguments, so whatever the model sent is ignored
                    result = tool.invoke({})
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))
        return AgentAnswer(question, "Stopped after the maximum number of steps without a final answer.", used, self.max_steps)


def _text(message: AIMessage) -> str:
    if isinstance(message.content, str):
        return message.content.strip()
    return " ".join(part.get("text", "") for part in message.content if isinstance(part, dict)).strip()


class RetrievalToolChooser(BaseChatModel):
    """Offline stand-in for a tool-calling LLM.

    First turn: calls the tool whose description best matches the question (TF-IDF).
    After a tool result: summarizes the first rows. Lets the agent loop run with no API key.
    """

    bound_tools: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "retrieval-tool-chooser"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"bound_tools": list(tools)})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            rows = [line for line in str(last.content).splitlines() if line.strip()]
            summary = f"The query returned {max(len(rows) - 1, 0)} rows. Top rows:\n" + "\n".join(rows[:6])
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=summary))])

        question = next(m.content for m in reversed(messages) if isinstance(m, HumanMessage))
        names = [t.name for t in self.bound_tools]
        descriptions = [t.description for t in self.bound_tools]
        vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False)
        matrix = vectorizer.fit_transform(descriptions + [question])
        scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
        best = int(scores.argmax()) if len(scores) else -1
        if best < 0 or scores[best] < 0.1:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(
                content="None of the predefined queries answers that question."))])
        call = {"name": names[best], "args": {}, "id": "call_1", "type": "tool_call"}
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[call]))])
