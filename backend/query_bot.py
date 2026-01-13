# #!/usr/bin/env python3
# """
# Query script for Qdrant + OpenRouter chat (Option A output format).

# Behavior:
# - Uses local SentenceTransformer embeddings (all-MiniLM-L6-v2) if available.
# - Searches Qdrant for relevant chunks.
# - Calls OpenRouter chat model to generate a natural-language answer (no JSON-enforcer).
# - Returns a structured dict: { success, question, answer, retrieved } so your server can read `answer`.
# """

# import os
# import json
# import requests
# import random
# from pathlib import Path
# from dotenv import load_dotenv
# from qdrant_client import QdrantClient

# # Get project root (parent of backend directory)
# BACKEND_DIR = Path(__file__).parent
# PROJECT_ROOT = BACKEND_DIR.parent

# # Load .env from project root
# load_dotenv(PROJECT_ROOT / ".env")
# # Simple in‑memory chat memory for a single user (last question & answer)
# CHAT_MEMORY = {}

# # Keywords that indicate a follow‑up request. All checks are case‑insensitive.
# FOLLOW_UP_KEYWORDS = {
#     # short / summary
#     "short",
#     "brief",
#     "summarize",
#     "summary",
#     "short me",
#     "short mein",

#     # detail / explanation
#     "detail",
#     "details",
#     "explain",
#     "explanation",
#     "aur detail",
#     "detail me",
#     "detail mein",

#     # reference to previous answer
#     "same",
#     "wahi",
#     "yehi",
#     "ye",
#     "iska",
#     "uska",
#     "iska matlab",
#     "uska matlab",

#     # continuation / more info
#     "aur",
#     "aur batao",
#     "aur samjhao",
#     "continue",
#     "continue karo",
#     "aage batao",

#     # formatting / change style
#     "steps",
#     "step",
#     "step by step",
#     "points",
#     "bullet",
#     "list me",
#     "points me",

#     # clarification / rephrase
#     "dubara",
#     "phir se",
#     "repeat",
#     "rephrase",
#     "simplify",
#     "easy language",
#     "simple language",

#     # language / tone changes
#     "hinglish",
#     "english me",
#     "hindi me",
#     "simple words"
# }


# def _is_follow_up(question: str) -> bool:
#     """Return True if the question looks like a follow‑up.

#     The detection is deliberately simple: if any of the defined keywords
#     appear anywhere in the lower‑cased question string we treat it as a
#     follow‑up. This matches the requirement to catch phrases such as
#     "short me explain karo" or "steps batao".
#     """
#     ql = question.lower()
#     return any(kw in ql for kw in FOLLOW_UP_KEYWORDS)


# GREETING_KEYWORDS = {
#     "hi",
#     "hello",
#     "hey",
#     "how are you",
#     "good morning",
#     "good afternoon",
#     "good evening",
# }


# def _is_greeting(question: str) -> bool:
#     ql = question.lower().strip()
#     # simple checks: exact phrases or startswith common greetings
#     if not ql:
#         return False
#     for kw in GREETING_KEYWORDS:
#         if ql == kw or ql.startswith(kw + " ") or ql.startswith(kw + "!") or ql.startswith(kw + ","):
#             return True
#     return False
# # Basic config (via .env or defaults)
# QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
# COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

# # ===== PRIMARY MODEL: OpenAI GPT-4o-mini =====
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# CHAT_MODEL_PROVIDER = os.getenv("CHAT_MODEL_PROVIDER", "openai")
# CHAT_MODEL_PRIMARY = os.getenv("CHAT_MODEL_PRIMARY", "gpt-4o-mini")

# # ===== FALLBACK MODEL: OpenRouter =====
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# CHAT_MODEL_FALLBACK = os.getenv("CHAT_MODEL_FALLBACK", "mistralai/mistral-7b-instruct:free")
# FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "openrouter")

# # Legacy support
# CHAT_MODEL = os.getenv("CHAT_MODEL", CHAT_MODEL_PRIMARY)
# OPENROUTER_FALLBACK_MODELS = os.getenv("OPENROUTER_FALLBACK_MODELS", "").strip()
# OLLAMA_FALLBACK = os.getenv("OLLAMA_FALLBACK", "false").lower() in ("1", "true", "yes")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

# if not OPENAI_API_KEY and not OPENROUTER_API_KEY:
#     print("Warning: Neither OPENAI_API_KEY nor OPENROUTER_API_KEY set in .env — chat calls will fail.")
# if OPENAI_API_KEY:
#     print("✓ OpenAI API key detected (using GPT-4o-mini as primary)")
# if OPENROUTER_API_KEY:
#     print("✓ OpenRouter API key detected (using as fallback)")

