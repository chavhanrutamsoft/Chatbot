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
# You are the QuotePlan Support Assistant, an expert AI assistant specialized in providing accurate, complete, and helpful answers about the QuotePlan software system.

# CORE PRINCIPLES:
# 1. ACCURACY FIRST: Only use information explicitly stated in the CONTEXT. Never infer, assume, or add information not present in CONTEXT.
# 2. COMPLETENESS: Provide complete answers with all relevant details from CONTEXT. Include all steps, all conditions, and all important information.
# 3. PRECISION: Match the user's intent exactly. If they ask "how to create", provide creation steps. If they ask "what is", provide definitions/explanations.
# 4. CLARITY: Write in clear, natural language that is easy to understand. Use proper formatting when CONTEXT contains structured information.

# STRICT CONTENT RULES:
# - Use ONLY information from CONTEXT. Never guess, infer, or add missing details.
# - If CONTEXT contains multiple methods or approaches, identify which one matches the user's question best.
# - If CONTEXT has numbered steps, include ALL steps in the correct order.
# - If CONTEXT has detailed explanations, include all relevant details.
# - Extract information even from partial matches - if CONTEXT mentions the topic in any way, use that information.

# ANSWER FORMATTING:
# - For PROCEDURES: Provide numbered steps (1., 2., 3., etc.) with clear, actionable instructions.
# - For DEFINITIONS: Provide clear explanations in natural paragraph format.
# - For MIXED CONTENT: Use appropriate formatting - steps for procedures, paragraphs for explanations.
# - Use bold sparingly only for critical UI elements, button names, or warnings.
# - Do NOT use markdown headings, code blocks, or excessive formatting.

# HANDLING MISSING INFORMATION:
# - If CONTEXT contains ANY mention of the topic (even partial), extract and provide that information.
# - Only say "I don't have this information in the QuotePlan manual" if CONTEXT has ZERO mentions of the topic.
# - When CONTEXT is partially relevant, extract what is available and state it clearly.

# OUTPUT REQUIREMENTS:
# - Output ONLY the final answer text.
# - No greetings, no sign-offs, no meta-commentary.
# - No JSON, no structured wrappers, no system messages.
# - Direct, helpful, and complete answers only.

# Remember: Your goal is to provide the most accurate, complete, and helpful answer possible using ONLY the information in CONTEXT.
# """

import os
import json
import requests
import random
import re
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from logger_config import logger

# =========================
# PATHS & ENV
# =========================

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env")

# File to store unanswered questions
UNANSWERED_QUESTIONS_FILE = DATA_DIR / "unanswered_questions.json"

CHAT_MEMORY = {}

# =========================
# CONFIG
# =========================

QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "quoteplan_chunks")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

CHAT_MODEL_PRIMARY = "gpt-4o"
CHAT_MODEL_FALLBACK = "mistralai/mistral-7b-instruct:free"

# LLM / retrieval tuning (production defaults, override via .env)
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
MAX_CONTEXT_PARTS = int(os.getenv("MAX_CONTEXT_PARTS", "24"))
MAX_VARIATION_SEARCHES = int(os.getenv("MAX_VARIATION_SEARCHES", "3"))

# Reuse one session for lower latency
HTTP_SESSION = requests.Session()

# =========================
# GREETING & FOLLOW-UP
# =========================

GREETING_KEYWORDS = {
    "hi", "hello", "hey","hi there", "hello there", "hey there", "hi there", "hello there", "hey there", "hi there", "hello there", "hey there",
    "good morning", "good afternoon", "good evening","good morning there", "good afternoon there", "good evening there", "good morning there", "good afternoon there", "good evening there", "good morning there", "good afternoon there", "good evening there",
}

FOLLOW_UP_KEYWORDS = {
    "short", "brief", "summary", "detail", "explain",
    "same", "wahi", "aur", "continue",
    "steps", "dubara", "repeat", "simplify"
}

YES_RESPONSES = {
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "alright", "alrighty",
    "absolutely", "definitely", "of course", "please", "go ahead"
}

def _is_greeting(q: str) -> bool:
    q = q.lower().strip()
    return any(q == g or q.startswith(g + " ") for g in GREETING_KEYWORDS)

def _is_follow_up(q: str) -> bool:
    q = q.lower()
    return any(k in q for k in FOLLOW_UP_KEYWORDS)

def _is_yes_response(q: str) -> bool:
    """Check if the question is a yes/affirmative response."""
    q = q.lower().strip()
    # Remove punctuation
    q = q.rstrip('.!?,;:')
    return q in YES_RESPONSES

def _extract_followup_question_from_answer(answer: str) -> str:
    """Extract the follow-up question from the previous answer."""
    if not answer:
        return None
    
    # Split by lines and get the last few lines
    lines = answer.strip().split('\n')
    
    # Look for question marks in the last 3 lines (follow-up questions are usually at the end)
    for line in reversed(lines[-3:]):
        line = line.strip()
        if '?' in line and len(line) > 10:  # Must have question mark and be substantial
            # Check if it's a follow-up question pattern
            lower_line = line.lower()
            if any(phrase in lower_line for phrase in ["would you like", "do you want", "would you like to know", "do you need"]):
                return line
            # Also check if it ends with a question mark and seems like a question
            if line.endswith('?'):
                return line
    
    return None

