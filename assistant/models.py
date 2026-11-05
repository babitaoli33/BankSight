"""LangChain chat models and embeddings, chosen by name so the same code runs online or offline.

Chat models:  anthropic | openai | mock (offline stand-ins defined next to the code that uses them)
Embeddings:   fastembed (local, free) | openai | hashing (offline, used by tests and CI)
"""

from __future__ import annotations

import os

import numpy as np
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import HashingVectorizer


def get_chat_model(provider: str, model: str | None = None):
    """Return a LangChain chat model, or None for the offline mock (callers supply their own stand-in)."""
    provider = provider.lower()
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model or os.getenv("BANKSIGHT_MODEL", "claude-sonnet-5-5"), max_tokens=700, temperature=0)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model or os.getenv("BANKSIGHT_MODEL", "gpt-4o-mini"), temperature=0)
    if provider == "mock":
        return None
    raise ValueError(f"Unknown provider '{provider}'. Use mock, anthropic or openai.")


class HashingEmbeddings(Embeddings):
    """Deterministic bag-of-words embeddings (no model download, no API key).

    Good enough for tests and offline demos; use fastembed or openai for real semantic search.
    """

    def __init__(self, n_features: int = 1024):
        self.vectorizer = HashingVectorizer(
            n_features=n_features, stop_words="english", alternate_sign=False, norm="l2", ngram_range=(1, 2)
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        matrix = self.vectorizer.transform(texts).toarray().astype(np.float32)
        return matrix.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


def get_embeddings(name: str = "fastembed") -> Embeddings:
    name = name.lower()
    if name == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")  # ~130MB, downloaded once, runs on CPU
    if name == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")
    if name == "hashing":
        return HashingEmbeddings()
    raise ValueError(f"Unknown embeddings '{name}'. Use fastembed, openai or hashing.")
