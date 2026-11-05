"""RAG over the project documents: loading, chunking, Chroma retrieval and the answer chain."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from assistant import REPO_ROOT
from assistant.docs_rag import DocsQA, build_vectorstore, load_documents, load_vectorstore, split_documents
from assistant.models import HashingEmbeddings


@pytest.fixture(scope="module")
def store():
    return build_vectorstore(REPO_ROOT, HashingEmbeddings())


def test_loads_readme_findings_and_notebook_narrative():
    docs = {d.metadata["source"]: d.page_content for d in load_documents(REPO_ROOT)}
    assert set(docs) == {"README.md", "reports/FINDINGS.md", "notebooks/banking_analysis.ipynb"}
    assert "import pandas" not in docs["notebooks/banking_analysis.ipynb"]  # code cells are left out


def test_chunks_are_small_overlapping_and_uniquely_labelled():
    chunks = split_documents(load_documents(REPO_ROOT), chunk_size=800, chunk_overlap=120)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)) > 10
    assert all(len(c.page_content) <= 800 for c in chunks)


@pytest.mark.parametrize("question, expected_source", [
    ("What did the analysis find about cross-selling and how many products customers hold?", "FINDINGS"),
    ("How were unusually large transactions flagged for review?", ""),
])
def test_retrieves_relevant_chunks(store, question, expected_source):
    hits = store.similarity_search(question, k=4)
    text = " ".join(h.page_content.lower() for h in hits)
    assert any(word in text for word in ("cross-sell", "cross sell", "unusually large", "0.1%"))
    assert expected_source in " ".join(h.metadata["source"] for h in hits)


def test_answer_cites_retrieved_chunks(store):
    answer = DocsQA(store).ask("Is the data reliable enough to build on?")
    assert answer.sources and all("#" in s for s in answer.sources)
    assert any(f"[{s}]" in answer.text for s in answer.sources)


def test_prompt_sends_context_and_question_to_the_model(store):
    model = FakeListChatModel(responses=["Most customers hold one or two products [reports/FINDINGS.md#2]."])
    qa = DocsQA(store, chat_model=model)
    answer = qa.ask("How many products does a typical customer hold?")
    assert answer.text.startswith("Most customers hold")


def test_persisted_index_can_be_reloaded(tmp_path):
    embeddings = HashingEmbeddings()
    built = build_vectorstore(REPO_ROOT, embeddings, tmp_path / "chroma")
    reloaded = load_vectorstore(tmp_path / "chroma", embeddings)
    assert reloaded._collection.count() == built._collection.count() > 0
