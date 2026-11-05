"""LLM clients behind one `complete(system, prompt)` interface: Anthropic, OpenAI, or an offline mock."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or os.getenv("BANKSIGHT_MODEL", "claude-sonnet-5-5")

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> LLMResponse:
        resp = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(text, resp.usage.input_tokens, resp.usage.output_tokens)


class OpenAILLM:
    name = "openai"

    def __init__(self, model: str | None = None):
        import openai

        self.client = openai.OpenAI()  # reads OPENAI_API_KEY
        self.model = model or os.getenv("BANKSIGHT_MODEL", "gpt-4o-mini")

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> LLMResponse:
        resp = self.client.chat.completions.create(
            model=self.model, max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        u = resp.usage
        return LLMResponse(resp.choices[0].message.content or "", u.prompt_tokens if u else 0,
                           u.completion_tokens if u else 0)


class MockLLM:
    """Offline stand-in used by tests and CI.

    For SQL it reuses the best retrieved example (so it shows the RAG step working);
    for answers it fills a template from the query result and the top finding.
    """

    name = "mock"
    DOCS_ONLY_WORDS = ("why", "recommend", "should", "meaning", "finding", "explain", "trust", "reliable")

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> LLMResponse:
        if "ROLE: sql" in system:
            text = self._sql(prompt)
        elif "ROLE: answer" in system:
            text = self._answer(prompt)
        else:
            text = "I don't know."
        return LLMResponse(text, estimate_tokens(system + prompt), estimate_tokens(text))

    def _sql(self, prompt: str) -> str:
        question = re.search(r"^Question:\s*(.*)$", prompt, re.MULTILINE).group(1).lower()
        examples = re.findall(r"^SQL:\n(.*?)(?=\n\n|\Z)", prompt, re.MULTILINE | re.DOTALL)
        if any(w in question for w in self.DOCS_ONLY_WORDS) or not examples:
            return json.dumps({"needs_sql": False, "sql": ""})
        index = 1 if "ERROR:" in prompt and len(examples) > 1 else 0
        return json.dumps({"needs_sql": True, "sql": examples[index].strip()})

    def _answer(self, prompt: str) -> str:
        parts = []
        table = re.search(r"RESULT \((\d+) rows?\):\n(.*?)(?=\n\nFINDINGS:|\Z)", prompt, re.DOTALL)
        if table:
            rows = table.group(2).strip().splitlines()
            parts.append(f"The query returned {table.group(1)} rows. Top results:\n" + "\n".join(rows[:6]) + " [query]")
        finding = re.search(r"\[(finding-\d+|[a-z-]+)\] ([^\n]+)", prompt.split("FINDINGS:", 1)[-1])
        if finding:
            sentences = re.split(r"(?<=[.!?])\s", finding.group(2))
            summary = " ".join(sentences[:2])
            parts.append(f"Related finding: {summary} [{finding.group(1)}]")
        return "\n\n".join(parts) or "I could not find enough information to answer."


def get_llm(provider: str = "mock", model: str | None = None):
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicLLM(model)
    if provider == "openai":
        return OpenAILLM(model)
    if provider == "mock":
        return MockLLM()
    raise ValueError(f"Unknown provider '{provider}'. Use mock, anthropic or openai.")
