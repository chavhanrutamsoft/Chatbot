# QuotePlan RAG Chatbot - Complete System

A production‑ready Retrieval‑Augmented Generation (RAG) chatbot system for QuotePlan documentation. Features a modern web interface, semantic search, and AI‑powered Q&A using free OpenRouter models.

## 🎯 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Frontend (HTML/CSS/JS)                 │
│                  http://localhost:8000                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Python HTTP Server (server.py)                  │
│          Serves UI + Routes API Requests                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         Python RAG Backend (query_bot.py)                    │
│  1. Embed question (local all‑MiniLM‑L6‑v2)                 │
│  2. Search Qdrant vector database                           │
│  3. Generate answer with free OpenRouter LLM                │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼─────┐  ┌─────▼──────┐  ┌──▼──────────┐
    │   Qdrant    │  │  OpenRouter│  │ Local Model │
    │  (Vector DB)│  │  (Free LLM)│  │ (Embeddings)│
    └─────────────┘  └────────────┘  └─────────────┘
```

## 📋 Project Structure

```
d:\qdrant-rag/
├── Frontend Files
│   ├── index.html              # Main chatbot UI
│   ├── style.css               # Modern styling
│   ├── script.js               # Frontend JavaScript
│   └── server.py               # Python HTTP server (serves UI + API)
│
├── Backend Files
│   ├── query_bot.py            # RAG query engine
│   ├── ingest_qdrant.py        # Data ingestion script
│   ├── extract_chunks.py       # Text chunking utility
│   └── api.php                 # Alternative PHP API (optional)
│
├── Configuration
│   ├── .env                    # API keys and settings
│   ├── docker-compose.yml      # Qdrant container
│   └── requirements.txt        # Python dependencies
│
├── Data
│   ├── chunks.json             # Extracted text chunks
│   └── Quote Plan Help Manual.docx # Source document
│
└── Documentation
    ├── README.md               # This file
    ├── README_RUN.md           # Quick start guide
    └── FRONTEND_SETUP.md       # Frontend setup details
```

## 🚀 Quick Start (≈5 minutes)

### Prerequisites
- Python 3.8+
- Docker (for Qdrant)
- OpenRouter API key (free tier)

### 1️⃣ Clone / navigate to the project

```bash
cd d:\qdrant-rag
```

### 2️⃣ Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Start Qdrant (Docker)

```bash
docker-compose up -d
```

### 4️⃣ Configure your API key

Edit **`.env`** (see *Configuration* below) and set:

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

### 5️⃣ Ingest the knowledge base (first run only)

```bash
python ingest_qdrant.py
```

### 6️⃣ Start the web server

```bash
python server.py
```

### 7️⃣ Open the chatbot

Visit **http://localhost:8000** in your browser.

---

## 📚 Detailed Setup

### 1️⃣ Python environment (optional virtualenv)

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2️⃣ Qdrant vector database

```bash
docker-compose up -d
docker-compose ps          # verify container is running
```

### 3️⃣ `.env` – **Configuration variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(none)* | **Required** – your OpenRouter key |
| `QDRANT_HOST` | `http://localhost:6333` | URL of the Qdrant service |
| `COLLECTION_NAME` | `quoteplan_chunks` | Name of the vector collection |
| `CHAT_MODEL` | `openai/gpt-4o-mini:free` | Primary LLM model used by `query_bot.py` |
| `OPENROUTER_FALLBACK_MODELS` | *(empty)* | Optional comma‑separated list of fallback OpenRouter models (e.g., `mistralai/mistral-7b-instruct:free,anthropic/claude-3-haiku:free`) |
| `OLLAMA_FALLBACK` | `false` | Set to `true` to use a local Ollama model when OpenRouter fails |
| `OLLAMA_MODEL` | `mistral:7b` | Model name for Ollama fallback |
| `OLLAMA_HTTP_URL` | `http://localhost:11434/api/generate` | (Optional) Custom Ollama HTTP endpoint |
| `CHUNKS_FILE` | `chunks.json` | File produced by `extract_chunks.py` and read by `ingest_qdrant.py` |
| `BATCH_SIZE` | `16` | Number of points uploaded per upsert batch |

