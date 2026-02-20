"""RAG knowledge store — runbooks, past incidents, architecture docs."""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter

from agent.config import settings

logger = logging.getLogger("agent.enrichment")

_COLLECTION_NAME = "sre_knowledge"


class KnowledgeStore:
    """Vector store backed by ChromaDB for runbook and incident retrieval."""

    def __init__(self) -> None:
        self._client = chromadb.Client(ChromaSettings(
            anonymized_telemetry=False,
            is_persistent=True,
            persist_directory=settings.chroma_persist_dir,
        ))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._splitter = MarkdownTextSplitter(chunk_size=800, chunk_overlap=100)

    def ingest_runbooks(self, directory: str | None = None) -> int:
        """Load all markdown files from the knowledge directory into the store."""
        knowledge_dir = Path(directory or settings.knowledge_dir)
        if not knowledge_dir.exists():
            logger.warning("Knowledge directory does not exist: %s", knowledge_dir)
            return 0

        docs: list[Document] = []
        for md_file in sorted(knowledge_dir.glob("*.md")):
            text = md_file.read_text()
            chunks = self._splitter.create_documents(
                [text],
                metadatas=[{"source": md_file.name, "type": "runbook"}],
            )
            docs.extend(chunks)

        if not docs:
            return 0

        self._collection.upsert(
            ids=[f"runbook-{i}" for i in range(len(docs))],
            documents=[d.page_content for d in docs],
            metadatas=[d.metadata for d in docs],
        )
        logger.info("Ingested %d chunks from %s", len(docs), knowledge_dir)
        return len(docs)

    def store_incident(self, incident_id: str, summary: str, metadata: dict | None = None) -> None:
        """Store a resolved incident for future retrieval."""
        self._collection.upsert(
            ids=[f"incident-{incident_id}"],
            documents=[summary],
            metadatas=[{**(metadata or {}), "type": "past_incident"}],
        )

    def search(self, query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
        """Retrieve the most relevant knowledge chunks for a query."""
        kwargs: dict = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        hits = []
        for i, doc in enumerate(results["documents"][0]):
            hits.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
        return hits

    def search_runbooks(self, query: str, n_results: int = 3) -> list[dict]:
        return self.search(query, n_results=n_results, where={"type": "runbook"})

    def search_incidents(self, query: str, n_results: int = 3) -> list[dict]:
        return self.search(query, n_results=n_results, where={"type": "past_incident"})
