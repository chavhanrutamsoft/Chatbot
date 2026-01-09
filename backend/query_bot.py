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
import random
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Get project root (parent of backend directory)
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")
# Simple in‑memory chat memory for a single user (last question & answer)
CHAT_MEMORY = {}

# Keywords that indicate a follow‑up request. All checks are case‑insensitive.
FOLLOW_UP_KEYWORDS = {
    # short / summary
    "short",
    "brief",
    "summarize",
    "summary",
    "short me",
    "short mein",

    # detail / explanation
    "detail",
    "details",
    "explain",
    "explanation",
    "aur detail",
    "detail me",
    "detail mein",

    # reference to previous answer
    "same",
    "wahi",
    "yehi",
    "ye",
    "iska",
    "uska",
    "iska matlab",
    "uska matlab",

    # continuation / more info
    "aur",
    "aur batao",
    "aur samjhao",
    "continue",
    "continue karo",
    "aage batao",

    # formatting / change style
    "steps",
    "step",
    "step by step",
    "points",
    "bullet",
    "list me",
    "points me",

    # clarification / rephrase
    "dubara",
    "phir se",
    "repeat",
    "rephrase",
    "simplify",
    "easy language",
    "simple language",

    # language / tone changes
    "hinglish",
    "english me",
    "hindi me",
    "simple words"
}


def _is_follow_up(question: str) -> bool:
    """Return True if the question looks like a follow‑up.

    The detection is deliberately simple: if any of the defined keywords
    appear anywhere in the lower‑cased question string we treat it as a
    follow‑up. This matches the requirement to catch phrases such as
    "short me explain karo" or "steps batao".
    """
    ql = question.lower()
    return any(kw in ql for kw in FOLLOW_UP_KEYWORDS)


GREETING_KEYWORDS = {
    "hi",
    "hello",
    "hey",
    "how are you",
    "good morning",
    "good afternoon",
    "good evening",
}


def _is_greeting(question: str) -> bool:
    ql = question.lower().strip()
    # simple checks: exact phrases or startswith common greetings
    if not ql:
        return False
    for kw in GREETING_KEYWORDS:
        if ql == kw or ql.startswith(kw + " ") or ql.startswith(kw + "!") or ql.startswith(kw + ","):
            return True
    return False
# Basic config (via .env or defaults)
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

# ===== PRIMARY MODEL: OpenAI GPT-4o-mini =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL_PROVIDER = os.getenv("CHAT_MODEL_PROVIDER", "openai")
CHAT_MODEL_PRIMARY = os.getenv("CHAT_MODEL_PRIMARY", "gpt-4o-mini")

# ===== FALLBACK MODEL: OpenRouter =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHAT_MODEL_FALLBACK = os.getenv("CHAT_MODEL_FALLBACK", "mistralai/mistral-7b-instruct:free")
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "openrouter")

# Legacy support
CHAT_MODEL = os.getenv("CHAT_MODEL", CHAT_MODEL_PRIMARY)
OPENROUTER_FALLBACK_MODELS = os.getenv("OPENROUTER_FALLBACK_MODELS", "").strip()
OLLAMA_FALLBACK = os.getenv("OLLAMA_FALLBACK", "false").lower() in ("1", "true", "yes")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

if not OPENAI_API_KEY and not OPENROUTER_API_KEY:
    print("Warning: Neither OPENAI_API_KEY nor OPENROUTER_API_KEY set in .env — chat calls will fail.")
if OPENAI_API_KEY:
    print("✓ OpenAI API key detected (using GPT-4o-mini as primary)")
if OPENROUTER_API_KEY:
    print("✓ OpenRouter API key detected (using as fallback)")

