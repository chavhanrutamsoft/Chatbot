# #!/usr/bin/env python3
# """
# PRODUCTION INGEST FOR QA-FIRST RAG (Qdrant + GPT-4 Mini)

# Fixes:
# - Stores module & intent metadata
# - Context-rich embeddings
# - GPT-4 mini optimized
# """

# import os
# import json
# import time
# from pathlib import Path
# from dotenv import load_dotenv
# from qdrant_client import QdrantClient
# from qdrant_client.http.models import VectorParams, Distance
# from qdrant_client.http.exceptions import ResponseHandlingException

# # =========================
# # PATHS
# # =========================

# BACKEND_DIR = Path(__file__).parent
# PROJECT_ROOT = BACKEND_DIR.parent
# DATA_DIR = PROJECT_ROOT / "data"

# QA_FILE = DATA_DIR / "final_chunks.json"

# load_dotenv(PROJECT_ROOT / ".env")

# # =========================
# # CONFIG
# # =========================

# QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
# QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
# COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

# # Parse BATCH_SIZE with error handling
# try:
#     batch_size_str = os.getenv("BATCH_SIZE", "8").strip()
#     BATCH_SIZE = int(batch_size_str) if batch_size_str else 8
# except (ValueError, AttributeError):
#     print(f"Warning: Invalid BATCH_SIZE value '{os.getenv('BATCH_SIZE')}', using default 8")
#     BATCH_SIZE = 8

# MAX_RETRIES = 5
# RETRY_DELAY = 2  # seconds
# TIMEOUT = 300  # 5 minutes timeout

# # =========================
# # EMBEDDINGS
# # =========================

# print("🔹 Loading embedding model (all-mpnet-base-v2 - best free model, 768 dims)")
# from sentence_transformers import SentenceTransformer
# embedding_model = SentenceTransformer("all-mpnet-base-v2")
# EMBEDDING_DIM = 768

# def embed(text: str):
#     vec = embedding_model.encode(text, normalize_embeddings=True)
#     return vec.tolist()

# # =========================
# # QDRANT CLIENT
# # =========================

# qdrant = QdrantClient(
#     url=QDRANT_HOST,
#     api_key=QDRANT_API_KEY,
#     timeout=TIMEOUT,  # Increased timeout for large batches
# )

# # =========================
# # COLLECTION
# # =========================

# def recreate_collection():
#     collections = [c.name for c in qdrant.get_collections().collections]
#     if COLLECTION_NAME in collections:
#         print(f"⚠️ Deleting existing collection: {COLLECTION_NAME}")
#         qdrant.delete_collection(COLLECTION_NAME)

#     # Use create_collection instead of deprecated recreate_collection
#     qdrant.create_collection(
#         collection_name=COLLECTION_NAME,
#         vectors_config=VectorParams(
#             size=EMBEDDING_DIM,
#             distance=Distance.COSINE
#         ),
#     )
#     print(f"✅ Created collection: {COLLECTION_NAME}")

# # =========================
# # LOAD QA
# # =========================

# def load_qa_pairs():
#     if not QA_FILE.exists():
#         raise FileNotFoundError(f"QA file missing: {QA_FILE}")
#     with open(QA_FILE, "r", encoding="utf-8") as f:
#         return json.load(f)

# def chunked(lst, n):
#     for i in range(0, len(lst), n):
#         yield lst[i:i+n]

# # =========================
# # INGEST
# # =========================

# def ingest():
#     recreate_collection()
#     chunks = load_qa_pairs()

#     print(f"🚀 Ingesting {len(chunks)} chunks (multi-view)")
#     print(f"📦 Batch size: {BATCH_SIZE}, Timeout: {TIMEOUT}s, Max retries: {MAX_RETRIES}")

#     point_id = 0
#     total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

#     for batch_idx, batch in enumerate(chunked(chunks, BATCH_SIZE), 1):
#         points = []
#         batch_start_id = point_id  # Track starting point_id for this batch

#         for chunk in batch:
#             chunk_type = chunk.get("type", "raw")
#             text = chunk.get("text", "")
            
#             if not text:
#                 continue

#             # Extract question/answer from different chunk types
#             question = ""
#             answer = ""
            
#             if chunk_type == "qa":
#                 # Parse Q: ... A: ... format
#                 if "Q:" in text and "A:" in text:
#                     parts = text.split("A:")
#                     question = parts[0].replace("Q:", "").strip()
#                     answer = parts[1].strip() if len(parts) > 1 else ""
#                 else:
#                     question = text
#                     answer = text
#             elif chunk_type == "definition":
#                 # "Definition of X. Y" -> question: "X", answer: "Y"
#                 if "Definition of" in text:
#                     parts = text.replace("Definition of", "").split(".", 1)
#                     question = parts[0].strip()
#                     answer = parts[1].strip() if len(parts) > 1 else ""
#                 else:
#                     question = text
#                     answer = text
#             elif chunk_type == "meaning":
#                 # "X means Y" -> question: "X", answer: "Y"
#                 if " means " in text:
#                     parts = text.split(" means ", 1)
#                     question = parts[0].strip()
#                     answer = parts[1].strip() if len(parts) > 1 else ""
#                 else:
#                     question = text
#                     answer = text
#             elif chunk_type == "usage":
#                 # "X is used for Y" -> question: "X", answer: "Y"
#                 if " is used for " in text:
#                     parts = text.split(" is used for ", 1)
#                     question = parts[0].strip()
#                     answer = parts[1].strip() if len(parts) > 1 else ""
#                 else:
#                     question = text
#                     answer = text
#             else:
#                 # For raw, procedure, etc. - use text as both question and answer
#                 question = text[:100] if len(text) > 100 else text  # Use first 100 chars as question
#                 answer = text