> **Why the change?**  
> The original README listed `CHAT_MODEL=mistralai/devstral-2512:free`, but the code defaults to `openai/gpt-4o-mini:free`. The table now reflects the actual default while still allowing you to override it in `.env`.

### 4️⃣ Ingesting / updating the knowledge base

1. **Extract chunks** (optional – only if you change the source document)

   ```bash
   python extract_chunks.py
   ```

   *You can adjust `CHUNK_SIZE_CHARS` inside `extract_chunks.py` (default 800).*

2. **Upload to Qdrant**

   ```bash
   python ingest_qdrant.py
   ```

   The script respects `CHUNKS_FILE` and `BATCH_SIZE` from `.env`.

### 5️⃣ Running the server

```bash
python server.py
```

You should see:

```
🚀 QuotePlan Chatbot Server running at http://localhost:8000
📝 Open your browser and navigate to http://localhost:8000
Press Ctrl+C to stop the server
```

---

## 🎨 Frontend Features

- **Real‑time messaging** – instant display of user & bot messages  
- **Auto‑scroll** – always shows the latest reply  
- **Typing indicator** – “Bot is thinking…” animation  
- **Message animations** – smooth slide‑in effects  

### Quick‑prompt buttons

| Prompt | What it asks |
|--------|--------------|
| **Create PO** | “How do I create a Purchase Order?” |
| **Receive Items** | “How do I receive items?” |
| **What is BOM** | “What is a BOM?” |
| **Modify PO** | “How do I modify a PO?” |

### Responsive design

- Desktop: full‑width layout  
- Tablet: medium‑screen optimisations  
- Mobile: touch‑friendly single‑column UI  

---

## 🔧 Backend Architecture

### `query_bot.py` – RAG engine (high‑level flow)

```python
def answer(question):
    # 1️⃣ Embed the question (local all‑MiniLM‑L6‑v2)
    q_emb = embed_text(question)

    # 2️⃣ Search Qdrant
    retrieved = search_qdrant(q_emb, top_k=5)

    # 3️⃣ Call the LLM with context
    answer_text = call_chat_api(question, retrieved)

    return answer_text
```

Key points:

- **Embedding** – uses `SentenceTransformer("all-MiniLM-L6-v2")`.  
- **Search** – flexible wrapper (`_qdrant_search_flexible`) that works with `search`, `search_points`, or `query_points` depending on the client version.  
- **LLM call** – tries `CHAT_MODEL`; on HTTP 429 it falls back to any models listed in `OPENROUTER_FALLBACK_MODELS`. If all fail and `OLLAMA_FALLBACK=true`, it calls a local Ollama model.  

### `server.py` – HTTP API

| Endpoint | Method | Request body | Success response | Error response |
|----------|--------|--------------|------------------|----------------|
| `/api` | POST | `{ "question": "…" }` | `{ "success": true, "question": "...", "answer": "…" }` | `{ "success": false, "error": "…" }` |
| `GET /` | GET | – | Serves `index.html` and static assets | 404 |

Status codes used:

- **200** – Success  
- **400** – Bad request (e.g., missing `question`)  
- **404** – Endpoint not found  
- **500** – Server error / internal exception  

---

## 📊 Performance (typical)

| Metric | Approx. value | Comment |
|--------|---------------|---------|
| First request (model load) | 5‑15 s | Loads the embedding model |
| Subsequent request | 2‑5 s | LLM + Qdrant lookup |
| Qdrant similarity search | < 100 ms | Vector distance |
| Ingestion (≈80 chunks) | ~30 s | `ingest_qdrant.py` |
| Embedding model size | ~130 MB | `all‑MiniLM‑L6‑v2` |

---

## 🔐 Security notes

### For production

1. Add authentication (e.g., JWT) to `server.py`.  
2. Implement rate‑limiting / request throttling.  
3. Serve over HTTPS (TLS termination).  
4. Validate and sanitise all incoming JSON.  
5. Keep the OpenRouter key out of source control – use a secrets manager.  

### Current development setup

- No auth, no rate limiting, no TLS.  
- API key stored in `.env` (do not commit this file).  

