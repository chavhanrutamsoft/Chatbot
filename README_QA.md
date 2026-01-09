# QA-Based RAG Chatbot - Quick Start

## 🎯 What's New?

Ab aapke chatbot mein **QA (Question-Answer) pairs** use ho rahe hain jo **better answers** dene mein help karte hain!

## ⚡ Quick Setup

### 1. Extract QA Pairs
```bash
python backend/extract_qa_pairs.py
```

### 2. Ingest into Qdrant
```bash
python backend/ingest_qa_qdrant.py
```

### 3. Start Server
```bash
python backend/server.py
```

## 📊 What You Get

- ✅ **494 QA pairs** extracted from your document
- ✅ **Better answer quality** - direct Q&A matching
- ✅ **Structured data** - easy to maintain and update
- ✅ **Faster retrieval** - semantic search on questions

## 📁 Key Files

- `backend/extract_qa_pairs.py` - QA extraction script
- `backend/ingest_qa_qdrant.py` - QA ingestion script
- `data/qa_pairs.json` - All extracted QA pairs
- `docs/QA_EXTRACTION_GUIDE.md` - Full documentation

## 🔄 Migration from Old System

Agar pehle se chunks use kar rahe the:

1. **Backup current data:**
   ```bash
   cp data/chunks.json data/chunks_backup.json
   ```

2. **Extract QA pairs:**
   ```bash
   python backend/extract_qa_pairs.py
   ```

3. **Update .env:**
   ```bash
   COLLECTION_NAME=quoteplan_qa
   ```

4. **Re-ingest:**
   ```bash
   python backend/ingest_qa_qdrant.py
   ```

## 📖 Full Documentation

See `docs/QA_EXTRACTION_GUIDE.md` for complete guide.

---

**Status**: ✅ Ready to use
**QA Pairs**: 494 extracted
**Collection**: `quoteplan_qa`