#             # ----------------------------
#             # 🔥 MULTI-VIEW EMBEDDINGS
#             # ----------------------------

#             views = []

#             # 1️⃣ Definition view (if we have question/answer)
#             if question and answer and question != answer:
#                 views.append(f"""
# Definition of {question}.
# {answer}
# """.strip())

#                 views.append(f"""
# What is {question}?
# {answer}
# """.strip())

#                 views.append(f"""
# {question} means:
# {answer}
# """.strip())

#                 # 2️⃣ Usage / explanation
#                 views.append(f"""
# Why is {question} used?
# {answer}
# """.strip())

#             # 3️⃣ Original text (always include)
#             views.append(f"""
# Type: {chunk_type}

# {text}
# """.strip())

#             # ----------------------------
#             # STORE ALL VIEWS
#             # ----------------------------

#             for view_text in views:
#                 vector = embed(view_text)

#                 payload = {
#                     "type": chunk_type,
#                     "text": text,
#                     "question": question if question else "",
#                     "answer": answer if answer else "",
#                     "view": view_text,
#                 }

#                 points.append({
#                     "id": point_id,
#                     "vector": vector,
#                     "payload": payload
#                 })

#                 point_id += 1

#         if points:
#             # Retry logic with exponential backoff
#             retry_count = 0
#             success = False
            
#             while retry_count < MAX_RETRIES and not success:
#                 try:
#                     qdrant.upsert(
#                         collection_name=COLLECTION_NAME,
#                         points=points
#                     )
#                     print(f"✅ Batch {batch_idx}/{total_batches} | {len(points)} vectors | Total: {point_id}")
#                     success = True
#                     time.sleep(0.1)  # Small delay between batches
                    
#                 except (ResponseHandlingException, Exception) as e:
#                     retry_count += 1
#                     if retry_count < MAX_RETRIES:
#                         wait_time = RETRY_DELAY * (2 ** (retry_count - 1))  # Exponential backoff
#                         print(f"⚠️ Batch {batch_idx} failed (attempt {retry_count}/{MAX_RETRIES}): {str(e)[:100]}")
#                         print(f"   Retrying in {wait_time} seconds...")
#                         time.sleep(wait_time)
#                     else:
#                         print(f"❌ Batch {batch_idx} failed after {MAX_RETRIES} attempts")
#                         print(f"   Error: {str(e)[:200]}")
#                         print(f"   Rolling back point_id from {point_id} to {batch_start_id}")
#                         point_id = batch_start_id  # Roll back point_id on failure
#                         print(f"   Continuing with next batch...")
#                         # Continue to next batch instead of crashing
#                         break

#     print("\n" + "="*80)
#     print("🎯 INGEST COMPLETE (MULTI-VIEW)")
#     print("="*80)
#     print(f"Collection: {COLLECTION_NAME}")
#     print(f"Total vectors: {point_id}")

# # =========================
# # MAIN
# # =========================

# if __name__ == "__main__":
#     ingest()



#!/usr/bin/env python3
"""
PRODUCTION INGEST FOR RAG (Qdrant + GPT-4.1)

- No synthetic questions
- No multi-view embeddings
- One chunk = one vector
- Metadata-first retrieval
"""

import os
import json
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

CHUNKS_FILE = DATA_DIR / "final_chunks.json"

load_dotenv(PROJECT_ROOT / ".env")

# =========================
# CONFIG
# =========================

QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

# =========================
# EMBEDDINGS
# =========================

print("🔹 Loading embedding model: all-mpnet-base-v2 (768 dims)")
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-mpnet-base-v2")
EMBEDDING_DIM = 768

def embed(text: str):
    return embedding_model.encode(
        text,
        normalize_embeddings=True
    ).tolist()

# =========================
# QDRANT
# =========================

qdrant = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY,
)

def recreate_collection():
    if COLLECTION_NAME in [c.name for c in qdrant.get_collections().collections]:
        print(f"⚠️ Deleting collection: {COLLECTION_NAME}")
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        )
    )
    print(f"✅ Created collection: {COLLECTION_NAME}")

# =========================
# INGEST
# =========================

def ingest():
    recreate_collection()

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"🚀 Ingesting {len(chunks)} chunks")

    points = []
    point_id = 0

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue

        payload = {
            "section": chunk.get("section", ""),
            "type": chunk.get("type", "paragraph"),
            "order": chunk.get("order"),
            "text": text
        }

        points.append({
            "id": point_id,
            "vector": embed(text),
            "payload": payload
        })

        point_id += 1

        # Flush in batches of 64
        if len(points) >= 64:
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            points.clear()

    if points:
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

    print("=" * 80)
    print("🎯 INGEST COMPLETE")
    print("=" * 80)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total vectors: {point_id}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    ingest()
