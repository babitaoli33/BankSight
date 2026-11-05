"""RAG over the project's own unstructured documents with LangChain + ChromaDB.

    README, findings report, notebook narrative
        -> split into overlapping chunks
        -> embed each chunk -> store in a Chroma vector store
    question -> embed -> retrieve top-k chunks -> LLM answers from them, citing chunk ids

Answers questions like "What did the analysis find about cross-selling?" or
"How were customers segmented?" from what the project actually wrote down.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOC_SOURCES = ["README.md", "reports/FINDINGS.md", "notebooks/banking_analysis.ipynb"]
COLLECTION = "banksight_docs"

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions about the BankSight banking analytics project using ONLY the context passages. "
     "Cite the passage ids you used in square brackets, e.g. [reports/FINDINGS.md#3]. "
     "If the context does not contain the answer, say you could not find it in the project documents. "
     "The dataset is synthetic; do not present results as real-world facts. At most 120 words."),
    ("human", "CONTEXT:\n{context}\n\nQuestion: {question}"),
])


def load_documents(repo_root: str | Path) -> list[Document]:
    """Read the project's prose. For the notebook, only the markdown cells (the narrative) are kept."""
    root = Path(repo_root)
    docs = []
    for rel in DOC_SOURCES:
        path = root / rel
        if not path.exists():
            continue
        if path.suffix == ".ipynb":
            cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
            text = "\n\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "markdown")
        else:
            text = path.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", " ", text, flags=re.S)  # commands and diagrams are not knowledge
        docs.append(Document(page_content=text, metadata={"source": rel}))
    return docs


def split_documents(docs: list[Document], chunk_size: int = 800, chunk_overlap: int = 120) -> list[Document]:
    """Split on headings first, then paragraphs, so chunks stay on one topic where possible."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    counters: dict[str, int] = {}
    for chunk in chunks:
        source = chunk.metadata["source"]
        counters[source] = counters.get(source, -1) + 1
        chunk.metadata["chunk_id"] = f"{source}#{counters[source]}"
    return chunks


def build_vectorstore(repo_root: str | Path, embeddings, persist_dir: str | Path | None = None) -> Chroma:
    """Embed every chunk into Chroma. With persist_dir the index is saved and rebuilt from scratch."""
    chunks = split_documents(load_documents(repo_root))
    if not chunks:
        raise ValueError(f"No documents found under {repo_root}")
    kwargs = {}
    if persist_dir:
        shutil.rmtree(persist_dir, ignore_errors=True)
        kwargs["persist_directory"] = str(persist_dir)
    return Chroma.from_documents(
        chunks, embeddings,
        collection_name=f"{COLLECTION}_{uuid.uuid4().hex[:8]}" if not persist_dir else COLLECTION,
        ids=[c.metadata["chunk_id"] for c in chunks],
        **kwargs,
    )


def load_vectorstore(persist_dir: str | Path, embeddings) -> Chroma:
    return Chroma(collection_name=COLLECTION, embedding_function=embeddings, persist_directory=str(persist_dir))


def format_context(chunks: list[Document]) -> str:
    return "\n\n".join(f"[{c.metadata['chunk_id']}] {c.page_content}" for c in chunks)


def extractive_mock(prompt_value) -> str:
    """Offline stand-in for an LLM: quotes the opening of the two best passages with their ids."""
    text = prompt_value.to_string()
    context = text.split("CONTEXT:", 1)[-1].split("Question:", 1)[0]
    passages = re.findall(r"\[([^\]]+#\d+)\] (.+?)(?=\n\n\[[^\]]+#\d+\] |\Z)", context, re.S)
    if not passages:
        return "I could not find this in the project documents."
    lines = []
    for chunk_id, body in passages[:2]:
        body = re.sub(r"[#*`|>-]+", " ", body)
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(body.split()))
        lines.append(" ".join(sentences[:2]) + f" [{chunk_id}]")
    return "\n".join(lines)


@dataclass
class DocsAnswer:
    question: str
    text: str
    sources: list[str] = field(default_factory=list)


class DocsQA:
    def __init__(self, vectorstore: Chroma, chat_model=None, k: int = 4):
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        llm = chat_model if chat_model is not None else RunnableLambda(extractive_mock)
        self.chain = PROMPT | llm | StrOutputParser()

    def ask(self, question: str) -> DocsAnswer:
        chunks = self.retriever.invoke(question)
        if not chunks:
            return DocsAnswer(question, "I could not find this in the project documents.")
        text = self.chain.invoke({"context": format_context(chunks), "question": question})
        return DocsAnswer(question, text.strip(), [c.metadata["chunk_id"] for c in chunks])