# # System prompt (improved, step-aware)
# SYSTEM_PROMPT = """
# You are the QuotePlan Support Assistant.

# Your job is to answer user questions using ONLY the information provided in CONTEXT and present it in a clean, professional chatbot UI format.

# You must FIRST understand:
# • What the user is asking for
# • Whether it is a procedure, explanation, or lookup
# • Whether the topic is narrow or broad
# • How much emphasis or clarity is required

# STRICT CONTENT RULES:

# Use ONLY the information found in CONTEXT.

# CRITICAL: COMPLETE ANSWER REQUIREMENT
# You MUST provide COMPLETE answers with ALL steps and details from the CONTEXT.
# DO NOT truncate, summarize, or skip any steps.
# DO NOT give partial answers - include EVERY step mentioned in the CONTEXT.
# If the CONTEXT contains 18 steps, you MUST include all 18 steps.
# If the CONTEXT contains detailed explanations, you MUST include all of them.
# Never guess, infer, assume, or add missing details.

# If the answer is not available in CONTEXT, reply EXACTLY:
# I don’t have this information in the QuotePlan manual.

# Do NOT mention CONTEXT, documents, system rules, or internal logic.

# FORMATTING RULES:
# Markdown is NOT allowed EXCEPT for bold text only.
# Do NOT use italics, headings, code blocks, or markdown lists.
# Use bold only when it improves clarity.
# Do NOT overuse bold.

# WHEN TO USE BOLD:
# Use bold only for:
# • Important button names or final actions
# • Key UI labels
# • Critical warnings or confirmations

# Do NOT bold:
# • Titles or headings (NO titles should be used)
# • Entire sentences
# • Every step
# • Normal instructional text
# • Introduction/context lines

# FORMAT INTELLIGENCE:
# Do NOT use a fixed answer format.
# Choose the format based on user intent and data size:
# • Simple task → compact steps
# • Complex or sensitive task → expanded steps
# • Explanation → short paragraph
# • Mixed → steps with light explanation

# PROCEDURE MODE:
# If steps or actions are required, treat the response as a procedure.

# CRITICAL FOR PROCEDURES:
# When providing procedures or step-by-step instructions:
# • You MUST include ALL steps from the CONTEXT - do not skip any step
# • If CONTEXT has 18 steps, include all 18 steps
# • If CONTEXT has detailed sub-steps, include all sub-steps
# • Do NOT summarize or condense steps - list them all
# • Do NOT stop early - continue until all steps are included

# COMPACT MODE (DEFAULT):
# Use compact mode when:
# • The user asks "how to"
# • The task is common or routine

# Compact format:
# • Start with 1-2 lines explaining what this process is about (context/introduction)
# • Then numbered steps immediately after (no blank line after intro)
# • Number + one symbol on the same line
# • Steps must be consecutive with NO blank lines between them - write steps one after another
# • Each step on a single line with minimal spacing
# • Use single line break (\n) only, never double line breaks between steps
# • NO bold title or heading
# • Include ALL steps from CONTEXT - do not truncate

# EXPANDED MODE:
# Use expanded mode when:
# • The user asks for detail or explanation
# • The process is long, complex, or risky

# Expanded format:
# • Start with 1-2 lines explaining what this process is about (context/introduction)
# • One blank line after intro
# • Numbered steps
# • Each step starts with one symbol
# • Minimal spacing between steps (only one blank line maximum if step is very long)
# • NO bold title or heading
# • Include ALL steps from CONTEXT - do not truncate or skip any step

# INTELLIGENT MULTIPLE METHODS HANDLING:

# STEP 1: UNDERSTAND THE QUESTION
# Before answering, carefully analyze the user's question to determine:
# • Does the question mention a specific method, module, or approach? (e.g., "create PO from PR", "using MRP", "in PO Module")
# • Is the question general without specifying a method? (e.g., "how to create PO", "how to create timesheet")
# • What keywords or context clues are in the question?

# STEP 2: ANALYZE CONTEXT FOR MULTIPLE METHODS
# Read ALL chunks in CONTEXT completely and identify:
# • Are there multiple methods/approaches described? (Look for numbered sections like 14.1, 14.2, 14.3, module names, or phrases like "multiple methods", "different ways")
# • What are the different methods available?
# • Which method best matches the user's question based on keywords and context?

