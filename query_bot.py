#!/usr/bin/env python3
"""
Query script for Qdrant + OpenRouter chat (Option A output format).

Behavior:
- Uses local SentenceTransformer embeddings (all-MiniLM-L6-v2) if available.
- Searches Qdrant for relevant chunks.
- Calls OpenRouter chat model to generate a natural-language answer (no JSON-enforcer).
- Returns a structured dict: { success, question, answer, retrieved } so your server can read `answer`.
"""

import os
import json
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

# Basic config (via .env or defaults)
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini:free")
OPENROUTER_FALLBACK_MODELS = os.getenv("OPENROUTER_FALLBACK_MODELS", "").strip()
OLLAMA_FALLBACK = os.getenv("OLLAMA_FALLBACK", "false").lower() in ("1", "true", "yes")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")

if not OPENROUTER_API_KEY:  
    print("Warning: OPENROUTER_API_KEY not set in .env — chat calls will fail.")

# System prompt (improved, step-aware)
SYSTEM_PROMPT = """
You are the QuotePlan Support Assistant. Use the provided CONTEXT to answer the user’s question.
RULES:
1. Only use information from CONTEXT. Never guess or add new information.
2. If the CONTEXT describes a procedure, provide clear step-by-step instructions.
3. If the CONTEXT describes concepts or explanations, provide a normal descriptive answer.
4. Only use steps, bullets, or tables when the CONTEXT requires them.
5. The answer should be clear, complete, and natural — like ChatGPT. Not too short and not too long.
6. Do NOT summarize unless the CONTEXT itself is a summary.
7. Output only the final answer text. No JSON enforcement, no structured wrappers.
8. If information is missing from CONTEXT, reply exactly:
   "I don’t have this information in the QuotePlan manual."
"""

# Initialize Qdrant client
qdrant = QdrantClient(url=QDRANT_HOST)

# Load local embedding model if available
print("Loading local embedding model (all-MiniLM-L6-v2) ...")
try:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    EMBEDDING_DIM = 384
    print("Loaded all-MiniLM-L6-v2")
except Exception as e:
    print(f"Could not load local embedding model: {e}")
    embedding_model = None
    EMBEDDING_DIM = 384  # fallback dimension


def embed_text(text):
    """Return embedding vector (list of floats). Uses local model if available."""
    if embedding_model:
        emb = embedding_model.encode(text)
        try:
            return emb.tolist()
        except Exception:
            return list(map(float, emb))
    # fallback: zero vector (not ideal, but prevents crashes)
    return [0.0] * EMBEDDING_DIM


def _qdrant_search_flexible(query_vector, top_k=5):
    """
    Use available qdrant-client method to search. Tries several possible APIs for compatibility:
      - qdrant.search(...)
      - qdrant.search_points(...)
      - qdrant.query_points(...)
    Returns list of hits with attributes id, payload, score (if available).
    """
    # Try qdrant.search (common)
    try:
        hits = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return hits
    except Exception:
        pass

    # Try qdrant.search_points
    try:
        hits = qdrant.search_points(
            collection_name=COLLECTION_NAME,
            vector=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return hits
    except Exception:
        pass

    # Try qdrant.query_points (older/newer variants)
    try:
        res = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        # some query_points return an object with .points
        if hasattr(res, "points"):
            return res.points
        return res
    except Exception:
        pass

    raise RuntimeError("Unable to call Qdrant search API — check qdrant-client version.")


def search_qdrant(query_embedding, top_k=5):
    """Search Qdrant and return list of dicts: { id, text, score }."""
    hits = _qdrant_search_flexible(query_embedding, top_k=top_k)
    results = []
    for hit in hits:
        # `hit` might be a dict-like or object; be defensive
        try:
            hit_id = getattr(hit, "id", None) or hit.get("id", None)
        except Exception:
            hit_id = None
        try:
            payload = getattr(hit, "payload", None) or hit.get("payload", None)
        except Exception:
            payload = None
        try:
            score = getattr(hit, "score", None) or hit.get("score", None)
        except Exception:
            score = None

        text = None
        if payload:
            # payload may be a dict with 'text'
            text = payload.get("text") if isinstance(payload, dict) else getattr(payload, "get", lambda k: None)("text")
        results.append({"id": hit_id, "text": text, "score": score})
    return results


def call_chat_api(question, context_chunks):
    """
    Call OpenRouter chat API and return the natural answer text (no JSON enforcing).
    If the primary model fails with 429, will try any comma-separated fallbacks from env var.
    If OpenRouter is completely not available and OLLAMA_FALLBACK is enabled, try local Ollama.
    """
    if not OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY missing in .env — set it to use chat API")

    # Build context text
    context_text = "\n\n---\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks)])

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context_text}\n\nQuestion: {question}"}
    ]

    # models to try
    models_to_try = [CHAT_MODEL]
    if OPENROUTER_FALLBACK_MODELS:
        for m in OPENROUTER_FALLBACK_MODELS.split(","):
            mm = m.strip()
            if mm and mm not in models_to_try:
                models_to_try.append(mm)

    last_exc = None
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.0
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            # Response content: choices[0].message.content (string)
            content = r.json()["choices"][0]["message"]["content"]
            if isinstance(content, dict):
                # Some wrappers might return structured content — convert to string if needed
                return json.dumps(content, ensure_ascii=False)
            return content.strip()
        except requests.exceptions.HTTPError as he:
            status = getattr(he.response, "status_code", None)
            last_exc = he
            if status == 429:
                print(f"Model {model} rate-limited (429). Trying fallback model if available...")
                continue
            # non-rate-limit HTTP error: raise immediately
            raise
        except Exception as e:
            last_exc = e
            print(f"Warning: OpenRouter model {model} failed: {e}. Trying next if available...")
            continue

    # If all OpenRouter models failed, attempt local Ollama fallback (best-effort)
    if OLLAMA_FALLBACK:
        try:
            print("Attempting local Ollama fallback...")
            return call_local_ollama(question, context_chunks, model=OLLAMA_MODEL)
        except Exception as e:
            last_exc = e

    raise Exception(f"All OpenRouter attempts failed. Last error: {last_exc}")