---

## 🐛 Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Port 8000 already in use** | Another process bound to 8000 | Kill the process (`netstat -ano \| findstr :8000` → `taskkill /PID <PID> /F`) or change `PORT` in `server.py`. |
| **`python query_bot.py` fails** | Missing env vars or Qdrant not running | Ensure `.env` has `OPENROUTER_API_KEY`; run `docker-compose up -d` and verify `curl http://localhost:6333/health`. |
| **No response from Qdrant** | Container stopped or wrong host | `docker-compose ps`; if stopped, `docker-compose up -d`. |
| **429 Too Many Requests (OpenRouter)** | Rate‑limit exceeded | Wait a minute, or add fallback models via `OPENROUTER_FALLBACK_MODELS`. |
| **Embedding model cannot load** | `sentence_transformers` not installed or no internet | `pip install -r requirements.txt`; ensure internet access for the first download. |

---

## 📖 API Documentation

### POST `/api`

**Request**

```json
{
  "question": "How do I create a Purchase Order?"
}
```

**Success response (HTTP 200)**

```json
{
  "success": true,
  "question": "How do I create a Purchase Order?",
  "answer": "To create a Purchase Order in QuotePlan, follow these steps..."
}
```

**Error response (HTTP 400 / 500)**

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

**Status codes**

- **200** – Success  
- **400** – Bad request (missing question)  
- **404** – Endpoint not found  
- **500** – Server error  

---

## 🔄 Updating the Knowledge Base

1. **Add a new document** to `d:\qdrant-rag\` (supported: `.docx`, `.txt`, `.pdf`).  
2. **Edit `extract_chunks.py`** – change `INPUT_DOCX` (or adapt for other formats).  
3. **Re‑run the pipeline**

```bash
python extract_chunks.py
python ingest_qdrant.py
```

---

## 💡 Customisation

| What | How |
|------|-----|
| **Change UI colours** | Edit `style.css` – modify the gradient values. |
| **Add quick‑prompt buttons** | Edit `index.html` – copy an existing `<button class="quick-prompt">` block and change the label / text. |
| **Swap LLM model** | Change `CHAT_MODEL` in `.env` (e.g., `CHAT_MODEL=mistralai/devstral-2512:free`). |
| **Adjust chunk size** | Edit `CHUNK_SIZE_CHARS` in `extract_chunks.py` and re‑ingest. |
| **Enable Ollama fallback** | Set `OLLAMA_FALLBACK=true` and optionally `OLLAMA_MODEL` / `OLLAMA_HTTP_URL`. |

---

## 📞 Support & Help

**Common questions**

- **How many chunks can I ingest?**  
  Unlimited, limited only by disk space. Adjust `BATCH_SIZE` if you hit memory limits.  

- **Can I use my own LLM?**  
  Yes – modify `call_chat_api()` in `query_bot.py` to call any API you prefer.  

- **How do I back up the vector database?**  

  ```bash
  docker-compose stop
  cp -r qdrant_storage/ backup/
  docker-compose start
  ```

- **Can I deploy to the cloud?**  
  Absolutely – just expose port 8000 and the Qdrant port (6333) on your host, and provide the same `.env` variables.

---

## 📄 License

- **Qdrant** – AGPL 3.0  
- **Sentence‑Transformers** – Apache 2.0  
- **OpenRouter** – free‑tier usage (respect their terms)

---

## 🎓 Learning Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)  
- [OpenRouter Models](https://openrouter.ai/models)  
- [Sentence‑Transformers](https://www.sbert.net/)  
- [RAG Patterns (LangChain)](https://python.langchain.com/docs/use_cases/question_answering/)  

---

## 🤝 Contributing

1. Fork or clone the repo.  
2. Make your improvements.  
3. Run the full test flow (`python ingest_qdrant.py && python server.py && curl http://localhost:8000/api -d '{"question":"test"}' -H "Content-Type: application/json"`).  
4. Submit a Pull Request with a clear description of the change.

---

**Last Updated**: December 2025  
**Version**: 1.0  
**Status**: Production Ready (development‑only security)  