# STEP 3: DECISION LOGIC

# CASE A: QUESTION IS SPECIFIC (mentions method/module/context)
# If the user's question contains specific indicators like:
# • Module names: "PO Module", "PR Module", "MRP", "MM Module", "Material Management"
# • Method indicators: "from PR", "using MRP", "through MRP", "via Purchase Requisition"
# • Context clues: "convert", "generate", "create from", "using [specific method]"

# THEN:
# • Find the matching method in CONTEXT
# • Provide COMPLETE steps for that specific method
# • Include ALL steps - do not truncate
# • Do NOT ask for clarification - the user has already specified their intent

# CASE B: QUESTION IS GENERAL (no specific method mentioned)
# If the user's question is general (e.g., "how to create PO", "how to create timesheet") AND multiple methods exist in CONTEXT:

# FIRST, try to provide the BEST/MOST COMMON method:
# • If one method is clearly the primary/default method in CONTEXT, provide complete steps for that method
# • Include ALL steps for that method
# • At the end, mention: "Note: There are other methods available. Would you like to know about [list other methods]?"

# ONLY if you cannot determine the best method OR if all methods are equally valid:
# • Ask for clarification using this format:
#   "There are multiple ways to [action]. Which method would you like to use?"
  
#   1. [Method 1 name] - [brief description]
#   2. [Method 2 name] - [brief description]
#   3. [Method 3 name] - [brief description]

# CRITICAL RULES:
# • ALWAYS provide COMPLETE answers with ALL steps - never truncate
# • Try to be helpful first - provide the best answer based on question analysis
# • Only ask for clarification if truly necessary (general question + multiple equally valid methods)
# • When providing a specific method, include ALL steps from CONTEXT for that method
# • When listing multiple methods for clarification, keep it brief and clear

# FOLLOW-UP HANDLING:
# If the user says “short me”, “detail me”, “same cheez”, or similar:
# Modify ONLY the previous response.
# Do NOT add new information.

# PROACTIVE FOLLOW-UP RULE (MANDATORY):

# After completing an answer:
# • If the topic is informational or exploratory
# • And the user has not asked a final or closed question

# You MUST ask exactly ONE short, relevant follow-up question.

# The follow-up question must:
# • Be directly related to the user’s question
# • Help clarify intent OR suggest the next logical step
# • Be optional and non-pushy
# • Be a single sentence

# Do NOT ask follow-up questions when:
# • The user asks a yes/no question
# • The user asks for a final action
# • The task is purely procedural and complete

# Follow-up question format:
# • Place it on a new line after the answer
# • No bold
# • No symbols
# • End with a question mark

# SAFETY:
# If an action may cause data loss or is irreversible, include a bold ⚠️ warning.

# OUTPUT RULE:
# Output ONLY the final formatted answer text.
# No greetings.
# No sign-offs.
# No filler text.

# """

# # Initialize Qdrant client
# #qdrant = QdrantClient(url=QDRANT_HOST)
# QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# qdrant = QdrantClient(
#     url=QDRANT_HOST,
#     api_key=QDRANT_API_KEY,   # <-- NEW
# )

# # Load local embedding model if available
# print("Loading local embedding model (all-MiniLM-L6-v2) ...")
# try:
#     from sentence_transformers import SentenceTransformer
#     embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
#     EMBEDDING_DIM = 384
#     print("Loaded all-MiniLM-L6-v2")
# except Exception as e:
#     print(f"Could not load local embedding model: {e}")
#     embedding_model = None
#     EMBEDDING_DIM = 384  # fallback dimension


# def embed_text(text):
#     """Return embedding vector (list of floats). Uses local model if available."""
#     if embedding_model:
#         emb = embedding_model.encode(text)
#         try:
#             return emb.tolist()
#         except Exception:
#             return list(map(float, emb))
#     # fallback: zero vector (not ideal, but prevents crashes)
#     return [0.0] * EMBEDDING_DIM


# def _qdrant_search_flexible(query_vector, top_k=5):
#     """
#     Use available qdrant-client method to search. Tries several possible APIs for compatibility:
#       - qdrant.search(...)
#       - qdrant.search_points(...)
#       - qdrant.query_points(...)
#     Returns list of hits with attributes id, payload, score (if available).
#     """
#     # Try qdrant.search (common)
#     try:
#         hits = qdrant.search(
#             collection_name=COLLECTION_NAME,
#             query_vector=query_vector,
#             limit=top_k,
#             with_payload=True,
#         )
#         return hits
#     except Exception:
#         pass