def call_local_ollama(question, context_chunks, model="mistral:7b"):
    """
    Best-effort attempt to call local Ollama (CLI or HTTP) and return text output.
    This is optional and will only be used if configured via OLLAMA_FALLBACK.
    """
    prompt_text = "\n\n---\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks)])
    full_prompt = f"CONTEXT:\n{prompt_text}\n\nQuestion: {question}\n\nAnswer in natural text."

    # Try CLI first
    try:
        import subprocess, shlex
        cmd = ["ollama", "generate", model, "--prompt", full_prompt]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.strip()
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Ollama CLI attempt failed: {e}")

    # Try local Ollama HTTP endpoint
    try:
        url = os.getenv("OLLAMA_HTTP_URL", "http://localhost:11434/api/generate")
        payload = {"model": model, "prompt": full_prompt}
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        # Attempt to return 'response' or raw text
        j = r.json()
        if isinstance(j, dict) and "response" in j:
            return j["response"]
        return json.dumps(j, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Local Ollama fallback failed: {e}")


def build_context(retrieved):
    """Return the joined context text (for debugging / logging)"""
    return "\n\n---\n\n".join([f"[{i+1}] {r['text']}" for i, r in enumerate(retrieved)])


def answer_structured(question, top_k=5, verbose=True):
    """
    Main entry for your server.
    Returns a dict: { success: bool, question: str, answer: str, retrieved: [...] }
    The 'answer' field contains the full natural answer text (no forced summary).
    """
    try:
        if verbose:
            print("\n[embed] embedding question...")
        q_emb = embed_text(question)

        if verbose:
            print("[search] searching Qdrant...")
        retrieved = search_qdrant(q_emb, top_k=top_k)

        if not retrieved:
            return {
                "success": True,
                "question": question,
                "answer": "I don’t have this information in the QuotePlan manual.",
                "retrieved": []
            }

        if verbose:
            print(f"[chat] calling chat api (model={CHAT_MODEL}) with {len(retrieved)} retrieved chunks...")
        answer_text = call_chat_api(question, retrieved)

        # Return full natural answer text exactly as received from model
        return {
            "success": True,
            "question": question,
            "answer": answer_text,
            "retrieved": retrieved
        }

    except Exception as e:
        # Return helpful error for frontend
        return {
            "success": False,
            "question": question,
            "answer": f"Error: {e}",
            "retrieved": []
        }


def answer(question, top_k=5):
    """Backward-compatible helper returning the answer string only."""
    out = answer_structured(question, top_k=top_k, verbose=False)
    return out.get("answer", "")


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", required=True, help="User question in quotes")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
    args = parser.parse_args()

    if args.json:
        res = answer_structured(args.q, verbose=True)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"\nQuestion: {args.q}\n")
        print(answer(args.q))
        print()
