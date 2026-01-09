#!/usr/bin/env python3
"""
Ingest QA pairs into Qdrant with enhanced metadata
Stores both question and answer for better retrieval
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

# Get project paths
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

# Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_qa")
QA_FILE = DATA_DIR / "qa_pairs.json"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))

# Use local embedding model
print("Loading local embedding model (all-MiniLM-L6-v2)...")
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# Qdrant client
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
qdrant = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY,
)

def embed_text(text):
    """Get embedding using local SentenceTransformer."""
    emb = embedding_model.encode(text)
    try:
        return emb.tolist()
    except Exception:
        return list(map(float, emb))

def create_collection():
    """Create or recreate collection for QA pairs"""
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' exists. Deleting to recreate...")
        qdrant.delete_collection(collection_name=COLLECTION_NAME)

    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    print(f"Created collection: {COLLECTION_NAME} with dim {EMBEDDING_DIM}")

def load_qa_pairs():
    """Load QA pairs from JSON file"""
    if not QA_FILE.exists():
        print(f"QA pairs file not found: {QA_FILE.resolve()}")
        print("Please run: python backend/extract_qa_pairs.py")
        raise SystemExit(1)
    
    with open(QA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def chunked(iterable, n):
    """Split iterable into chunks of size n"""
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]

if __name__ == "__main__":
    create_collection()
    qa_pairs = load_qa_pairs()
    print(f"Total QA pairs: {len(qa_pairs)}")

    for batch_idx, batch in enumerate(chunked(qa_pairs, BATCH_SIZE)):
        ids = []
        vectors = []
        payloads = []

        for i, qa in enumerate(batch):
            # Create combined text for embedding (question + answer)
            # This helps with semantic search
            combined_text = f"Q: {qa['question']}\nA: {qa['answer']}"
            
            try:
                emb = embed_text(combined_text)
            except Exception as e:
                print(f"Embedding failed: {e}")
                raise
            
            point_id = batch_idx * BATCH_SIZE + i
            
            # Store rich metadata for better retrieval
            payload = {
                "text": combined_text,  # Full text for retrieval
                "question": qa['question'],
                "answer": qa['answer'],
                "type": qa.get('type', 'general'),
                "has_steps": qa.get('has_steps', False),
                "step_count": qa.get('step_count', 0),
            }
            
            # Add step-specific metadata if available
            if qa.get('type') == 'step':
                payload['step_number'] = qa.get('step_number')
                payload['parent_procedure'] = qa.get('parent_procedure', '')
            
            ids.append(point_id)
            vectors.append(emb)
            payloads.append(payload)

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[{"id": ids[i], "vector": vectors[i], "payload": payloads[i]} for i in range(len(ids))],
        )
        print(f"Upserted batch {batch_idx+1}/{(len(qa_pairs)+BATCH_SIZE-1)//BATCH_SIZE} ({len(batch)} QA pairs)")
        time.sleep(0.1)

    print("\n" + "="*80)
    print("✅ Done ingesting QA pairs into Qdrant!")
    print("="*80)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total points: {len(qa_pairs)}")
    print("\nYou can now query using: python backend/query_bot.py --q 'your question'")
