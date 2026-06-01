import time
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.common.llm_client import embed_text
from app.config import settings

CHROMA_COLLECTION = "document_chunks"
EMBEDDING_DIM = 1536  # DeepSeek embedding dimension
EMBED_BATCH_SIZE = 20
EMBED_RETRY_DELAY = 2

_client = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection():
    client = get_chroma_client()
    try:
        coll = client.get_collection(CHROMA_COLLECTION)
        return coll
    except Exception:
        return client.create_collection(
            CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )


def _embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using DeepSeek API with retry."""
    embeddings = []
    for text in texts:
        for attempt in range(3):
            try:
                vec = embed_text(text)
                embeddings.append(vec)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(EMBED_RETRY_DELAY * (attempt + 1))
    return embeddings


def add_chunks(chunks: List[dict]) -> List[str]:
    """
    Add document chunks to ChromaDB with DeepSeek embeddings.
    Processes in batches to avoid overwhelming the API.
    """
    collection = get_or_create_collection()
    all_ids = []

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        ids = [str(c["id"]) for c in batch]
        documents = [c["content"] for c in batch]
        metadatas = [
            {"document_id": c["document_id"], "chunk_index": c["chunk_index"]}
            for c in batch
        ]

        try:
            embeddings = _embed_batch(documents)
        except Exception:
            # Fallback: let ChromaDB use its default embedding
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
        else:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        all_ids.extend(ids)

    return all_ids


def delete_document_chunks(document_id: int):
    collection = get_or_create_collection()
    try:
        results = collection.get(where={"document_id": document_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass


def search_chunks(
    query: str,
    top_k: int = 10,
    where: Optional[dict] = None,
    subject_id: Optional[int] = None,
) -> List[dict]:
    """
    Search chunks using DeepSeek embedding for the query.
    Falls back to ChromaDB default embedding if DeepSeek fails.
    """
    collection = get_or_create_collection()

    try:
        query_embedding = embed_text(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )
    except Exception:
        # Fallback to ChromaDB's default embedding
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )

    hits = []
    if results.get("ids") and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            raw_distance = (
                results["distances"][0][i] if results.get("distances") else 0
            )
            if raw_distance is not None:
                score = 1.0 / (1.0 + raw_distance)
            else:
                score = 0.0
            hits.append({
                "id": int(results["ids"][0][i]),
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "score": round(score, 4),
            })

    return hits
