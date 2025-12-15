"""Ingest chunks into Qdrant using local SentenceTransformer embeddings."""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

load_dotenv()

# Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")
CHUNKS_FILE = os.getenv("CHUNKS_FILE", "chunks.json")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))

# Use local embedding model
print("Loading local embedding model (all-MiniLM-L6-v2)...")
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 outputs 384 dims

# Qdrant client
qdrant = QdrantClient(url=QDRANT_HOST)


def embed_text(text):
    """Get embedding using local SentenceTransformer."""
    emb = embedding_model.encode(text)
    try:
        return emb.tolist()
    except Exception:
        return list(map(float, emb))


def create_collection():
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME in existing:
        print("Collection exists. Deleting to recreate with correct vector size...")
        qdrant.delete_collection(collection_name=COLLECTION_NAME)

    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    print("Created collection:", COLLECTION_NAME, "with dim", EMBEDDING_DIM)


def load_chunks():
    p = Path(CHUNKS_FILE)
    if not p.exists():
        print(f"Chunks file not found: {p.resolve()}")
        raise SystemExit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]


if __name__ == "__main__":
    create_collection()
    chunks = load_chunks()
    print("Total chunks:", len(chunks))

    for batch_idx, batch in enumerate(chunked(chunks, BATCH_SIZE)):
        ids = []
        vectors = []
        payloads = []

        for i, text in enumerate(batch):
            try:
                emb = embed_text(text)
            except Exception as e:
                print("Embedding failed:", e)
                raise
            ids.append(batch_idx * BATCH_SIZE + i)
            vectors.append(emb)
            payloads.append({"text": text})

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[{"id": ids[i], "vector": vectors[i], "payload": payloads[i]} for i in range(len(ids))],
        )
        print(f"Upserted batch {batch_idx+1}/{(len(chunks)+BATCH_SIZE-1)//BATCH_SIZE}")
        time.sleep(0.1)

    print("Done ingesting into Qdrant.")
            # Use integer IDs for Qdrant
