# 🚀 START HERE - Quick Setup Guide

## ✅ Kya Already Ho Chuka Hai

Aapke QA pairs already extract ho chuke hain aur ready hain:
- ✅ 765 QA pairs extracted
- ✅ Questions fixed and improved
- ✅ Quality checked (9.6/10 score)

## 📝 Ab Bas 2 Commands Run Karein

### Command 1: QA Pairs ko Qdrant mein Load Karein

```bash
python backend/ingest_qa_qdrant.py
```

**Ye kya karega:**
- 765 QA pairs ko Qdrant database mein store karega
- Embeddings generate karega
- 2-3 minutes lag sakte hain

**Expected Output:**
```
Loading local embedding model (all-MiniLM-L6-v2)...
Created collection: quoteplan_qa
Total QA pairs: 765
Upserted batch 1/48...
...
✅ Done ingesting QA pairs into Qdrant!
```

### Command 2: Server Start Karein

```bash
python backend/server.py
```

**Ye kya karega:**
- Web server start karega
- Chatbot interface available hoga

**Expected Output:**
```
🚀 QuotePlan Chatbot Server running at http://localhost:8000
📝 Open your browser and navigate to http://localhost:8000
Press Ctrl+C to stop the server
```

### Step 3: Browser Mein Test Karein

1. Browser open karein (Chrome, Firefox, Edge)
2. Address bar mein type karein: `http://localhost:8000`
3. Enter press karein
4. Chatbot interface dikhega
5. Questions poochhein:
   - "How do I create a lead?"
   - "What is lead status?"
   - "How do I create a timesheet?"

## ⚠️ Important - Pehle Check Karein

### 1. Qdrant Running Hai?

```bash
docker-compose ps
```

Agar running nahi hai:
```bash
docker-compose up -d
```

### 2. .env File Check Karein

`.env` file (root folder mein) mein ye hona chahiye:
```bash
QDRANT_HOST=http://localhost:6333
COLLECTION_NAME=quoteplan_qa
OPENAI_API_KEY=your_key_here
# ya
OPENROUTER_API_KEY=your_key_here
```

## 🔍 Verification

Sab ready hai ya nahi check karein:
```bash
python backend/check_ready.py
```

## 📋 Complete Step-by-Step

```bash
# Terminal/Command Prompt open karein

# Step 1: Check readiness
python backend/check_ready.py

# Step 2: Ingest QA pairs (2-3 minutes)
python backend/ingest_qa_qdrant.py

# Step 3: Start server (new terminal window mein)
python backend/server.py

# Step 4: Browser mein
# http://localhost:8000
```

## ❓ Common Questions

### Q: Kya pehle se chunks ingest kiye hain to kya karein?
**A:** Koi problem nahi. QA pairs alag collection mein jayenge (`quoteplan_qa`). Dono use kar sakte hain.

### Q: Agar error aaye to?
**A:** 
- Qdrant check karein: `docker-compose ps`
- Dependencies: `pip install -r requirements.txt`
- .env file check karein

### Q: Kya ye files delete kar sakte hain?
**A:** Nahi! Ye files important hain:
- `extract_qa_pairs_improved.py` - Future updates ke liye
- `fix_qa_questions.py` - Question fixing ke liye
- `analyze_qa_quality.py` - Quality check ke liye

## ✨ Summary

**Bas 2 Commands:**
1. `python backend/ingest_qa_qdrant.py` ← Data load karein
2. `python backend/server.py` ← Server start karein

**Phir browser:**
- `http://localhost:8000` ← Chatbot use karein

---

**Ready? Let's go! 🚀**
