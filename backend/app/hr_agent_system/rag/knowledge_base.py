"""
rag/knowledge_base.py
─────────────────────
ChromaDB RAG setup. Three collections:
  hr_policies       — leave, attendance rules, conduct
  company_culture   — values, conduct, disciplinary process
  job_descriptions  — role specs for recruitment agent

On startup: seed_all_policies() loads sample_policies/ into ChromaDB.
Retriever: get_retriever(collection) → LangChain retriever object.
"""

import os
from pathlib import Path
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader

from config.settings import settings

POLICIES_DIR = Path(__file__).parent / "sample_policies"
COLLECTIONS  = ["hr_policies", "company_culture", "job_descriptions"]


# ── Embeddings ────────────────────────────────────────────────────────────────

def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


# ── ChromaDB client ───────────────────────────────────────────────────────────

def _get_chroma_client():
    """
    Returns an HttpClient if CHROMA_HOST is set (Docker mode).
    Falls back to local PersistentClient for development without Docker.
    """
    if settings.CHROMA_HOST:
        print(f"[RAG] Using ChromaDB HTTP server at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        return chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
    print(f"[RAG] Using ChromaDB local persistence at {settings.CHROMA_PERSIST_PATH}")
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_PATH)


# ── Per-collection vectorstore ────────────────────────────────────────────────

def get_vectorstore(collection_name: str) -> Chroma:
    client = _get_chroma_client()
    return Chroma(
        client             = client,
        collection_name    = collection_name,
        embedding_function = get_embeddings(),
    )


def get_retriever(collection_name: str = "hr_policies", k: int = 3):
    """
    Returns a LangChain retriever for the given collection.
    Use in tools: retriever.invoke("your query") → List[Document]
    """
    try:
        store = get_vectorstore(collection_name)
        return store.as_retriever(search_kwargs={"k": k})
    except Exception as e:
        print(f"[RAG] Retriever unavailable for '{collection_name}': {e}")
        return None


# ── Document Ingestion ────────────────────────────────────────────────────────

def ingest_text_file(
    file_path: str,
    collection_name: str,
    metadata: dict = None,
) -> int:
    """Load a .txt or .pdf file into the specified ChromaDB collection."""
    path = Path(file_path)
    if not path.exists():
        print(f"[RAG] File not found: {file_path}")
        return 0

    loader = PyPDFLoader(str(path)) if path.suffix == ".pdf" else TextLoader(str(path))
    docs   = loader.load()

    if metadata:
        for doc in docs:
            doc.metadata.update(metadata)

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    chunks   = splitter.split_documents(docs)

    store = get_vectorstore(collection_name)
    store.add_documents(chunks)
    print(f"[RAG] Ingested '{path.name}' → {len(chunks)} chunks → '{collection_name}'")
    return len(chunks)


def ingest_raw_text(
    text: str,
    collection_name: str,
    source: str = "inline",
    metadata: dict = None,
) -> int:
    """Ingest a raw text string into a collection."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    meta     = {"source": source, **(metadata or {})}
    chunks   = splitter.create_documents([text], metadatas=[meta])

    store = get_vectorstore(collection_name)
    store.add_documents(chunks)
    return len(chunks)


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_all_policies():
    """
    Called once at startup (main.py lifespan).
    Loads all .txt files from sample_policies/ into hr_policies collection.
    Skips if already seeded.
    """
    try:
        store    = get_vectorstore("hr_policies")
        existing = store.get()
        if existing and len(existing.get("ids", [])) > 10:
            print("[RAG] Policies already seeded in ChromaDB. Skipping.")
            return

        total = 0
        for txt_file in POLICIES_DIR.glob("*.txt"):
            collection = "hr_policies"
            if "culture" in txt_file.name or "handbook" in txt_file.name:
                collection = "company_culture"
            elif "job" in txt_file.name or "description" in txt_file.name:
                collection = "job_descriptions"

            n = ingest_text_file(
                str(txt_file),
                collection,
                metadata={"file": txt_file.name},
            )
            total += n

        print(f"[RAG] Seeded {total} total chunks from sample_policies/")

    except Exception as e:
        print(f"[RAG] Seeding failed (set OPENAI_API_KEY): {e}")