def _extract_main_topic_from_question(question: str) -> str:
    """Extract the main topic/noun from a question like 'how to create timesheet' -> 'timesheet'"""
    if not question:
        return None
    
    q_lower = question.lower()
    
    # Remove common question prefixes
    for prefix in ["how to", "how do i", "how can i", "what is", "what's", "what are", "where is", "when is", "why is"]:
        if q_lower.startswith(prefix):
            q_lower = q_lower[len(prefix):].strip()
            break
    
    # Remove common verbs/operations
    for verb in ["create", "modify", "edit", "delete", "remove", "view", "add", "update", "change"]:
        if q_lower.startswith(verb):
            q_lower = q_lower[len(verb):].strip()
            break
    
    # Get the main noun (usually the last meaningful word or phrase)
    words = q_lower.split()
    if words:
        # Return the main topic (could be multiple words like "business entity")
        return " ".join(words[:3])  # Take up to 3 words as the topic
    
    return None

def _extract_topic_from_followup_question(followup_q: str, previous_question: str = None) -> str:
    """Extract the topic/question from a follow-up question like 'Would you like to know how to view leads?'
    If the topic contains 'this', 'it', 'that', replace it with the topic from previous_question."""
    if not followup_q:
        return None
    
    # Common patterns:
    # "Would you like to know how to [topic]?"
    # "Do you want to [topic]?"
    # "Would you like help with [topic]?"
    
    followup_lower = followup_q.lower()
    
    # Extract topic after common phrases
    patterns = [
        r"would you like to know how to (.+?)\?",
        r"do you want to know how to (.+?)\?",
        r"would you like to (.+?)\?",
        r"do you want to (.+?)\?",
        r"would you like help with (.+?)\?",
        r"do you need to (.+?)\?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, followup_lower)
        if match:
            topic = match.group(1).strip()
            
            # If topic contains pronouns like "this", "it", "that", replace with actual topic
            if previous_question and any(pronoun in topic.lower() for pronoun in ["this", "it", "that"]):
                main_topic = _extract_main_topic_from_question(previous_question)
                if main_topic:
                    # Replace pronouns with the actual topic
                    topic = re.sub(r'\b(this|it|that)\b', main_topic, topic, flags=re.IGNORECASE).strip()
                    logger.debug(f"Replaced pronoun in topic, new topic: {topic}")
            
            # Convert to question format
            if not topic.startswith(("how", "what", "where", "when", "why", "who")):
                topic = f"how to {topic}"
            return topic
    
    # Fallback: just extract the main content before the question mark
    # Remove common question prefixes
    cleaned = followup_q.lower()
    for prefix in ["would you like to know", "do you want to know", "would you like to", "do you want to", "would you like help with"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    
    cleaned = cleaned.rstrip('?').strip()
    if cleaned:
        # Handle pronouns
        if previous_question and any(pronoun in cleaned for pronoun in ["this", "it", "that"]):
            main_topic = _extract_main_topic_from_question(previous_question)
            if main_topic:
                cleaned = re.sub(r'\b(this|it|that)\b', main_topic, cleaned, flags=re.IGNORECASE).strip()
        
        if not cleaned.startswith(("how", "what", "where", "when", "why", "who")):
            cleaned = f"how to {cleaned}"
        return cleaned
    
    return None

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
    # Enhanced definition detection
    if any(w in q for w in ["what is", "what's", "meaning", "definition", "define", "matlab", "kya hai", "kya hota hai", "explain what"]):
        intent = "definition"
    # Enhanced procedure detection
    elif any(w in q for w in ["how", "steps", "step", "create", "modify", "delete", "process", "procedure", "kaise", "karne", "banane"]):
        intent = "procedure"

    return module, intent

# =========================
# EMBEDDINGS
# =========================

from sentence_transformers import SentenceTransformer

logger.info("Loading embedding model (all-mpnet-base-v2)")
try:
    embedding_model = SentenceTransformer("all-mpnet-base-v2")
    EMBEDDING_DIM = 768
    logger.info("Embedding model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load embedding model: {e}")
    raise

def embed_text(text: str):
    """Generate embedding vector for text."""
    try:
        emb = embedding_model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return emb.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise

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
            logger.debug(f"query_points failed: {e}")

    if hasattr(qdrant, "search"):
        try:
            return qdrant.search(
                **common_kwargs,
                query_vector=query_embedding
            )
        except Exception as e:
            logger.debug(f"search failed: {e}")

    if hasattr(qdrant, "search_points"):
        try:
            return qdrant.search_points(
                **common_kwargs,
                vector=query_embedding
            )
        except Exception as e:
            logger.debug(f"search_points failed: {e}")

    raise RuntimeError("Unable to call either search/search_points/query_points on QdrantClient")


def search_qdrant(query_embedding, question, top_k=8):
    try:
        # Increase top_k significantly for better coverage - production level
        initial_top_k = max(top_k * 3, 75)  # Get 3x more results or minimum 75
        hits = _perform_qdrant_search(query_embedding, question, initial_top_k)
        
        # Handle case where hits might be None or empty
        if not hits:
            logger.debug("_perform_qdrant_search returned empty/None")
            return []
        
        # Handle case where hits might be a generator or list
        if hasattr(hits, '__iter__'):
            hits = list(hits)
        else:
            logger.debug(f"Hits is not iterable: {type(hits)}")
            return []
        
        # Detect question intent for intelligent re-ranking
        question_lower = question.lower()
        module, intent = detect_module_and_intent(question)
        is_definition = intent == "definition" or any(w in question_lower for w in ["what is", "what's", "meaning", "define", "kya hai"])
        is_procedure = intent == "procedure" or any(w in question_lower for w in ["how", "steps", "process", "kaise", "create", "make"])
        
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
                    chunk_type = payload.get("type", "raw")
                    score = getattr(h, "score", None) or 0.0
                    
                    # Intelligent re-ranking: boost relevant chunks based on operation and type
                    text_lower = text.lower()
                    
                    # Boost chunks that match the operation (create/modify/delete)
                    if "create" in question_lower or "add" in question_lower:
                        if "create" in text_lower or "add" in text_lower or "new" in text_lower:
                            score = score * 1.2
                        elif "modify" in text_lower or "edit" in text_lower or "update" in text_lower:
                            score = score * 0.7  # Penalize modify chunks for create questions
                    elif "modify" in question_lower or "edit" in question_lower or "update" in question_lower:
                        if "modify" in text_lower or "edit" in text_lower or "update" in text_lower or "change" in text_lower:
                            score = score * 1.2
                        elif "create" in text_lower or "add" in text_lower:
                            score = score * 0.7  # Penalize create chunks for modify questions
                    
                    # Boost by chunk type
                    if is_definition and chunk_type in ["definition", "meaning", "qa"]:
                        score = score * 1.1
                    elif is_procedure and chunk_type == "procedure":
                        score = score * 1.1
                    
                    results.append(
                        {
                            "id": getattr(h, "id", None),
                            "text": text,
                            "score": score,
                            "module": payload.get("module"),
                            "intent": payload.get("intent"),
                            "type": chunk_type,
                        }
                    )
            except Exception as e:
                logger.debug(f"Error processing hit: {e}")
                continue
        
        # Sort by boosted score and return top_k
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return results[:top_k]
    except Exception as e:
        logger.error(f"Error in search_qdrant: {e}", exc_info=True)
        return []


def _hash_text(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def _merge_retrievals(primary, additions):
    """Merge retrieval lists, keeping the highest score per unique text."""
    merged = {}
    for item in (primary or []) + (additions or []):
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("view") or ""
        if not text:
            continue
        key = _hash_text(text)
        existing = merged.get(key)
        if not existing or item.get("score", 0.0) > existing.get("score", 0.0):
            merged[key] = item
    merged_list = list(merged.values())
    merged_list.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return merged_list


def _build_context_parts(retrieved, question, filter_low_score=True):
    """Build a bounded, deduplicated context list from retrieved chunks."""
    context_parts = []
    used_chars = 0
    seen = set()

    question_lower = question.lower()
    question_keywords = set(question_lower.split())
    main_keywords = []
    for kw in question_keywords:
        kw = kw.lower().strip()
        if kw not in {
            "what", "is", "the", "a", "an", "how", "to", "do", "does", "are", "can", "will", "would",
            "should", "could", "of", "in", "on", "at", "for", "with", "by"
        } and len(kw) > 2:
            main_keywords.append(kw)

    for i, r in enumerate(retrieved or []):
        text = (r.get("text") or r.get("view") or "").strip()
        if not text:
            continue

        key = _hash_text(text)
        if key in seen:
            continue

        score = r.get("score", 0.0)
        text_lower = text.lower()
        if filter_low_score and score < 0.2 and len(main_keywords) > 3:
            has_keyword_match = any(kw in text_lower for kw in main_keywords if len(kw) > 3)
            if not has_keyword_match:
                variations_map = {
                    "grn": ["goods receipt", "grn", "receipt note"],
                    "bom": ["bill of materials", "bom"],
                    "timesheet": ["time sheet", "timesheet", "time tracking"],
                    "stock": ["inventory", "stock", "current stock", "view current stock"],
                    "synch": ["sync", "synchronize", "synch"],
                    "calculate": ["calculation", "compute", "calculate", "view"],
                    "rejected": ["reject", "rejection", "rejected"],
                    "admin": ["administrator", "admin"],
                    "labor": ["labor code", "labor", "labour"],
                    "user": ["user created", "user-created", "created by"],
                }
                has_variation_match = False
                for term, vars_list in variations_map.items():
                    if term in question_lower and any(var in text_lower for var in vars_list):
                        has_variation_match = True
                        break
                if not has_variation_match:
                    logger.debug(f"Chunk {i} filtered out - very low relevance (score: {score:.2f})")
                    continue

        remaining = MAX_CONTEXT_CHARS - used_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            if remaining < 200:
                break
            text = text[:remaining]

        context_parts.append(text)
        used_chars += len(text)
        seen.add(key)

        if len(context_parts) >= MAX_CONTEXT_PARTS:
            break

    logger.debug(f"Built {len(context_parts)} context parts from {len(retrieved or [])} retrieved chunks")
    return context_parts

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are the QuotePlan Support Assistant, an expert AI assistant specialized in providing accurate, complete, and helpful answers about the QuotePlan software system.

CORE PRINCIPLES:
1. ACCURACY FIRST: Only use information explicitly stated in the CONTEXT. Never infer, assume, or add information not present in CONTEXT.
2. COMPLETENESS: Provide complete answers with all relevant details from CONTEXT. Include all steps, all conditions, and all important information.
3. PRECISION: Match the user's intent exactly. If they ask "how to create", provide creation steps. If they ask "what is", provide definitions/explanations.
4. CLARITY: Write in clear, natural language that is easy to understand. Use proper formatting when CONTEXT contains structured information.

STRICT CONTENT RULES:
- Use ONLY information from CONTEXT. Never guess, infer, or add missing details.
- If CONTEXT contains multiple methods or approaches, identify which one matches the user's question best.
- If CONTEXT has numbered steps, include ALL steps in the correct order.
- If CONTEXT has detailed explanations, include all relevant details.
- Extract information even from partial matches - if CONTEXT mentions the topic in any way, use that information.

ANSWER FORMATTING:
- For PROCEDURES: Provide numbered steps (1., 2., 3., etc.) with clear, actionable instructions.
- For DEFINITIONS: Provide clear explanations in natural paragraph format.
- For MIXED CONTENT: Use appropriate formatting - steps for procedures, paragraphs for explanations.
- Use bold sparingly only for critical UI elements, button names, or warnings.
- Do NOT use markdown headings, code blocks, or excessive formatting.

HANDLING MISSING INFORMATION:
- If CONTEXT contains ANY mention of the topic (even partial), extract and provide that information.
- Only say "I don't have this information in the QuotePlan manual" if CONTEXT has ZERO mentions of the topic.
- When CONTEXT is partially relevant, extract what is available and state it clearly.

OUTPUT REQUIREMENTS:
- Output ONLY the final answer text.
- No greetings, no sign-offs, no meta-commentary.
- No JSON, no structured wrappers, no system messages.
- Direct, helpful, and complete answers only.

Remember: Your goal is to provide the most accurate, complete, and helpful answer possible using ONLY the information in CONTEXT.
"""
# =========================
# CHAT CALLS
# =========================

def _call_chat_completion(url, headers, payload, provider_name, retries=2):
    """Shared HTTP helper for chat completion calls."""
    for attempt in range(retries + 1):
        response = None
        try:
            start_time = time.time()
            response = HTTP_SESSION.post(
                url,
                headers=headers,
                json=payload,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            response_time = time.time() - start_time
            logger.info(f"{provider_name} API call successful (took {response_time:.2f}s)")
            return content
        except requests.exceptions.Timeout:
            if attempt < retries:
                logger.warning(f"{provider_name} API timeout, retrying ({attempt + 1}/{retries})...")
                time.sleep(1)
                continue
            raise
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"{provider_name} API response parsing error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            status_code = None
            if response is not None:
                status_code = response.status_code
            elif getattr(e, "response", None) is not None:
                status_code = e.response.status_code
            if attempt < retries and status_code and status_code >= 500:
                logger.warning(f"{provider_name} API error (status {status_code}), retrying...")
                time.sleep(1)
                continue
            logger.error(f"{provider_name} API error: {e}")
            raise
    raise Exception(f"{provider_name} API call failed after retries")


def call_openai(messages, retries=2):
    """Call OpenAI API with retry logic."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    payload = {
        "model": CHAT_MODEL_PRIMARY,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": LLM_MAX_TOKENS,
    }
    return _call_chat_completion(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        payload=payload,
        provider_name="OpenAI",
        retries=retries,
    )


def call_openrouter(messages, retries=2):
    """Call OpenRouter API with retry logic."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    payload = {
        "model": CHAT_MODEL_FALLBACK,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": LLM_MAX_TOKENS,
    }
    return _call_chat_completion(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        payload=payload,
        provider_name="OpenRouter",
        retries=retries,
    )


def call_llm_with_fallback(messages):
    """Try OpenAI first, then fallback to OpenRouter if available."""
    if OPENAI_API_KEY:
        try:
            return call_openai(messages)
        except Exception as e:
            if OPENROUTER_API_KEY:
                logger.warning(f"OpenAI failed, falling back to OpenRouter: {e}")
                return call_openrouter(messages)
            raise
    if OPENROUTER_API_KEY:
        return call_openrouter(messages)
    raise Exception("No API keys available (OPENAI_API_KEY or OPENROUTER_API_KEY required)")

# =========================
# UNANSWERED QUESTIONS TRACKING
# =========================

def save_unanswered_question(question: str, answer: str, retrieved_count: int = 0):
    """Save unanswered questions to JSON file for analysis and improvement."""
    try:
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)
        
        # Load existing unanswered questions
        unanswered_questions = []
        if UNANSWERED_QUESTIONS_FILE.exists():
            try:
                with open(UNANSWERED_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                    unanswered_questions = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error reading unanswered questions file: {e}, starting fresh")
                unanswered_questions = []
        
        # Create new entry
        new_entry = {
            "question": question,
            "answer": answer,
            "retrieved_chunks": retrieved_count,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "date": time.strftime("%Y-%m-%d")
        }
        
        # Check if this exact question already exists (avoid duplicates)
        question_lower = question.lower().strip()
        existing_questions = [q.get("question", "").lower().strip() for q in unanswered_questions]
        
        if question_lower not in existing_questions:
            unanswered_questions.append(new_entry)
            
            # Save to file
            with open(UNANSWERED_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(unanswered_questions, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved unanswered question to {UNANSWERED_QUESTIONS_FILE}")
        else:
            logger.debug(f"Question already exists in unanswered questions file, skipping duplicate")
            
    except Exception as e:
        logger.error(f"Error saving unanswered question: {e}", exc_info=True)

# =========================
# VIDEO LINK EXTRACTION
# =========================

def extract_video_links(context_text: str) -> list:
    """Extract YouTube/video links from context text."""
    video_links = []
    
    # Pattern to match full YouTube URLs (most common formats)
    # Matches: https://www.youtube.com/watch?v=VIDEO_ID
    #          https://youtu.be/VIDEO_ID
    #          http://www.youtube.com/watch?v=VIDEO_ID
    url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    
    matches = re.finditer(url_pattern, context_text)
    for match in matches:
        video_id = match.group(1)
        # Standardize to full YouTube URL format
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        if full_url not in video_links:
            video_links.append(full_url)
    
    # Also try to find URLs that might be in the text directly (already full URLs)
    direct_url_pattern = r'https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]{11}'
    direct_matches = re.findall(direct_url_pattern, context_text)
    for url in direct_matches:
        if url not in video_links:
            video_links.append(url)
    
    return video_links

def format_video_links_section(video_links: list) -> str:
    """Format video links section to append at the end of answer.
    Returns only the first video link. Frontend will automatically make it clickable.
    """
    if not video_links:
        return ""
    
    # Take only the first video link
    first_link = video_links[0]
    
    # Format with plain URL - frontend will automatically convert it to a clickable link
    section = "\n\nFor more detailed information, watch the video:\n"
    section += first_link
    
    return section

# =========================
# MAIN ANSWER FUNCTION
# =========================

def answer_structured(question, top_k=30):  # Production level - retrieve more chunks for maximum coverage
    try:
        # Greeting
        if _is_greeting(question):
            reply = random.choice([
                "Hi — I’m Eva AI, the QuotePlan Assistant. How can I help?",
                "Hello! I'm Eva AI, the QuotePlan Assistant. Ask me anything about QuotePlan.",
            ])
            CHAT_MEMORY["last_question"] = question
            CHAT_MEMORY["last_answer"] = reply
            return {"success": True, "question": question, "answer": reply}

        # Handle "yes" response to follow-up questions
        if _is_yes_response(question) and CHAT_MEMORY.get("last_answer"):
            prev_answer = CHAT_MEMORY["last_answer"]
            followup_q = _extract_followup_question_from_answer(prev_answer)
            
            if followup_q:
                # Extract the topic from the follow-up question
                topic = _extract_topic_from_followup_question(followup_q)
                if topic:
                    logger.info(f"Detected 'yes' response, extracting topic: {topic}")
                    # Use the extracted topic as the new question for RAG search
                    question = topic
                    # Continue to normal RAG processing below (don't return here)
                else:
                    # Couldn't extract topic, treat as normal question
                    logger.debug("Could not extract topic from follow-up question")
            else:
                # No follow-up question found, treat as normal question
                logger.debug("No follow-up question found in previous answer")
        
        # Follow-up (existing logic for other follow-up keywords)
        if _is_follow_up(question) and CHAT_MEMORY.get("last_answer") and not _is_yes_response(question):
            prev = CHAT_MEMORY["last_answer"]
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Previous answer:\n{prev}\n\nQuestion: {question}"}
            ]
            answer = call_llm_with_fallback(messages)
            CHAT_MEMORY["last_question"] = question
            CHAT_MEMORY["last_answer"] = answer
            return {"success": True, "question": question, "answer": answer}

        # Normal RAG
        # Improved query expansion for better retrieval
        expanded_question = question
        q_lower = question.lower()
        word_count = len(question.split())
        
        # Detect operation type first (critical for create vs modify)
        operation_keywords = []
        if "create" in q_lower or "add" in q_lower or "new" in q_lower:
            operation_keywords = ["create", "add", "new"]
        elif "modify" in q_lower or "edit" in q_lower or "update" in q_lower or "change" in q_lower:
            operation_keywords = ["modify", "edit", "update", "change"]
        elif "delete" in q_lower or "remove" in q_lower:
            operation_keywords = ["delete", "remove"]
        
        # Detect intent
        module, intent = detect_module_and_intent(question)
        
        # PRODUCTION: Aggressive query expansion for maximum retrieval
        # Always expand queries for better semantic matching
        if operation_keywords:
            # For operation queries, add operation keywords
            expanded_question = f"{question} {' '.join(operation_keywords)}"
        elif intent == "definition":
            # For definition queries, always add definition-related terms
            # Also add common variations for better matching
            expanded_question = f"{question} definition meaning explanation what is"
            # Special handling for common terms
            if "bom" in q_lower:
                expanded_question = f"{question} bill of materials BOM definition meaning explanation what is"
            elif "grn" in q_lower:
                expanded_question = f"{question} goods receipt note GRN definition meaning explanation what is"
            elif "labor" in q_lower or "labour" in q_lower:
                expanded_question = f"{question} labor code labour code definition meaning explanation what is"
            elif "po" in q_lower and "purchase" not in q_lower:
                expanded_question = f"{question} purchase order PO definition meaning explanation what is"
        elif intent == "procedure" or "how" in q_lower:
            # For procedure queries, always add procedure-related terms
            expanded_question = f"{question} steps procedure how to process method"
        else:
            # For general queries, add information-related terms
            expanded_question = f"{question} information details explanation"
        
        # Try multiple query variations for better retrieval
        query_variations = [expanded_question, question]
        
        # PRODUCTION: Comprehensive term variations and synonyms
        term_variations = {
            "grn": ["goods receipt note", "grn", "receipt note"],
            "bom": ["bill of materials", "bom", "bom items", "bom management"],
            "po": ["purchase order", "po", "purchase orders"],
            "pr": ["purchase requisition", "pr", "requisition"],
            "timesheet": ["time sheet", "timesheet", "time tracking", "time entry"],
            "stock": ["inventory", "stock", "current stock", "view current stock"],
            "synch": ["sync", "synchronize", "synch", "synchronization"],
            "calculate": ["calculation", "compute", "calculate", "view", "see", "check", "display"],
            "view": ["view", "see", "check", "display", "show", "calculate"],
            "create": ["create", "add", "new", "make", "generate"],
            "modify": ["modify", "edit", "update", "change", "alter"],
            "delete": ["delete", "remove", "erase"],
            "labor": ["labor code", "labor", "labour", "labour code"],
            "user": ["user created", "user-created", "created by user"],
        }
        
        # Add variations
        for term, variations in term_variations.items():
            if term in q_lower:
                for var in variations:
                    if var != term:
                        query_variations.append(question.replace(term, var))
        
        # Special handling: "calculate current stock" -> also try "view current stock"
        if "calculate" in q_lower and "stock" in q_lower:
            query_variations.append(question.replace("calculate", "view"))
        if "how to" in q_lower and "stock" in q_lower:
            query_variations.append(question.replace("how to", "view"))
        
        # Use the best query (original expanded) - production level retrieval
        q_emb = embed_text(expanded_question)
        retrieved = search_qdrant(q_emb, question, top_k=top_k)  # Already gets 3x internally

        # Try a few query variations if we retrieved too little
        if len(retrieved) < top_k:
            for variation in query_variations[1:1 + MAX_VARIATION_SEARCHES]:
                if not variation or variation == expanded_question:
                    continue
                try:
                    q_emb_var = embed_text(variation)
                    variation_hits = search_qdrant(q_emb_var, question, top_k=top_k)
                    retrieved = _merge_retrievals(retrieved, variation_hits)
                    if len(retrieved) >= top_k:
                        break
                except Exception as e:
                    logger.debug(f"Variation search failed ({variation[:50]}...): {e}")
        
        logger.debug(f"Retrieved {len(retrieved)} chunks for question: {question[:50]}...")
        if retrieved:
            logger.debug(f"First chunk preview: {retrieved[0].get('text', '')[:100]}...")

        # PRODUCTION: Multiple fallback strategies
        if not retrieved or len(retrieved) < 3:
            logger.debug("Few results, trying multiple fallback strategies...")
            
            # Strategy 1: Try with original question (no expansion)
            try:
                q_emb_original = embed_text(question)
                fallback_hits = _perform_qdrant_search(q_emb_original, question, top_k=50)
                if fallback_hits:
                    logger.debug(f"Fallback 1 (original query) returned {len(fallback_hits)} hits")
                    extra = []
                    for h in fallback_hits:
                        payload = getattr(h, "payload", None) or {}
                        if not isinstance(payload, dict):
                            payload = {}
                        text = payload.get("text") or payload.get("view") or payload.get("answer") or ""
                        if text:
                            extra.append({"text": text, "score": getattr(h, "score", 0.0)})
                    retrieved = _merge_retrievals(retrieved, extra)
            except Exception as e:
                logger.warning(f"Fallback 1 failed: {e}")
            
            # Strategy 2: Try with simplified query (remove stop words)
            if len(retrieved) < 5:
                try:
                    # Extract main terms
                    words = question.lower().split()
                    main_terms = [w for w in words if w not in {"how", "to", "what", "is", "the", "a", "an", "do", "does", "can", "will"}]
                    if main_terms and len(main_terms) < len(words):
                        simplified_q = " ".join(main_terms)
                        q_emb_simple = embed_text(simplified_q)
                        fallback_hits2 = _perform_qdrant_search(q_emb_simple, question, top_k=30)
                        if fallback_hits2:
                            logger.debug(f"Fallback 2 (simplified query) returned {len(fallback_hits2)} hits")
                            extra = []
                            for h in fallback_hits2:
                                payload = getattr(h, "payload", None) or {}
                                if not isinstance(payload, dict):
                                    payload = {}
                                text = payload.get("text") or payload.get("view") or payload.get("answer") or ""
                                if text:
                                    extra.append({"text": text, "score": getattr(h, "score", 0.0)})
                            retrieved = _merge_retrievals(retrieved, extra)
                except Exception as e:
                    logger.warning(f"Fallback 2 failed: {e}")

        if not retrieved:
            logger.warning(f"No chunks found. Collection: {COLLECTION_NAME}, Question: {question[:50]}")
            try:
                collections = qdrant.get_collections()
                collection_names = [c.name for c in collections.collections]
                logger.debug(f"Available collections: {collection_names}")
                if COLLECTION_NAME in collection_names:
                    info = qdrant.get_collection(COLLECTION_NAME)
                    logger.debug(f"Collection {COLLECTION_NAME} has {info.points_count} points")
            except Exception as e:
                logger.error(f"Error checking collection: {e}")
            answer = "I don't have this information in the QuotePlan manual."
            # Save unanswered question
            save_unanswered_question(question, answer, retrieved_count=0)
        else:
            # Use text field, fallback to view if text is empty
            # Relaxed relevance filtering - trust semantic search more
            context_parts = _build_context_parts(retrieved, question, filter_low_score=True)
            
            # PRODUCTION: If we filtered out too many, use original retrieved chunks
            # Be very lenient - only use all if we filtered out more than 80%
            if len(context_parts) < len(retrieved) * 0.2 and len(context_parts) < MAX_CONTEXT_PARTS:
                logger.warning(f"Too many chunks filtered ({len(context_parts)}/{len(retrieved)}), using broader context")
                context_parts = _build_context_parts(retrieved, question, filter_low_score=False)
            
            if not context_parts:
                logger.warning("No context parts extracted after filtering")
                # Try one more time with original question embedding
                try:
                    logger.debug("Trying one more search with original question...")
                    q_emb_original = embed_text(question)
                    retrieved_original = search_qdrant(q_emb_original, question, top_k=10)
                    if retrieved_original:
                        context_parts = _build_context_parts(retrieved_original, question, filter_low_score=False)
                        logger.debug(f"Retrieved {len(context_parts)} chunks with original question")
                except Exception as e:
                    logger.warning(f"Fallback search failed: {e}")
                
                if not context_parts:
                    answer = "I don't have this information in the QuotePlan manual."
                    # Save unanswered question
                    save_unanswered_question(question, answer, retrieved_count=len(retrieved))
            else:
                context = "\n\n".join(context_parts)
                logger.debug(f"Context length: {len(context)} characters")
                
                # Extract video links from context
                video_links = extract_video_links(context)
                if video_links:
                    logger.debug(f"Found {len(video_links)} video link(s) in context")
                
                # Detect operation type (create, modify, delete, etc.)
                question_lower = question.lower()
                operation = None
                if "create" in question_lower or "add" in question_lower or "new" in question_lower:
                    operation = "create"
                elif "modify" in question_lower or "edit" in question_lower or "update" in question_lower or "change" in question_lower:
                    operation = "modify"
                elif "delete" in question_lower or "remove" in question_lower:
                    operation = "delete"
                
                # Detect question type
                is_definition = any(w in question_lower for w in ["what is", "what's", "meaning", "define", "kya hai"])
                
                # Build focused instructions - optimized for maximum answers
                if is_definition:
                    # Extract main term from question
                    main_term = question.lower()
                    for prefix in ["what is", "what's", "what are", "meaning of", "define"]:
                        if main_term.startswith(prefix):
                            main_term = main_term[len(prefix):].strip()
                            break
                    main_term = main_term.rstrip("?").strip()
                    
                    instructions = f"""DEFINITION QUESTION - CRITICAL INSTRUCTIONS:
1. Search CONTEXT for ANY mention of "{main_term}" or related terms
2. Extract information even if it's not labeled as "definition"
3. Look for: "{main_term} is...", "{main_term} means...", "{main_term} refers to...", "{main_term} is used for...", descriptions, explanations
4. Combine ALL information about "{main_term}" from CONTEXT
5. If CONTEXT mentions "{main_term}" in ANY way, provide that information
6. Format: "[Term] is [information from CONTEXT]. [Additional details if available]."
7. DO NOT say "I don't have this information" if CONTEXT mentions the term at all"""
                elif operation:
                    instructions = f"""PROCEDURE QUESTION - CRITICAL INSTRUCTIONS:
1. Find {operation} steps in CONTEXT
2. Match the operation exactly - if question asks '{operation}', use {operation} steps only
3. Include ALL steps from CONTEXT - count them exactly
4. Number steps: 1., 2., 3., etc.
5. One step per line"""
                else:
                    instructions = """GENERAL QUESTION - CRITICAL INSTRUCTIONS:
1. Find relevant information in CONTEXT
2. If CONTEXT contains steps, include ALL steps numbered (1., 2., 3., etc.)
3. If CONTEXT contains definitions/explanations, provide them
4. Use exact words from CONTEXT"""
                
                user_message = f"""CONTEXT:
{context}

{instructions}

CRITICAL REMINDER:
- Use ONLY information from CONTEXT
- Extract information even from partial matches
- Only say "I don't have this information" if CONTEXT has ZERO mentions of the topic

Question: {question}"""
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
                try:
                    logger.debug("Calling LLM API...")
                    start_time = time.time()
                    answer = call_llm_with_fallback(messages)
                    
                    response_time = time.time() - start_time
                    logger.info(f"LLM response generated (took {response_time:.2f}s, {len(answer)} chars)")
                    
                    # Check if answer indicates no information available
                    answer_lower = answer.lower()
                    no_info_phrases = [
                        "i don't have this information",
                        "i don't have information",
                        "don't have this information",
                        "don't have information",
                        "no information available",
                        "information is not available",
                        "not available in the quoteplan manual",
                        "not in the quoteplan manual",
                        "not explicitly defined",
                        "no mentions",
                        "no descriptions",
                        "not found",
                        "cannot find",
                        "doesn't have",
                        "don't have",
                        "not in the",
                        "not available"
                    ]
                    
                    # Also check if answer is very short and contains negative phrases
                    has_no_info = any(phrase in answer_lower for phrase in no_info_phrases)
                    
                    # Additional check: if answer is very short (< 100 chars) and contains negative words
                    if not has_no_info and len(answer) < 100:
                        negative_words = ["not", "no", "cannot", "doesn't", "don't", "unavailable", "missing"]
                        if any(word in answer_lower for word in negative_words):
                            # Check if it's actually saying no info vs just a short answer
                            if any(phrase in answer_lower for phrase in ["not found", "not available", "not in", "no information", "cannot find"]):
                                has_no_info = True
                    
                    # Save unanswered question if answer indicates no information
                    if has_no_info:
                        save_unanswered_question(question, answer, retrieved_count=len(retrieved))
                    
                    # Only append video links if:
                    # 1. Answer doesn't already contain video links
                    # 2. Answer has actual information (not "I don't have information")
                    # 3. Answer is meaningful (more than just "I don't have information")
                    answer_video_links = extract_video_links(answer)
                    
                    if answer_video_links:
                        logger.debug(f"Answer already contains {len(answer_video_links)} video link(s), skipping append")
                    elif has_no_info:
                        logger.debug("Answer indicates no information available - NOT appending video links")
                        # Don't append video links if answer says no information
                    elif video_links and len(answer.strip()) > 50:  # Only if answer is meaningful (more than 50 chars)
                        # Check if video link is relevant to the question
                        # Extract main keywords from question
                        question_keywords = set(question.lower().split())
                        question_keywords = {kw for kw in question_keywords if len(kw) > 3 and kw not in {"what", "is", "the", "how", "to", "do", "does", "are", "can", "will", "would", "should", "could"}}
                        
                        # Check if answer contains question keywords (relevance check)
                        answer_has_keywords = any(kw in answer_lower for kw in question_keywords) if question_keywords else True
                        
                        if answer_has_keywords:
                            video_section = format_video_links_section(video_links)
                            answer = answer + video_section
                            logger.debug("Appended relevant video links to answer")
                        else:
                            logger.debug("Answer doesn't contain question keywords - NOT appending video links (likely unrelated)")
                    elif video_links:
                        logger.debug("Answer too short or no information - NOT appending video links")
                except Exception as e:
                    logger.error(f"LLM API call failed: {e}", exc_info=True)
                    answer = "I apologize, but I encountered an error while generating the answer. Please try again."

        CHAT_MEMORY["last_question"] = question
        CHAT_MEMORY["last_answer"] = answer
        return {"success": True, "question": question, "answer": answer}

    except Exception as e:
        logger.error(f"Error in answer_structured: {e}", exc_info=True)
        return {
            "success": False, 
            "question": question, 
            "answer": "I apologize, but I encountered an error processing your question. Please try again or rephrase your question."
        }

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
    result = answer(args.q)
    print(result)  # CLI output, keep print for command-line usage
