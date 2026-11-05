"""Ask BankSight: a retrieval-augmented text-to-SQL assistant for the BankSight dataset."""

from pathlib import Path

from .agent import AssistantAnswer, BankSightAssistant
from .llm import get_llm

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / "data" / "raw" / "banking_dataset_kaggle" / "data" / "database" / "bank_sqlite.db"

__all__ = ["AssistantAnswer", "BankSightAssistant", "get_llm", "REPO_ROOT", "REAL_DB"]
