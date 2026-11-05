"""The retrieval part of the assistant.

Two kinds of documents come from this repo itself:
- findings: sections of reports/FINDINGS.md (the business story and recommendations)
- sql examples: each business question + query pair in sql/queries.sql

Similar SQL examples are retrieved and shown to the model as few-shot examples,
which makes the generated SQL follow this dataset's real table and column names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOKEN_RE = re.compile(r"[a-z0-9]+")  # splits snake_case columns: total_balance -> total, balance


def _stem(word: str) -> str:
    """Light suffix stripping so 'merchants' matches 'merchant' and 'monthly' matches 'month'."""
    if any(ch.isdigit() for ch in word) or len(word) <= 4:
        return word
    for suffix in ("ing", "ly", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in ENGLISH_STOP_WORDS]


@dataclass
class Doc:
    id: str
    kind: str      # "finding" or "sql"
    title: str
    text: str
    sql: str = ""
    score: float = 0.0


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_findings(path: Path) -> list[Doc]:
    docs = []
    for section in re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.MULTILINE)[1:]:
        title, _, body = section.partition("\n")
        body = re.sub(r"\n-{3,}\s*$", "", body.strip())
        number = re.match(r"Finding (\d+)", title)
        doc_id = f"finding-{number.group(1)}" if number else _slug(title)
        docs.append(Doc(doc_id, "finding", title.strip(), f"{title.strip()}. {body}"))
    return docs


def load_sql_examples(path: Path) -> list[Doc]:
    """Pair each SQL statement with the closest preceding '-- Business question:' comment."""
    docs, question, buffer = [], None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        q = re.match(r"--\s*Business question:\s*(.+)", stripped, re.IGNORECASE)
        if q:
            question = q.group(1).strip()
            continue
        if stripped.startswith("--") and not buffer:
            continue
        if stripped or buffer:
            buffer.append(line)
        if stripped.endswith(";"):
            sql = "\n".join(buffer).strip()
            buffer = []
            if question:
                docs.append(Doc(f"sql-{len(docs) + 1}", "sql", question, f"{question}\n{sql}", sql=sql))
    return docs


class KnowledgeBase:
    def __init__(self, repo_root: str | Path):
        root = Path(repo_root)
        self.docs = load_findings(root / "reports" / "FINDINGS.md") + load_sql_examples(root / "sql" / "queries.sql")
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(d.text for d in self.docs)

    def search(self, query: str, kind: str, k: int = 3, min_score: float = 0.03) -> list[Doc]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = sorted(
            (i for i, d in enumerate(self.docs) if d.kind == kind), key=lambda i: scores[i], reverse=True
        )
        out = []
        for i in ranked[:k]:
            if scores[i] < min_score:
                break
            d = self.docs[i]
            out.append(Doc(d.id, d.kind, d.title, d.text, d.sql, float(scores[i])))
        return out