#     # Try qdrant.search_points
#     try:
#         hits = qdrant.search_points(
#             collection_name=COLLECTION_NAME,
#             vector=query_vector,
#             limit=top_k,
#             with_payload=True,
#         )
#         return hits
#     except Exception:
#         pass

#     # Try qdrant.query_points (older/newer variants)
#     try:
#         res = qdrant.query_points(
#             collection_name=COLLECTION_NAME,
#             query=query_vector,
#             limit=top_k,
#             with_payload=True,
#         )
#         # some query_points return an object with .points
#         if hasattr(res, "points"):
#             return res.points
#         return res
#     except Exception:
#         pass

#     raise RuntimeError("Unable to call Qdrant search API — check qdrant-client version.")


# def search_qdrant(query_embedding, top_k=5):
#     """Search Qdrant and return list of dicts: { id, text, score }."""
#     hits = _qdrant_search_flexible(query_embedding, top_k=top_k)
#     results = []
#     for hit in hits:
#         # `hit` might be a dict-like or object; be defensive
#         try:
#             hit_id = getattr(hit, "id", None) or hit.get("id", None)
#         except Exception:
#             hit_id = None
#         try:
#             payload = getattr(hit, "payload", None) or hit.get("payload", None)
#         except Exception:
#             payload = None
#         try:
#             score = getattr(hit, "score", None) or hit.get("score", None)
#         except Exception:
#             score = None

#         text = None
#         if payload:
#             # payload may be a dict with 'text'
#             text = payload.get("text") if isinstance(payload, dict) else getattr(payload, "get", lambda k: None)("text")
#         results.append({"id": hit_id, "text": text, "score": score})
#     return results


# def call_chat_api(question, context_chunks):
#     """
#     Call chat API with primary model (OpenAI GPT-4o-mini) and fallback to OpenRouter.
#     Returns the natural answer text (no JSON enforcing).
#     """
#     # Build context text
#     context_text = "\n\n---\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks)])

#     # Enhanced user message with intelligent method selection instructions
#     user_message = f"""CONTEXT:
# {context_text}

# INSTRUCTIONS:
# 1. Read ALL chunks in CONTEXT completely - do not skip any chunk
# 2. Analyze the user's question carefully to identify:
#    - Does it mention a specific method/module? (e.g., "from PR", "using MRP", "PO Module")
#    - Is it a general question? (e.g., "how to create PO")
# 3. If the question is SPECIFIC (mentions method/module):
#    - Find the matching method in CONTEXT
#    - Provide COMPLETE steps for that specific method
#    - Include ALL steps - do not truncate
#    - Do NOT ask for clarification
# 4. If the question is GENERAL and multiple methods exist:
#    - FIRST try to provide the best/most common method with ALL steps
#    - Only ask for clarification if you cannot determine the best method
# 5. ALWAYS provide COMPLETE answers with ALL steps - never truncate or skip steps

# Question: {question}"""

#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": user_message}
#     ]

#     # Try OpenAI first if API key is available
#     if OPENAI_API_KEY:
#         try:
#             print(f"[Primary] Attempting OpenAI GPT-4o-mini...")
#             response = call_openai(messages)
#             print(f"[Primary] OpenAI success!")
#             return response
#         except Exception as e:
#             print(f"[Primary] OpenAI failed: {e}. Attempting fallback...")

#     # Fall back to OpenRouter if available
#     if OPENROUTER_API_KEY:
#         try:
#             print(f"[Fallback] Attempting OpenRouter {CHAT_MODEL_FALLBACK}...")
#             response = call_openrouter(messages, CHAT_MODEL_FALLBACK)
#             print(f"[Fallback] OpenRouter success!")
#             return response
#         except Exception as e:
#             print(f"[Fallback] OpenRouter failed: {e}")

#     # Final fallback to local Ollama if enabled
#     if OLLAMA_FALLBACK:
#         try:
#             print("[Fallback] Attempting local Ollama...")
#             return call_local_ollama(question, context_chunks, model=OLLAMA_MODEL)
#         except Exception as e:
#             print(f"[Fallback] Ollama failed: {e}")

#     raise Exception("All chat API options exhausted (OpenAI, OpenRouter, and Ollama all failed or unavailable)")


# def call_openai(messages):
#     """
#     Call OpenAI API for chat completions.
#     """
#     url = "https://api.openai.com/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {OPENAI_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "model": "gpt-4o-mini",
#         "messages": messages,
#         "max_tokens": 3000,  # Increased to allow complete answers with all steps
#         "temperature": 0.0
#     }

