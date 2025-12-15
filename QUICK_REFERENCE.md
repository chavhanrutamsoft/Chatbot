# QuotePlan Chatbot - Quick Reference Card

## 🚀 Start Services

```powershell
# Terminal 1: Start Qdrant (Docker)
docker-compose up -d

# Terminal 2: Start Web Server
python server.py

# Open browser: http://localhost:8000
```

## 📁 File Structure

| File | Purpose | Type |
|------|---------|------|
| `index.html` | Chatbot UI | Frontend |
| `script.js` | Message handling | Frontend |
| `style.css` | Styling & animations | Frontend |
| `server.py` | HTTP server + API | Backend |
| `query_bot.py` | RAG engine | Backend |
| `ingest_qdrant.py` | Data ingestion | Backend |
| `extract_chunks.py` | Text chunking | Utility |
| `.env` | Configuration | Config |
| `docker-compose.yml` | Qdrant setup | Config |

## ⚙️ Configuration

**.env File:**
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx  # Required
QDRANT_HOST=http://localhost:6333          # Default
COLLECTION_NAME=quoteplan_chunks           # Default
CHAT_MODEL=mistralai/devstral-2512:free    # Free tier
```

## 🔧 Common Tasks

### Add New Document
```bash
# 1. Place document in d:\qdrant-rag\
# 2. Edit extract_chunks.py (update INPUT_DOCX path)
# 3. Re-extract and ingest
python extract_chunks.py
python ingest_qdrant.py
```

### Query Directly (Without Web UI)
```bash
python query_bot.py --q "Your question here?"
```

### Check Qdrant Status
```bash
docker-compose ps
curl http://localhost:6333/health
```

### View Ingested Chunks
```bash
cat chunks.json
```

### Reset Vector Database
```bash
# Delete collection and re-ingest
docker-compose down -v
docker-compose up -d
python ingest_qdrant.py
```

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Chatbot Web UI | http://localhost:8000 | User interface |
| API Endpoint | http://localhost:8000/api | JSON API |
| Qdrant Console | http://localhost:6333 | Vector DB admin |

## 📊 Key Metrics

| Metric | Value |
|--------|-------|
| First Response | 5-15s (model loading) |
| Regular Response | 2-5s |
| Knowledge Base | 80 chunks |
| Embedding Model | all-MiniLM-L6-v2 (384-dim) |
| Vector DB | Qdrant (local) |
| LLM Provider | OpenRouter (free tier) |

## 💡 Common Issues

| Issue | Fix |
|-------|-----|
| `Address already in use` | Port 8000 busy - kill process or use different port |
| `Connection refused` | Qdrant not running - `docker-compose up -d` |
| `API key invalid` | Check `.env` file - ensure correct key format |
| `No response from bot` | Check Python is in PATH, verify `.env` has API key |
| `Slow first request` | Normal - model loads on first use (~10s) |

## 🔐 Security Checklist

- [ ] Change port 8000 to non-standard port in production
- [ ] Add authentication to `server.py`
- [ ] Enable HTTPS/SSL
- [ ] Use `.env` for secrets (never commit)
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Use API gateway in front
- [ ] Enable Qdrant authentication
- [ ] Backup vector database regularly
- [ ] Monitor API usage (free tier limits)

## 📚 Documentation

| Document | Content |
|----------|---------|
| `README.md` | Complete system guide |
| `README_RUN.md` | Quick start (Python RAG) |
| `FRONTEND_SETUP.md` | Frontend details |
| This file | Quick reference |

## 🎯 Next Steps

1. ✅ Frontend running at http://localhost:8000
2. ✅ Backend integrated with RAG system
3. 🔄 Monitor performance and user feedback
4. 📈 Optionally: Add authentication, deploy to cloud
5. 🔧 Customize: Colors, prompts, models
6. 📊 Monitor: API usage, response times, accuracy

## 🆘 Help Commands

```bash
# Check Python version
python --version

# Verify pip packages
pip list | findstr -i "qdrant\|sentence\|requests"

# Test API manually
curl -X POST http://localhost:8000/api -H "Content-Type: application/json" -d "{\"question\":\"test\"}"

# View server logs
# Check the terminal running server.py for real-time logs

# Restart services
docker-compose restart
```

## 📞 Quick Support

- **Web UI issues**: Check `script.js` and `style.css`
- **API issues**: Check `server.py` logs
- **RAG issues**: Check `query_bot.py` and ensure Qdrant is running
- **Data issues**: Verify `chunks.json` exists and has content
- **Model issues**: Check `.env` file and API key validity

---

**ProTip**: Use Ctrl+C to stop server, Ctrl+Shift+Esc to find port conflicts, `docker-compose logs` to see container output
