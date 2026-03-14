"""
services/knowledge_seeder.py
──────────────────────────────
Loads HR policy documents into ChromaDB at startup.

Collections:
  hr_policies     ← leave_policy.txt  and any other policy docs
  company_culture ← hr_handbook.txt   (conduct, values, disciplinary)

Skips if ChromaDB already has documents (idempotent).
OPENAI_API_KEY must be set for embeddings to work.
"""

from pathlib import Path
from app.core.config import settings

# Policy files live in hr_agent_system/rag/sample_policies/
_POLICIES_DIR = (
    Path(__file__).resolve().parent.parent  # backend/app/
    / "hr_agent_system" / "rag" / "sample_policies"
)


def seed_policies():
    """
    Seeds ChromaDB with HR policy files.
    Safe to call on every startup — skips if already loaded.
    """
    if not settings.OPENAI_API_KEY:
        print("[RAG] OPENAI_API_KEY not set — skipping ChromaDB seeding.")
        return

    try:
        import chromadb
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.document_loaders import TextLoader, PyPDFLoader
    except ImportError as e:
        print(f"[RAG] Missing dependency: {e}")
        return

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

    # Check if already seeded
    try:
        coll  = client.get_collection("hr_policies")
        count = coll.count()
        if count > 5:
            print(f"[RAG] ChromaDB already has {count} chunks — skipping seed.")
            return
    except Exception:
        pass  # collection doesn't exist yet

    if not _POLICIES_DIR.exists():
        print(f"[RAG] Policies directory not found: {_POLICIES_DIR}")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    total    = 0

    for txt_file in _POLICIES_DIR.glob("*.txt"):
        # Determine collection from filename
        name = txt_file.name.lower()
        if "handbook" in name or "culture" in name or "conduct" in name:
            collection = "company_culture"
        elif "job" in name or "description" in name:
            collection = "job_descriptions"
        else:
            collection = "hr_policies"

        try:
            loader = TextLoader(str(txt_file), encoding="utf-8")
            docs   = loader.load()
            for doc in docs:
                doc.metadata["file"] = txt_file.name

            chunks = splitter.split_documents(docs)
            store  = Chroma(
                client=client,
                collection_name=collection,
                embedding_function=embeddings,
            )
            store.add_documents(chunks)
            total += len(chunks)
            print(f"[RAG] {txt_file.name} → {len(chunks)} chunks → '{collection}'")
        except Exception as e:
            print(f"[RAG] Failed to load {txt_file.name}: {e}")

    # Also load any PDFs
    for pdf_file in _POLICIES_DIR.glob("*.pdf"):
        try:
            loader = PyPDFLoader(str(pdf_file))
            docs   = loader.load()
            for doc in docs:
                doc.metadata["file"] = pdf_file.name
            chunks = splitter.split_documents(docs)
            store  = Chroma(
                client=client,
                collection_name="hr_policies",
                embedding_function=embeddings,
            )
            store.add_documents(chunks)
            total += len(chunks)
            print(f"[RAG] {pdf_file.name} → {len(chunks)} chunks → 'hr_policies'")
        except Exception as e:
            print(f"[RAG] Failed to load {pdf_file.name}: {e}")

    print(f"[RAG] Seeded {total} total chunks into ChromaDB.")