#     r = requests.post(url, headers=headers, json=payload, timeout=60)
#     r.raise_for_status()
#     content = r.json()["choices"][0]["message"]["content"]
    
#     if isinstance(content, dict):
#         return json.dumps(content, ensure_ascii=False)
#     return content.strip()


# def call_openrouter(messages, model):
#     """
#     Call OpenRouter API for chat completions with specified model.
#     """
#     url = "https://openrouter.ai/api/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "model": model,
#         "messages": messages,
#         "max_tokens": 3000,  # Increased to allow complete answers with all steps
#         "temperature": 0.0
#     }

#     r = requests.post(url, headers=headers, json=payload, timeout=60)
#     r.raise_for_status()
#     content = r.json()["choices"][0]["message"]["content"]
    
#     if isinstance(content, dict):
#         return json.dumps(content, ensure_ascii=False)
#     return content.strip()

# def _call_chat_api_followup(prev_answer: str, question: str):
#     """Call chat API for follow-up using only the previous answer.

#     The system prompt stays the same, but the user message is rewritten to
#     instruct the model to base its response solely on the provided previous
#     answer. Tries OpenAI first, then falls back to OpenRouter.
#     """
#     user_content = (
#         "Based only on the previous answer below, respond to the user request.\n\n"
#         f"Previous answer:\n{prev_answer}\n\nQuestion: {question}"
#     )
#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": user_content}
#     ]

#     # Try OpenAI first if API key is available
#     if OPENAI_API_KEY:
#         try:
#             print(f"[Follow-up] Attempting OpenAI...")
#             return call_openai(messages)
#         except Exception as e:
#             print(f"[Follow-up] OpenAI failed: {e}. Attempting fallback...")

#     # Fall back to OpenRouter if available
#     if OPENROUTER_API_KEY:
#         try:
#             print(f"[Follow-up] Attempting OpenRouter {CHAT_MODEL_FALLBACK}...")
#             return call_openrouter(messages, CHAT_MODEL_FALLBACK)
#         except Exception as e:
#             print(f"[Follow-up] OpenRouter failed: {e}")

#     # Final fallback to local Ollama if enabled
#     if OLLAMA_FALLBACK:
#         try:
#             print("[Follow-up] Attempting local Ollama...")
#             return call_local_ollama(question, [{"text": prev_answer}], model=OLLAMA_MODEL)
#         except Exception as e:
#             print(f"[Follow-up] Ollama failed: {e}")

#     raise Exception("All chat API options exhausted for follow-up")


# def call_local_ollama(question, context_chunks, model="mistral:7b"):
#     """
#     Best-effort attempt to call local Ollama (CLI or HTTP) and return text output.
#     This is optional and will only be used if configured via OLLAMA_FALLBACK.
#     """
#     prompt_text = "\n\n---\n\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks)])
#     full_prompt = f"CONTEXT:\n{prompt_text}\n\nQuestion: {question}\n\nAnswer in natural text."

#     # Try CLI first
#     try:
#         import subprocess, shlex
#         cmd = ["ollama", "generate", model, "--prompt", full_prompt]
#         proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
#         if proc.returncode == 0 and proc.stdout:
#             return proc.stdout.strip()
#     except FileNotFoundError:
#         pass
#     except Exception as e:
#         print(f"Ollama CLI attempt failed: {e}")

#     # Try local Ollama HTTP endpoint
#     try:
#         url = os.getenv("OLLAMA_HTTP_URL", "http://localhost:11434/api/generate")
#         payload = {"model": model, "prompt": full_prompt}
#         r = requests.post(url, json=payload, timeout=60)
#         r.raise_for_status()
#         # Attempt to return 'response' or raw text
#         j = r.json()
#         if isinstance(j, dict) and "response" in j:
#             return j["response"]
#         return json.dumps(j, ensure_ascii=False)
#     except Exception as e:
#         raise Exception(f"Local Ollama fallback failed: {e}")


# def build_context(retrieved):
#     """Return the joined context text (for debugging / logging)"""
#     return "\n\n---\n\n".join([f"[{i+1}] {r['text']}" for i, r in enumerate(retrieved)])


# def answer_structured(question, top_k=15, verbose=True):
#     """Main entry for your server with simple in‑memory chat memory.

#     The function now distinguishes between a normal query and a follow‑up.
#     For follow‑ups we reuse the previous answer and skip the embedding /
#     Qdrant search steps.
#     """
#     try:
#         # Detect follow‑up request
#         is_follow = _is_follow_up(question)
#         # Retrieve previous memory if any
#         prev = CHAT_MEMORY.get("last_answer")