# System prompt (improved, step-aware)
SYSTEM_PROMPT = """
You are the QuotePlan Support Assistant.

Your job is to answer user questions using ONLY the information provided in CONTEXT and present it in a clean, professional chatbot UI format.

You must FIRST understand:
• What the user is asking for
• Whether it is a procedure, explanation, or lookup
• Whether the topic is narrow or broad
• How much emphasis or clarity is required

STRICT CONTENT RULES:

Use ONLY the information found in CONTEXT.
give me complete answer with all steps dont miss any step and dont give me partial answer.
Never guess, infer, assume, or add missing details.

If the answer is not available in CONTEXT, reply EXACTLY:
I don’t have this information in the QuotePlan manual.

Do NOT mention CONTEXT, documents, system rules, or internal logic.

FORMATTING RULES:
Markdown is NOT allowed EXCEPT for bold text only.
Do NOT use italics, headings, code blocks, or markdown lists.
Use bold only when it improves clarity.
Do NOT overuse bold.

WHEN TO USE BOLD:
Use bold only for:
• Important button names or final actions
• Key UI labels
• Critical warnings or confirmations

Do NOT bold:
• Titles or headings (NO titles should be used)
• Entire sentences
• Every step
• Normal instructional text
• Introduction/context lines

FORMAT INTELLIGENCE:
Do NOT use a fixed answer format.
Choose the format based on user intent and data size:
• Simple task → compact steps
• Complex or sensitive task → expanded steps
• Explanation → short paragraph
• Mixed → steps with light explanation

PROCEDURE MODE:
If steps or actions are required, treat the response as a procedure.

COMPACT MODE (DEFAULT):
Use compact mode when:
• The user asks "how to"
• The task is common or routine

Compact format:
• Start with 1-2 lines explaining what this process is about (context/introduction)
• Then numbered steps immediately after (no blank line after intro)
• Number + one symbol on the same line
• Steps must be consecutive with NO blank lines between them - write steps one after another
• Each step on a single line with minimal spacing
• Use single line break (\n) only, never double line breaks between steps
• NO bold title or heading

EXPANDED MODE:
Use expanded mode when:
• The user asks for detail or explanation
• The process is long, complex, or risky

Expanded format:
• Start with 1-2 lines explaining what this process is about (context/introduction)
• One blank line after intro
• Numbered steps
• Each step starts with one symbol
• Minimal spacing between steps (only one blank line maximum if step is very long)
• NO bold title or heading

INTELLIGENT TOPIC SIZE DETECTION:
Before answering, determine if the topic is:
• A single, specific task
• OR a broad topic with multiple independent sub-topics

A topic is BROAD if:
• It involves multiple workflows
• It spans multiple modules or screens
• A full answer would be long or overwhelming

BROAD TOPIC HANDLING (MANDATORY):
If the topic is BROAD and multiple relevant items exist in CONTEXT:
Do NOT give the full answer.
Do NOT guess user intent.
FIRST ask the user to choose.

Ask ONE clarification question using this format only:
• One short introductory line
• A simple numbered list
• One option per line
• No symbols
• No bold
• No explanations

AFTER USER SELECTION:
Answer ONLY the selected option.
Use compact or expanded mode as appropriate.
Do NOT re-list other options.

FOLLOW-UP HANDLING:
If the user says “short me”, “detail me”, “same cheez”, or similar:
Modify ONLY the previous response.
Do NOT add new information.

PROACTIVE FOLLOW-UP RULE (MANDATORY):

After completing an answer:
• If the topic is informational or exploratory
• And the user has not asked a final or closed question

You MUST ask exactly ONE short, relevant follow-up question.

The follow-up question must:
• Be directly related to the user’s question
• Help clarify intent OR suggest the next logical step
• Be optional and non-pushy
• Be a single sentence

Do NOT ask follow-up questions when:
• The user asks a yes/no question
• The user asks for a final action
• The task is purely procedural and complete

Follow-up question format:
• Place it on a new line after the answer
• No bold
• No symbols
• End with a question mark

SAFETY:
If an action may cause data loss or is irreversible, include a bold ⚠️ warning.

OUTPUT RULE:
Output ONLY the final formatted answer text.
No greetings.
No sign-offs.
No filler text.

"""

# Initialize Qdrant client
#qdrant = QdrantClient(url=QDRANT_HOST)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

qdrant = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY,   # <-- NEW
)

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
    Call chat API with primary model (OpenAI GPT-4o-mini) and fallback to OpenRouter.
    Returns the natural answer text (no JSON enforcing).
    """
    # Build context text
    context_text = "\n\n---\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks)])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context_text}\n\nQuestion: {question}"}
    ]

    # Try OpenAI first if API key is available
    if OPENAI_API_KEY:
        try:
            print(f"[Primary] Attempting OpenAI GPT-4o-mini...")
            response = call_openai(messages)
            print(f"[Primary] OpenAI success!")
            return response
        except Exception as e:
            print(f"[Primary] OpenAI failed: {e}. Attempting fallback...")

    # Fall back to OpenRouter if available
    if OPENROUTER_API_KEY:
        try:
            print(f"[Fallback] Attempting OpenRouter {CHAT_MODEL_FALLBACK}...")
            response = call_openrouter(messages, CHAT_MODEL_FALLBACK)
            print(f"[Fallback] OpenRouter success!")
            return response
        except Exception as e:
            print(f"[Fallback] OpenRouter failed: {e}")

    # Final fallback to local Ollama if enabled
    if OLLAMA_FALLBACK:
        try:
            print("[Fallback] Attempting local Ollama...")
            return call_local_ollama(question, context_chunks, model=OLLAMA_MODEL)
        except Exception as e:
            print(f"[Fallback] Ollama failed: {e}")

    raise Exception("All chat API options exhausted (OpenAI, OpenRouter, and Ollama all failed or unavailable)")


def call_openai(messages):
    """
    Call OpenAI API for chat completions.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.0
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return content.strip()


