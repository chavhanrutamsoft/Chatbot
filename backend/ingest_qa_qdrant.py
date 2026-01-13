#!/usr/bin/env python3
"""
PRODUCTION INGEST FOR QA-FIRST RAG (Qdrant + GPT-4 Mini)

Fixes:
- Stores module & intent metadata
- Context-rich embeddings
- GPT-4 mini optimized
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

# =========================
# PATHS
# =========================

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

QA_FILE = DATA_DIR / "final_chunks.json"

load_dotenv(PROJECT_ROOT / ".env")

# =========================
# CONFIG
# =========================

QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_qa")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))

# =========================
# EMBEDDINGS
# =========================

print("🔹 Loading embedding model (all-MiniLM-L6-v2)")
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

def embed(text: str):
    vec = embedding_model.encode(text)
    return vec.tolist()

# =========================
# QDRANT CLIENT
# =========================

qdrant = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY,
)

# =========================
# COLLECTION
# =========================

def recreate_collection():
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME in collections:
        print(f"⚠️ Deleting existing collection: {COLLECTION_NAME}")
        qdrant.delete_collection(COLLECTION_NAME)

    # Use create_collection instead of deprecated recreate_collection
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        ),
    )
    print(f"✅ Created collection: {COLLECTION_NAME}")

# =========================
# LOAD QA
# =========================

def load_qa_pairs():
    if not QA_FILE.exists():
        raise FileNotFoundError(f"QA file missing: {QA_FILE}")
    with open(QA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

# =========================
# INGEST
# =========================

def ingest():
    recreate_collection()
    chunks = load_qa_pairs()

    print(f"🚀 Ingesting {len(chunks)} chunks (multi-view)")

    point_id = 0

    for batch_idx, batch in enumerate(chunked(chunks, BATCH_SIZE), 1):
        points = []

        for chunk in batch:
            chunk_type = chunk.get("type", "raw")
            text = chunk.get("text", "")
            
            if not text:
                continue

            # Extract question/answer from different chunk types
            question = ""
            answer = ""
            
            if chunk_type == "qa":
                # Parse Q: ... A: ... format
                if "Q:" in text and "A:" in text:
                    parts = text.split("A:")
                    question = parts[0].replace("Q:", "").strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                else:
                    question = text
                    answer = text
            elif chunk_type == "definition":
                # "Definition of X. Y" -> question: "X", answer: "Y"
                if "Definition of" in text:
                    parts = text.replace("Definition of", "").split(".", 1)
                    question = parts[0].strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                else:
                    question = text
                    answer = text
            elif chunk_type == "meaning":
                # "X means Y" -> question: "X", answer: "Y"
                if " means " in text:
                    parts = text.split(" means ", 1)
                    question = parts[0].strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                else:
                    question = text
                    answer = text
            elif chunk_type == "usage":
                # "X is used for Y" -> question: "X", answer: "Y"
                if " is used for " in text:
                    parts = text.split(" is used for ", 1)
                    question = parts[0].strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                else:
                    question = text
                    answer = text
            else:
                # For raw, procedure, etc. - use text as both question and answer
                question = text[:100] if len(text) > 100 else text  # Use first 100 chars as question
                answer = text

            # ----------------------------
            # 🔥 MULTI-VIEW EMBEDDINGS
            # ----------------------------

            views = []

            # 1️⃣ Definition view (if we have question/answer)
            if question and answer and question != answer:
                views.append(f"""
Definition of {question}.
{answer}
""".strip())

                views.append(f"""
What is {question}?
{answer}
""".strip())

                views.append(f"""
{question} means:
{answer}
""".strip())

                # 2️⃣ Usage / explanation
                views.append(f"""
Why is {question} used?
{answer}
""".strip())

            # 3️⃣ Original text (always include)
            views.append(f"""
Type: {chunk_type}

{text}
""".strip())

            # ----------------------------
            # STORE ALL VIEWS
            # ----------------------------

            for view_text in views:
                vector = embed(view_text)

                payload = {
                    "type": chunk_type,
                    "text": text,
                    "question": question if question else "",
                    "answer": answer if answer else "",
                    "view": view_text,
                }

                points.append({
                    "id": point_id,
                    "vector": vector,
                    "payload": payload
                })

                point_id += 1

        if points:
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )

            print(f"✅ Batch {batch_idx} | {len(points)} vectors")
            time.sleep(0.05)

    print("\n" + "="*80)
    print("🎯 INGEST COMPLETE (MULTI-VIEW)")
    print("="*80)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total vectors: {point_id}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    ingest()