#         # Greeting handling: respond locally to simple greetings without using the LLM
#         if _is_greeting(question):
#             replies = [
#                 "Hi — I'm the QuotePlan Assistant. How can I help you today?",
#                 "Hello — I can help with QuotePlan documentation. What would you like to know?",
#                 "Hi there! Ask me about creating projects, BOMs, POs, or offer letters."
#             ]
#             answer_text = random.choice(replies)
#             CHAT_MEMORY["last_question"] = question
#             CHAT_MEMORY["last_answer"] = answer_text
#             retrieved = []
#             return {
#                 "success": True,
#                 "question": question,
#                 "answer": answer_text,
#                 "retrieved": retrieved,
#             }

#         if is_follow and prev:
#             # Follow‑up: use only previous answer
#             if verbose:
#                 print("[follow‑up] using previous answer for context")
#             answer_text = _call_chat_api_followup(prev, question)
#             # No retrieved chunks for follow‑up
#             retrieved = []
#         else:
#             # Normal RAG flow
#             if verbose:
#                 print("\n[embed] embedding question...")
#             q_emb = embed_text(question)

#             if verbose:
#                 print("[search] searching Qdrant...")
#             retrieved = search_qdrant(q_emb, top_k=top_k)

#             if not retrieved:
#                 answer_text = "I don’t have this information in the QuotePlan manual."
#             else:
#                 if verbose:
#                     print(f"[chat] calling chat api (model={CHAT_MODEL}) with {len(retrieved)} retrieved chunks...")
#                 answer_text = call_chat_api(question, retrieved)

#         # Store memory for next turn
#         CHAT_MEMORY["last_question"] = question
#         CHAT_MEMORY["last_answer"] = answer_text

#         return {
#             "success": True,
#             "question": question,
#             "answer": answer_text,
#             "retrieved": retrieved,
#         }

#     except Exception as e:
#         return {
#             "success": False,
#             "question": question,
#             "answer": f"Error: {e}",
#             "retrieved": [],
#         }


# def answer(question, top_k=5):
#     """Backward-compatible helper returning the answer string only."""
#     out = answer_structured(question, top_k=top_k, verbose=False)
#     return out.get("answer", "")


# # CLI
# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--q", required=True, help="User question in quotes")
#     parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
#     args = parser.parse_args()

#     if args.json:
#         res = answer_structured(args.q, verbose=True)
#         print(json.dumps(res, ensure_ascii=False, indent=2))
#     else:
#         print(f"\nQuestion: {args.q}\n")
#         print(answer(args.q))
#         print()



#!/usr/bin/env python3
"""
Query script for Qdrant + OpenAI/OpenRouter
PRODUCTION READY – Definition + Procedure SAFE
"""

import os
import json
import requests
import random
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# =========================
# PATHS & ENV
# =========================

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

CHAT_MEMORY = {}

# =========================
# CONFIG
# =========================

QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

CHAT_MODEL_PRIMARY = "gpt-4o-mini"
CHAT_MODEL_FALLBACK = "mistralai/mistral-7b-instruct:free"

# =========================
# GREETING & FOLLOW-UP
# =========================

GREETING_KEYWORDS = {
    "hi", "hello", "hey",
    "good morning", "good afternoon", "good evening"
}

FOLLOW_UP_KEYWORDS = {
    "short", "brief", "summary", "detail", "explain",
    "same", "wahi", "aur", "continue",
    "steps", "dubara", "repeat", "simplify"
}

def _is_greeting(q: str) -> bool:
    q = q.lower().strip()
    return any(q == g or q.startswith(g + " ") for g in GREETING_KEYWORDS)

def _is_follow_up(q: str) -> bool:
    q = q.lower()
    return any(k in q for k in FOLLOW_UP_KEYWORDS)

# =========================
# MODULE & INTENT DETECTOR
# =========================

def detect_module_and_intent(question: str):
    q = question.lower()

    module = None
    if "lead" in q:
        module = "Lead Management"
    elif "timesheet" in q:
        module = "Time Tracking"
    elif "bom" in q:
        module = "BOM"
    elif "po" in q or "purchase order" in q:
        module = "Purchase Order"

    intent = "general"
    if any(w in q for w in ["what is", "meaning", "definition", "matlab"]):
        intent = "definition"
    elif any(w in q for w in ["how", "steps", "create", "modify", "delete"]):
        intent = "procedure"

    return module, intent