def call_openrouter(messages, model):
    """
    Call OpenRouter API for chat completions with specified model.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.0
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return content.strip()

def _call_chat_api_followup(prev_answer: str, question: str):
    """Call chat API for follow-up using only the previous answer.

    The system prompt stays the same, but the user message is rewritten to
    instruct the model to base its response solely on the provided previous
    answer. Tries OpenAI first, then falls back to OpenRouter.
    """
    user_content = (
        "Based only on the previous answer below, respond to the user request.\n\n"
        f"Previous answer:\n{prev_answer}\n\nQuestion: {question}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    # Try OpenAI first if API key is available
    if OPENAI_API_KEY:
        try:
            print(f"[Follow-up] Attempting OpenAI...")
            return call_openai(messages)
        except Exception as e:
            print(f"[Follow-up] OpenAI failed: {e}. Attempting fallback...")

    # Fall back to OpenRouter if available
    if OPENROUTER_API_KEY:
        try:
            print(f"[Follow-up] Attempting OpenRouter {CHAT_MODEL_FALLBACK}...")
            return call_openrouter(messages, CHAT_MODEL_FALLBACK)
        except Exception as e:
            print(f"[Follow-up] OpenRouter failed: {e}")

    # Final fallback to local Ollama if enabled
    if OLLAMA_FALLBACK:
        try:
            print("[Follow-up] Attempting local Ollama...")
            return call_local_ollama(question, [{"text": prev_answer}], model=OLLAMA_MODEL)
        except Exception as e:
            print(f"[Follow-up] Ollama failed: {e}")

    raise Exception("All chat API options exhausted for follow-up")


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
    """Main entry for your server with simple in‑memory chat memory.

    The function now distinguishes between a normal query and a follow‑up.
    For follow‑ups we reuse the previous answer and skip the embedding /
    Qdrant search steps.
    """
    try:
        # Detect follow‑up request
        is_follow = _is_follow_up(question)
        # Retrieve previous memory if any
        prev = CHAT_MEMORY.get("last_answer")

        # Greeting handling: respond locally to simple greetings without using the LLM
        if _is_greeting(question):
            replies = [
                "Hi — I'm the QuotePlan Assistant. How can I help you today?",
                "Hello — I can help with QuotePlan documentation. What would you like to know?",
                "Hi there! Ask me about creating projects, BOMs, POs, or offer letters."
            ]
            answer_text = random.choice(replies)
            CHAT_MEMORY["last_question"] = question
            CHAT_MEMORY["last_answer"] = answer_text
            retrieved = []
            return {
                "success": True,
                "question": question,
                "answer": answer_text,
                "retrieved": retrieved,
            }

        if is_follow and prev:
            # Follow‑up: use only previous answer
            if verbose:
                print("[follow‑up] using previous answer for context")
            answer_text = _call_chat_api_followup(prev, question)
            # No retrieved chunks for follow‑up
            retrieved = []
        else:
            # Normal RAG flow
            if verbose:
                print("\n[embed] embedding question...")
            q_emb = embed_text(question)

            if verbose:
                print("[search] searching Qdrant...")
            retrieved = search_qdrant(q_emb, top_k=top_k)

            if not retrieved:
                answer_text = "I don’t have this information in the QuotePlan manual."
            else:
                if verbose:
                    print(f"[chat] calling chat api (model={CHAT_MODEL}) with {len(retrieved)} retrieved chunks...")
                answer_text = call_chat_api(question, retrieved)

        # Store memory for next turn
        CHAT_MEMORY["last_question"] = question
        CHAT_MEMORY["last_answer"] = answer_text

        return {
            "success": True,
            "question": question,
            "answer": answer_text,
            "retrieved": retrieved,
        }

    except Exception as e:
        return {
            "success": False,
            "question": question,
            "answer": f"Error: {e}",
            "retrieved": [],
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