# =========================
# EMBEDDINGS
# =========================

from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

def embed_text(text: str):
    emb = embedding_model.encode(text)
    return emb.tolist()

# =========================
# QDRANT
# =========================

qdrant = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY
)

def _perform_qdrant_search(query_embedding, question, top_k):
    module, intent = detect_module_and_intent(question)

    # 🔥 Apply strict filter ONLY for PROCEDURES (if indexes exist)
    # Note: Filters require indexes to be created in Qdrant
    # For now, we'll search without filters to avoid index errors
    # TODO: Add payload indexes in ingest script for better filtering
    q_filter = None
    # Disabled filter until indexes are created
    # if intent == "procedure":
    #     must = []
    #     if module:
    #         must.append({"key": "module", "match": {"value": module}})
    #     must.append({"key": "type", "match": {"value": "procedure"}})
    #     q_filter = {"must": must}

    common_kwargs = {
        "collection_name": COLLECTION_NAME,
        "limit": top_k,
        "with_payload": True,
    }
    
    # Only add filter if it's set (and indexes exist)
    if q_filter:
        common_kwargs["query_filter"] = q_filter

    # Try query_points first (most common in newer versions)
    if hasattr(qdrant, "query_points"):
        try:
            result = qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                limit=top_k,
                with_payload=True,
            )
            # Handle both response formats
            if hasattr(result, "points"):
                return result.points
            return result
        except Exception as e:
            print(f"[DEBUG] query_points failed: {e}")

    if hasattr(qdrant, "search"):
        try:
            return qdrant.search(
                **common_kwargs,
                query_vector=query_embedding
            )
        except Exception as e:
            print(f"[DEBUG] search failed: {e}")

    if hasattr(qdrant, "search_points"):
        try:
            return qdrant.search_points(
                **common_kwargs,
                vector=query_embedding
            )
        except Exception as e:
            print(f"[DEBUG] search_points failed: {e}")

    raise RuntimeError("Unable to call either search/search_points/query_points on QdrantClient")


def search_qdrant(query_embedding, question, top_k=8):
    try:
        hits = _perform_qdrant_search(query_embedding, question, top_k)
        
        # Handle case where hits might be None or empty
        if not hits:
            print(f"[DEBUG] _perform_qdrant_search returned empty/None")
            return []
        
        # Handle case where hits might be a generator or list
        if hasattr(hits, '__iter__'):
            hits = list(hits)
        else:
            print(f"[DEBUG] Hits is not iterable: {type(hits)}")
            return []
        
        results = []
        for h in hits:
            try:
                payload = getattr(h, "payload", None) or {}
                if not isinstance(payload, dict):
                    # Try to convert if it's not a dict
                    if hasattr(payload, '__dict__'):
                        payload = payload.__dict__
                    else:
                        payload = {}
                
                # Try different possible text fields from ingest script
                text = payload.get("text") or payload.get("view") or payload.get("answer") or ""
                
                if text:  # Only add if we have text
                    results.append(
                        {
                            "id": getattr(h, "id", None),
                            "text": text,
                            "score": getattr(h, "score", None),
                            "module": payload.get("module"),
                            "intent": payload.get("intent"),
                            "type": payload.get("type"),
                        }
                    )
            except Exception as e:
                print(f"[DEBUG] Error processing hit: {e}")
                continue
        
        return results
    except Exception as e:
        print(f"[DEBUG] Error in search_qdrant: {e}")
        import traceback
        traceback.print_exc()
        return []

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """You are the QuotePlan Support Assistant.

Your job is to answer user questions using ONLY the information provided in CONTEXT.

CRITICAL RULES:
1. Use ONLY the information found in CONTEXT - do not make up information
2. Provide COMPLETE answers with ALL steps if the CONTEXT contains procedures
3. If the CONTEXT has multiple steps, include ALL of them
4. Format answers clearly with numbered steps when procedures are involved
5. If the answer is truly not available in CONTEXT, reply exactly: "I don't have this information in the QuotePlan manual."

FORMATTING:
- Use numbered steps (1., 2., 3.) for procedures
- Be clear and concise
- Include all relevant details from CONTEXT
- Do NOT mention "CONTEXT" or "document" in your answer

Answer the user's question based on the CONTEXT provided.
"""

# =========================
# CHAT CALLS
# =========================

def call_openai(messages):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": CHAT_MODEL_PRIMARY,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 3000
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def call_openrouter(messages):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": CHAT_MODEL_FALLBACK,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 3000
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# =========================
# MAIN ANSWER FUNCTION
# =========================

def answer_structured(question, top_k=8):
    try:
        # Greeting
        if _is_greeting(question):
            reply = random.choice([
                "Hi — I’m the QuotePlan Assistant. How can I help?",
                "Hello! Ask me anything about QuotePlan."
            ])
            CHAT_MEMORY["last_answer"] = reply
            return {"success": True, "question": question, "answer": reply}

        # Follow-up
        if _is_follow_up(question) and CHAT_MEMORY.get("last_answer"):
            prev = CHAT_MEMORY["last_answer"]
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Previous answer:\n{prev}\n\nQuestion: {question}"}
            ]
            answer = call_openai(messages) if OPENAI_API_KEY else call_openrouter(messages)
            CHAT_MEMORY["last_answer"] = answer
            return {"success": True, "question": question, "answer": answer}

        # Normal RAG
        q_emb = embed_text(question)
        retrieved = search_qdrant(q_emb, question, top_k=top_k)
        
        print(f"[DEBUG] Retrieved {len(retrieved)} chunks for question: {question[:50]}...")
        if retrieved:
            print(f"[DEBUG] First chunk text preview: {retrieved[0].get('text', '')[:100]}...")

        # 🔁 Semantic fallback (definition-safe)
        if not retrieved:
            print(f"[DEBUG] No results, trying fallback search...")
            try:
                fallback_hits = _perform_qdrant_search(q_emb, question, top_k=10)
                print(f"[DEBUG] Fallback search returned {len(fallback_hits) if fallback_hits else 0} hits")
                retrieved = []
                for h in fallback_hits:
                    payload = getattr(h, "payload", None) or {}
                    if not isinstance(payload, dict):
                        payload = {}
                    text = payload.get("text") or payload.get("view") or payload.get("answer") or ""
                    if text:
                        retrieved.append({"text": text})
            except Exception as e:
                print(f"[DEBUG] Fallback search failed: {e}")
                import traceback
                traceback.print_exc()

        if not retrieved:
            print(f"[DEBUG] No chunks found. Collection: {COLLECTION_NAME}, Question: {question}")
            # Try to check if collection exists and has data
            try:
                collections = qdrant.get_collections()
                collection_names = [c.name for c in collections.collections]
                print(f"[DEBUG] Available collections: {collection_names}")
                if COLLECTION_NAME in collection_names:
                    info = qdrant.get_collection(COLLECTION_NAME)
                    print(f"[DEBUG] Collection {COLLECTION_NAME} has {info.points_count} points")
            except Exception as e:
                print(f"[DEBUG] Error checking collection: {e}")
            answer = "I don't have this information in the QuotePlan manual."
        else:
            # Use text field, fallback to view if text is empty
            context_parts = []
            for i, r in enumerate(retrieved):
                text = r.get("text") or r.get("view") or ""
                if text:
                    context_parts.append(text)
                else:
                    print(f"[DEBUG] Chunk {i} has no text. Keys: {list(r.keys())}")
            
            print(f"[DEBUG] Built {len(context_parts)} context parts from {len(retrieved)} retrieved chunks")
            
            if not context_parts:
                print(f"[DEBUG] No context parts extracted! Retrieved chunks: {retrieved[:2]}")
                answer = "I don't have this information in the QuotePlan manual."
            else:
                context = "\n\n".join(context_parts)
                print(f"[DEBUG] Context length: {len(context)} characters")
                print(f"[DEBUG] Context preview: {context[:200]}...")
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"CONTEXT:\n{context}\n\nQuestion: {question}"}
                ]
                try:
                    print(f"[DEBUG] Calling LLM API...")
                    answer = call_openai(messages) if OPENAI_API_KEY else call_openrouter(messages)
                    print(f"[DEBUG] LLM response length: {len(answer)} characters")
                    print(f"[DEBUG] LLM response preview: {answer[:200]}...")
                except Exception as e:
                    print(f"[DEBUG] LLM API call failed: {e}")
                    import traceback
                    traceback.print_exc()
                    answer = f"Error generating answer: {str(e)}"

        CHAT_MEMORY["last_answer"] = answer
        return {"success": True, "question": question, "answer": answer}

    except Exception as e:
        return {"success": False, "question": question, "answer": str(e)}

def answer(question: str) -> str:
    return answer_structured(question)["answer"]

# =========================
# CLI
# =========================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", required=True)
    args = parser.parse_args()
    print(answer(args.q))
